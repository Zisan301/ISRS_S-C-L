from __future__ import annotations

import json
import re
import subprocess
import sys
import sysconfig
from copy import deepcopy
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
from isrs_scl.system.grid import OpticalGrid, band_from_wavelength
from isrs_scl.system.parameters import apply_defaults, validate_config

C = 299792458.0
SPANS = [1, 4, 8]
POWER_OFFSETS_DB = [-2.0, 0.0, 2.0]
POWER_UNIFORMITY_TOLERANCE_DB = 0.10

GENERATED = ROOT / "releases" / "pnc-v1.0" / "generated"
RAW_DIR = GENERATED / "gnpy_cband_launch_power_raw"
REFERENCE_ROWS = GENERATED / "cband_launch_power_sweep_reference_rows.csv"
COMPARISON_ROWS = GENERATED / "cband_launch_power_sweep_model_comparison.csv"
ANCHOR_ROWS = GENERATED / "cband_launch_power_sweep_anchor_comparison.csv"
SUMMARY_JSON = GENERATED / "cband_launch_power_sweep_summary.json"

# This spectrum asks GNPy for S+C+L partitions. The default example equipment
# propagates its supported C-band block (about 63 channels). We intentionally
# use the propagated block and construct the model on the exact same frequencies.
SPECTRUM_PATH = ROOT / "external_validation" / "gnpy" / "cases" / "scl_band_partition_flat_spectrum.json"
NETWORK_TEMPLATE = ROOT / "external_validation" / "gnpy" / "cases" / "gnpy_flat_{spans}span_network.json"
ANCHOR_WAVELENGTHS_NM = [1535.0, 1550.0, 1560.0]


def offset_label(value: float) -> str:
    if value < 0:
        return f"m{abs(value):.0f}"
    if value > 0:
        return f"p{value:.0f}"
    return "p0"


def read_text_robust(path: Path) -> str:
    data = path.read_bytes()
    for encoding in ("utf-8-sig", "utf-16", "utf-16-le", "cp1252"):
        try:
            text = data.decode(encoding)
            if "The GSNR per channel" in text or "Channel frequency" in text:
                return text.replace("\x00", "")
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace").replace("\x00", "")


def parse_gnpy_rows(path: Path) -> pd.DataFrame:
    clean = re.sub(r"\x1b\[[0-9;]*m", "", read_text_robust(path))
    records: list[dict[str, float | int]] = []
    pattern = re.compile(
        r"\s*(\d+)\s+([0-9.]+)\s+(-?[0-9.]+)\s+([0-9.]+)\s+([0-9.]+)\s+([0-9.]+)\s*$"
    )
    for line in clean.splitlines():
        match = pattern.match(line)
        if not match:
            continue
        frequency_thz = float(match.group(2))
        records.append(
            {
                "channel": int(match.group(1)),
                "frequency_thz": frequency_thz,
                "wavelength_nm": C / (frequency_thz * 1e12) * 1e9,
                "gnpy_channel_power_dbm": float(match.group(3)),
                "osnr_ase_signal_bw_db": float(match.group(4)),
                "snr_nli_signal_bw_db": float(match.group(5)),
                "gnpy_gsnr_db": float(match.group(6)),
            }
        )
    if not records:
        raise RuntimeError(f"No GNPy channel rows found in {path}")
    frame = pd.DataFrame(records).sort_values("frequency_thz").reset_index(drop=True)
    if len(frame) < 3:
        raise RuntimeError(f"Expected a loaded C-band block, found only {len(frame)} channels in {path}")
    return frame


def exact_grid_from_gnpy(frame: pd.DataFrame) -> OpticalGrid:
    reported = frame["frequency_thz"].to_numpy(float) * 1e12
    spacing = float(np.median(np.diff(reported)))
    if spacing <= 0:
        raise RuntimeError("GNPy frequencies are not strictly increasing")
    # Printed GNPy frequencies are rounded. Rebuild an exact uniform grid from
    # the first printed frequency and the median channel spacing.
    frequencies = reported[0] + spacing * np.arange(reported.size, dtype=float)
    wavelengths = C / frequencies * 1e9
    bands = band_from_wavelength(wavelengths)
    if np.any(bands != "C"):
        raise RuntimeError("The propagated GNPy block is not purely C band")
    return OpticalGrid(frequencies, wavelengths, bands, spacing, "gnpy_matched_cband")


def load_matched_config() -> dict[str, Any]:
    path = ROOT / "config_q2_final.yaml"
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    cfg = apply_defaults(raw)
    cfg = deepcopy(cfg)
    # Align the explicitly known operating conditions with the GNPy spectrum
    # and topology used here. Device-internal models remain independently
    # implemented and are not claimed to be identical.
    cfg["modulation"]["symbol_rate_gbaud"] = 32.0
    cfg["modulation"]["roll_off"] = 0.15
    cfg["fiber"]["span_length_km"] = 80.0
    cfg["fiber"]["attenuation_anchors"] = {
        "wavelength_nm": [1460.0, 1530.0, 1550.0, 1565.0, 1625.0],
        "db_per_km": [0.2, 0.2, 0.2, 0.2, 0.2],
    }
    cfg["raman"]["pumps"] = []
    cfg["nli"]["transceiver_snr_db"] = 40.0
    validate_config(cfg, base_dir=path.parent)
    return cfg


def locate_gnpy_executable() -> Path:
    scripts_dir = Path(sysconfig.get_path("scripts"))
    for name in ("gnpy-transmission-example.exe", "gnpy-transmission-example"):
        candidate = scripts_dir / name
        if candidate.exists():
            return candidate
    raise RuntimeError("GNPy executable not found in the active Python environment")


def run_gnpy_case(executable: Path, spans: int, offset_db: float) -> Path:
    network = Path(str(NETWORK_TEMPLATE).format(spans=spans))
    if not network.exists():
        raise RuntimeError(f"Missing GNPy network: {network}")
    if not SPECTRUM_PATH.exists():
        raise RuntimeError(f"Missing GNPy spectrum: {SPECTRUM_PATH}")
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    raw_path = RAW_DIR / f"gnpy_cband_offset_{offset_label(offset_db)}_{spans}span.txt"
    command = [
        str(executable),
        "--show-channels",
        "-po",
        f"{offset_db:.2f}",
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
        raise RuntimeError(f"GNPy failed for spans={spans}, offset={offset_db:+.1f} dB; see {raw_path}")
    return raw_path


def metric_dict(residuals: np.ndarray) -> dict[str, float | int]:
    values = np.asarray(residuals, dtype=float)
    return {
        "n": int(values.size),
        "rmse_db": float(np.sqrt(np.mean(values**2))),
        "mae_db": float(np.mean(np.abs(values))),
        "bias_db": float(np.mean(values)),
        "max_abs_error_db": float(np.max(np.abs(values))),
    }


def grouped_metrics(frame: pd.DataFrame, column: str) -> dict[str, dict[str, float | int]]:
    output: dict[str, dict[str, float | int]] = {}
    for key, group in frame.groupby(column, sort=True):
        output[str(key)] = metric_dict(group["residual_db"].to_numpy(float))
    return output


def nearest_anchor_rows(frame: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (offset, spans), group in frame.groupby(["requested_power_offset_db", "spans"], sort=True):
        for target in ANCHOR_WAVELENGTHS_NM:
            index = (group["gnpy_wavelength_nm"] - target).abs().idxmin()
            row = group.loc[index].copy()
            row["requested_anchor_wavelength_nm"] = target
            rows.append(row)
    return pd.DataFrame(rows)


def main() -> int:
    GENERATED.mkdir(parents=True, exist_ok=True)
    executable = locate_gnpy_executable()
    cfg = load_matched_config()

    reference_records: list[dict[str, Any]] = []
    comparison_records: list[dict[str, Any]] = []
    audit_records: list[dict[str, Any]] = []

    for offset_db in POWER_OFFSETS_DB:
        for spans in SPANS:
            raw_path = run_gnpy_case(executable, spans, offset_db)
            gnpy = parse_gnpy_rows(raw_path)
            grid = exact_grid_from_gnpy(gnpy)

            power_values = gnpy["gnpy_channel_power_dbm"].to_numpy(float)
            effective_power_dbm = float(np.median(power_values))
            spread_db = float(np.max(power_values) - np.min(power_values))
            if spread_db > POWER_UNIFORMITY_TOLERANCE_DB:
                raise RuntimeError(
                    f"GNPy channel power spread {spread_db:.3f} dB exceeds "
                    f"{POWER_UNIFORMITY_TOLERANCE_DB:.3f} dB for offset={offset_db}, spans={spans}"
                )

            link = LinkModel(grid, cfg)
            launch = link.flat_launch_w(effective_power_dbm)
            result = link.evaluate_recursive(launch, spans)

            audit_records.append(
                {
                    "requested_power_offset_db": offset_db,
                    "spans": spans,
                    "gnpy_effective_channel_power_dbm": effective_power_dbm,
                    "model_launch_power_dbm": effective_power_dbm,
                    "channel_power_spread_db": spread_db,
                    "channels": int(len(gnpy)),
                    "raw_file": str(raw_path.relative_to(ROOT)).replace("\\", "/"),
                }
            )

            for row_index, item in gnpy.iterrows():
                model_wavelength = float(grid.wavelengths_nm[row_index])
                model_gsnr = float(result.gsnr_db[row_index])
                reference_gsnr = float(item["gnpy_gsnr_db"])
                residual = model_gsnr - reference_gsnr
                source_id = f"gnpy_matched_offset_{offset_label(offset_db)}_{spans}span_ch{int(item['channel'])}"

                reference_records.append(
                    {
                        "source_id": source_id,
                        "source_type": "GNPy",
                        "tool_version": "2.14.1",
                        "requested_power_offset_db": offset_db,
                        "gnpy_effective_channel_power_dbm": effective_power_dbm,
                        "spans": spans,
                        "channel": int(item["channel"]),
                        "frequency_thz": float(item["frequency_thz"]),
                        "gnpy_wavelength_nm": float(item["wavelength_nm"]),
                        "osnr_ase_signal_bw_db": float(item["osnr_ase_signal_bw_db"]),
                        "snr_nli_signal_bw_db": float(item["snr_nli_signal_bw_db"]),
                        "gnpy_gsnr_db": reference_gsnr,
                        "provenance_reference": str(raw_path.relative_to(ROOT)).replace("\\", "/"),
                    }
                )
                comparison_records.append(
                    {
                        "source_id": source_id,
                        "requested_power_offset_db": offset_db,
                        "gnpy_effective_channel_power_dbm": effective_power_dbm,
                        "model_launch_power_dbm": effective_power_dbm,
                        "spans": spans,
                        "channel": int(item["channel"]),
                        "frequency_thz": float(item["frequency_thz"]),
                        "gnpy_wavelength_nm": float(item["wavelength_nm"]),
                        "model_wavelength_nm": model_wavelength,
                        "wavelength_error_nm": model_wavelength - float(item["wavelength_nm"]),
                        "gnpy_gsnr_db": reference_gsnr,
                        "model_recursive_gsnr_db": model_gsnr,
                        "residual_db": residual,
                        "abs_error_db": abs(residual),
                    }
                )

    reference = pd.DataFrame(reference_records)
    comparison = pd.DataFrame(comparison_records)
    audit = pd.DataFrame(audit_records)
    anchors = nearest_anchor_rows(comparison)

    reference.to_csv(REFERENCE_ROWS, index=False)
    comparison.to_csv(COMPARISON_ROWS, index=False)
    anchors.to_csv(ANCHOR_ROWS, index=False)

    condition_metrics = []
    for (offset, spans), group in comparison.groupby(["requested_power_offset_db", "spans"], sort=True):
        metrics = metric_dict(group["residual_db"].to_numpy(float))
        audit_row = audit[(audit["requested_power_offset_db"] == offset) & (audit["spans"] == spans)].iloc[0]
        condition_metrics.append(
            {
                "requested_power_offset_db": float(offset),
                "gnpy_effective_channel_power_dbm": float(audit_row["gnpy_effective_channel_power_dbm"]),
                "spans": int(spans),
                **metrics,
            }
        )

    summary = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "note": (
            "Power- and loading-aligned C-band cross-tool robustness study. "
            "The model uses the exact GNPy-propagated C-band frequencies, the GNPy-reported effective "
            "channel power, 32 GBd, roll-off 0.15, 80-km spans, 0.2 dB/km loss, no external Raman pumps, "
            "and 40 dB transceiver SNR. Device-internal models remain independently implemented."
        ),
        "requested_power_offsets_db": POWER_OFFSETS_DB,
        "spans": SPANS,
        "channels_per_condition": int(comparison["channel"].nunique()),
        "operating_conditions": int(len(condition_metrics)),
        "rows": int(len(comparison)),
        "overall": metric_dict(comparison["residual_db"].to_numpy(float)),
        "by_requested_power_offset_db": grouped_metrics(comparison, "requested_power_offset_db"),
        "by_effective_launch_power_dbm": grouped_metrics(comparison, "gnpy_effective_channel_power_dbm"),
        "by_span": grouped_metrics(comparison, "spans"),
        "condition_metrics": condition_metrics,
        "power_reference_audit": audit.to_dict(orient="records"),
        "max_abs_wavelength_error_nm": float(np.max(np.abs(comparison["wavelength_error_nm"].to_numpy(float)))),
        "outputs": {
            "reference_rows": str(REFERENCE_ROWS.relative_to(ROOT)),
            "comparison_rows": str(COMPARISON_ROWS.relative_to(ROOT)),
            "anchor_rows": str(ANCHOR_ROWS.relative_to(ROOT)),
            "raw_output_dir": str(RAW_DIR.relative_to(ROOT)),
        },
        "claim_policy": (
            "This supports C-band cross-tool robustness under aligned power and loading. "
            "It does not establish full S+C+L, SSFM, experimental, or identical-device-model validation."
        ),
    }
    SUMMARY_JSON.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    print(f"Wrote {COMPARISON_ROWS}")
    print(f"Wrote {ANCHOR_ROWS}")
    print(f"Wrote {SUMMARY_JSON}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

