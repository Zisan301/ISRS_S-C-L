from __future__ import annotations

import json
import math
import os
import re
import subprocess
import sys
import sysconfig
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from isrs_scl.link import LinkModel
from isrs_scl.system.grid import build_grid
from isrs_scl.system.parameters import apply_defaults, validate_config

C = 299792458.0

TARGET_WAVELENGTHS_NM = [1535.0, 1550.0, 1560.0]
SPANS = [1, 4, 8]
REQUESTED_LAUNCH_POWERS_DBM = [-2.0, 0.0, 2.0]

GENERATED = ROOT / "releases" / "pnc-v1.0" / "generated"
RAW_DIR = GENERATED / "gnpy_cband_launch_power_raw"
REFERENCE_ROWS = GENERATED / "cband_launch_power_sweep_reference_rows.csv"
COMPARISON_ROWS = GENERATED / "cband_launch_power_sweep_model_comparison.csv"
SUMMARY_JSON = GENERATED / "cband_launch_power_sweep_summary.json"

SPECTRUM_PATH = ROOT / "external_validation" / "gnpy" / "cases" / "scl_9_targets_flat_spectrum.json"
NETWORK_TEMPLATE = ROOT / "external_validation" / "gnpy" / "cases" / "gnpy_flat_{spans}span_network.json"


def p_label(power_dbm: float) -> str:
    if power_dbm < 0:
        return f"m{abs(power_dbm):.0f}"
    if power_dbm > 0:
        return f"p{power_dbm:.0f}"
    return "p0"


def read_text_robust(path: Path) -> str:
    data = path.read_bytes()
    for enc in ["utf-8-sig", "utf-16", "utf-16-le", "cp1252"]:
        try:
            text = data.decode(enc)
            if "The GSNR per channel" in text or "Channel frequency" in text:
                return text.replace("\x00", "")
        except UnicodeDecodeError:
            pass
    return data.decode("utf-8", errors="replace").replace("\x00", "")


def parse_gnpy_rows(path: Path) -> list[dict[str, float]]:
    clean = re.sub(r"\x1b\[[0-9;]*m", "", read_text_robust(path))
    rows: list[dict[str, float]] = []

    for line in clean.splitlines():
        m = re.match(
            r"\s*(\d+)\s+([0-9.]+)\s+(-?[0-9.]+)\s+([0-9.]+)\s+([0-9.]+)\s+([0-9.]+)\s*$",
            line,
        )
        if not m:
            continue

        freq_thz = float(m.group(2))
        wl_nm = C / (freq_thz * 1e12) * 1e9

        rows.append(
            {
                "channel": int(m.group(1)),
                "frequency_thz": freq_thz,
                "wavelength_nm": wl_nm,
                "channel_power_dbm": float(m.group(3)),
                "osnr_ase_signal_bw_db": float(m.group(4)),
                "snr_nli_signal_bw_db": float(m.group(5)),
                "gnpy_gsnr_db": float(m.group(6)),
            }
        )

    if not rows:
        raise RuntimeError(f"No GNPy channel rows found in {path}")

    return rows


def nearest_rows_for_targets(
    rows: list[dict[str, float]],
    targets_nm: list[float],
    max_error_nm: float = 1.0,
) -> list[dict[str, float]]:
    selected: list[dict[str, float]] = []
    used_channels: set[int] = set()

    for target in targets_nm:
        nearest = min(rows, key=lambda row: abs(float(row["wavelength_nm"]) - target))
        err = abs(float(nearest["wavelength_nm"]) - target)

        if err > max_error_nm:
            raise RuntimeError(
                f"Target {target:.3f} nm not found within {max_error_nm:.3f} nm; "
                f"nearest was {nearest['wavelength_nm']:.6f} nm"
            )

        ch = int(nearest["channel"])
        if ch in used_channels:
            raise RuntimeError(
                f"Duplicate GNPy channel {ch} selected for target {target:.3f} nm"
            )

        used_channels.add(ch)

        item = dict(nearest)
        item["target_wavelength_nm"] = target
        item["target_error_nm"] = float(nearest["wavelength_nm"]) - target
        selected.append(item)

    return selected


def load_config() -> dict[str, Any]:
    config_path = ROOT / "config_q2_final.yaml"
    raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    cfg = apply_defaults(raw)
    validate_config(cfg, base_dir=config_path.parent)
    return cfg


def metric_dict(values: list[float]) -> dict[str, float | int | None]:
    if not values:
        return {
            "n": 0,
            "rmse_db": None,
            "mae_db": None,
            "bias_db": None,
            "max_abs_error_db": None,
        }

    arr = np.asarray(values, dtype=float)
    return {
        "n": int(arr.size),
        "rmse_db": float(np.sqrt(np.mean(arr**2))),
        "mae_db": float(np.mean(np.abs(arr))),
        "bias_db": float(np.mean(arr)),
        "max_abs_error_db": float(np.max(np.abs(arr))),
    }


def grouped_metrics(df: pd.DataFrame, group_col: str) -> dict[str, dict[str, float | int | None]]:
    out: dict[str, dict[str, float | int | None]] = {}
    for key, group in df.groupby(group_col):
        out[str(key)] = metric_dict(group["residual_db"].astype(float).tolist())
    return out


def locate_gnpy_transmission_exe() -> Path:
    scripts_dir = Path(sysconfig.get_path("scripts"))
    candidates = [
        scripts_dir / "gnpy-transmission-example.exe",
        scripts_dir / "gnpy-transmission-example",
    ]

    for candidate in candidates:
        if candidate.exists():
            return candidate

    raise RuntimeError(
        "Could not find gnpy-transmission-example executable. "
        "Check that GNPy is installed in the active Python environment."
    )


def run_gnpy_case(
    gnpy_exe: Path,
    spans: int,
    requested_launch_power_dbm: float,
) -> Path:
    network = Path(str(NETWORK_TEMPLATE).format(spans=spans))
    if not network.exists():
        raise RuntimeError(f"Missing GNPy network file: {network}")

    if not SPECTRUM_PATH.exists():
        raise RuntimeError(f"Missing GNPy spectrum file: {SPECTRUM_PATH}")

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    raw_path = RAW_DIR / f"gnpy_cband_launch_{p_label(requested_launch_power_dbm)}_{spans}span.txt"

    command = [
        str(gnpy_exe),
        "--show-channels",
        "-po",
        f"{requested_launch_power_dbm:.2f}",
        "--spectrum",
        str(SPECTRUM_PATH),
        str(network),
        "Site_A",
        "Site_B",
    ]

    completed = subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )

    raw_path.write_text(completed.stdout, encoding="utf-8")

    if completed.returncode != 0:
        raise RuntimeError(
            f"GNPy command failed for spans={spans}, power={requested_launch_power_dbm} dBm. "
            f"Output saved to {raw_path}"
        )

    return raw_path


def main() -> int:
    GENERATED.mkdir(parents=True, exist_ok=True)
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    gnpy_exe = locate_gnpy_transmission_exe()
    cfg = load_config()
    grid = build_grid(cfg["grid"])
    link = LinkModel(grid, cfg)

    reference_records: list[dict[str, Any]] = []
    comparison_records: list[dict[str, Any]] = []

    for requested_power in REQUESTED_LAUNCH_POWERS_DBM:
        launch_w = link.flat_launch_w(float(requested_power))

        for spans in SPANS:
            raw_path = run_gnpy_case(gnpy_exe, spans, requested_power)
            parsed = parse_gnpy_rows(raw_path)
            targets = nearest_rows_for_targets(parsed, TARGET_WAVELENGTHS_NM)

            result = link.evaluate_recursive(launch_w, spans)

            for item in targets:
                target_wl = float(item["target_wavelength_nm"])
                matched_wl_gnpy = float(item["wavelength_nm"])
                grid_index = int(grid.nearest_index_nm(matched_wl_gnpy))
                matched_wl_model = float(grid.wavelengths_nm[grid_index])

                model_gsnr = float(result.gsnr_db[grid_index])
                reference_gsnr = float(item["gnpy_gsnr_db"])
                residual = model_gsnr - reference_gsnr

                source_id = (
                    f"gnpy_cband_power_{p_label(requested_power)}_"
                    f"{spans}span_requested_{target_wl:.0f}nm_gsnr"
                )

                reference_records.append(
                    {
                        "source_id": source_id,
                        "source_type": "GNPy",
                        "tool_version": "2.14.1",
                        "provenance_reference": str(raw_path.relative_to(ROOT)).replace("\\", "/"),
                        "requested_launch_power_dbm": requested_power,
                        "spans": spans,
                        "target_wavelength_nm": target_wl,
                        "gnpy_wavelength_nm": matched_wl_gnpy,
                        "target_error_nm": float(item["target_error_nm"]),
                        "channel_frequency_thz": float(item["frequency_thz"]),
                        "gnpy_channel_power_dbm": float(item["channel_power_dbm"]),
                        "osnr_ase_signal_bw_db": float(item["osnr_ase_signal_bw_db"]),
                        "snr_nli_signal_bw_db": float(item["snr_nli_signal_bw_db"]),
                        "gnpy_gsnr_db": reference_gsnr,
                    }
                )

                comparison_records.append(
                    {
                        "source_id": source_id,
                        "requested_launch_power_dbm": requested_power,
                        "spans": spans,
                        "target_wavelength_nm": target_wl,
                        "gnpy_wavelength_nm": matched_wl_gnpy,
                        "model_matched_wavelength_nm": matched_wl_model,
                        "wavelength_error_model_minus_gnpy_nm": matched_wl_model - matched_wl_gnpy,
                        "gnpy_gsnr_db": reference_gsnr,
                        "model_recursive_gsnr_db": model_gsnr,
                        "residual_db": residual,
                        "abs_error_db": abs(residual),
                    }
                )

    ref_df = pd.DataFrame(reference_records)
    cmp_df = pd.DataFrame(comparison_records)

    ref_df.to_csv(REFERENCE_ROWS, index=False)
    cmp_df.to_csv(COMPARISON_ROWS, index=False)

    residuals = cmp_df["residual_db"].astype(float).tolist()
    summary = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "note": (
            "Compact C-band launch-power robustness experiment. "
            "This does not provide full S+C+L validation."
        ),
        "targets_nm": TARGET_WAVELENGTHS_NM,
        "spans": SPANS,
        "requested_launch_powers_dbm": REQUESTED_LAUNCH_POWERS_DBM,
        "rows": int(len(cmp_df)),
        "overall": metric_dict(residuals),
        "by_launch_power_dbm": grouped_metrics(cmp_df, "requested_launch_power_dbm"),
        "by_span": grouped_metrics(cmp_df, "spans"),
        "by_target_wavelength_nm": grouped_metrics(cmp_df, "target_wavelength_nm"),
        "outputs": {
            "reference_rows": str(REFERENCE_ROWS.relative_to(ROOT)),
            "comparison_rows": str(COMPARISON_ROWS.relative_to(ROOT)),
            "summary_json": str(SUMMARY_JSON.relative_to(ROOT)),
            "raw_output_dir": str(RAW_DIR.relative_to(ROOT)),
        },
        "claim_policy": (
            "Use this as C-band launch-power robustness evidence only. "
            "Do not claim S+C+L external validation from this experiment."
        ),
    }

    SUMMARY_JSON.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print(json.dumps(summary, indent=2))
    print()
    print(f"Wrote: {REFERENCE_ROWS}")
    print(f"Wrote: {COMPARISON_ROWS}")
    print(f"Wrote: {SUMMARY_JSON}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())