from __future__ import annotations

import json
import math
import sys
from copy import deepcopy
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
GENERATED = ROOT / "releases" / "pnc-v1.0" / "generated"
ASSETS = GENERATED / "joc_revision_assets" / "generated"
BIAS_ROWS = GENERATED / "joc_bias_audit_rows.csv"
BIAS_SUMMARY = GENERATED / "joc_bias_audit_summary.json"
BIAS_TABLE = ASSETS / "table_bias_audit_summary.tex"
BIAS_CENTER_TABLE = ASSETS / "table_bias_audit_center_channels.tex"
POWER_OFFSETS_DB = [-2.0, 0.0, 2.0]
SPANS = [1, 4, 8]
TRANSCEIVER_SNR_DB = 40.0


def require(path: Path) -> Path:
    if not path.exists():
        raise FileNotFoundError(f"Missing required evidence file: {path}")
    return path


def dbm_from_w(power_w: np.ndarray | float) -> np.ndarray | float:
    return 10.0 * np.log10(np.asarray(power_w, dtype=float) / 1e-3)


def snr_db(signal_w: np.ndarray, noise_w: np.ndarray) -> np.ndarray:
    return 10.0 * np.log10(signal_w / np.maximum(noise_w, 1e-300))


def combine_snr_db(*terms_db: float | np.ndarray) -> np.ndarray:
    inv = np.zeros_like(np.asarray(terms_db[0], dtype=float), dtype=float)
    for term in terms_db:
        inv += 10.0 ** (-np.asarray(term, dtype=float) / 10.0)
    return -10.0 * np.log10(np.maximum(inv, 1e-300))


def metric(values: np.ndarray) -> dict[str, float | int]:
    v = np.asarray(values, dtype=float)
    return {
        "n": int(v.size),
        "mean_db": float(np.mean(v)),
        "median_db": float(np.median(v)),
        "mean_abs_db": float(np.mean(np.abs(v))),
        "rms_db": float(np.sqrt(np.mean(v**2))),
        "max_abs_db": float(np.max(np.abs(v))),
    }


def load_matched_config() -> dict[str, Any]:
    path = ROOT / "config_q2_final.yaml"
    raw = yaml.safe_load(require(path).read_text(encoding="utf-8"))
    cfg = apply_defaults(raw)
    cfg = deepcopy(cfg)
    cfg["modulation"]["symbol_rate_gbaud"] = 32.0
    cfg["modulation"]["roll_off"] = 0.15
    cfg["fiber"]["span_length_km"] = 80.0
    cfg["fiber"]["attenuation_anchors"] = {
        "wavelength_nm": [1460.0, 1530.0, 1550.0, 1565.0, 1625.0],
        "db_per_km": [0.2, 0.2, 0.2, 0.2, 0.2],
    }
    cfg["raman"]["pumps"] = []
    cfg["nli"]["transceiver_snr_db"] = TRANSCEIVER_SNR_DB
    validate_config(cfg, base_dir=path.parent)
    return cfg


def exact_grid_from_reported(frame: pd.DataFrame) -> OpticalGrid:
    reported_hz = frame.sort_values("frequency_thz")["frequency_thz"].to_numpy(float) * 1e12
    spacing = float(np.median(np.diff(reported_hz)))
    frequencies = reported_hz[0] + spacing * np.arange(reported_hz.size, dtype=float)
    wavelengths = C / frequencies * 1e9
    bands = band_from_wavelength(wavelengths)
    return OpticalGrid(frequencies, wavelengths, bands, spacing, "gnpy_matched_cband_bias_audit")


def latex_table_summary(summary: dict[str, Any]) -> str:
    rows = [
        ("GSNR residual, model $-$ GNPy", summary["residual_db"]),
        ("ASE-SNR gap, model $-$ GNPy", summary["ase_snr_gap_db"]),
        ("NLI-SNR gap, model $-$ GNPy", summary["nli_snr_gap_db"]),
        ("Signal-power gap, model output $-$ GNPy report", summary["signal_power_gap_db"]),
        ("GNPy report reconstruction gap", summary["gnpy_reconstruction_gap_db"]),
    ]
    body = []
    for label, values in rows:
        body.append(
            f"{label} & {values['mean_db']:.4f} & {values['median_db']:.4f} & "
            f"{values['rms_db']:.4f} & {values['max_abs_db']:.4f} \\\\"
        )
    return """\\begin{table}[htbp]
\\centering
\\caption{Bias audit for the scenario-matched C-band comparison. Positive component gaps mean the recursive model reports a higher component SNR or signal power than the GNPy route report. The GNPy reconstruction gap compares GNPy's printed GSNR with the GSNR reconstructed from its printed ASE, NLI and 40-dB transceiver terms.}
\\label{tab:bias-audit}
\\small
\\begin{tabular}{@{}lrrrr@{}}
\\toprule
Audit quantity & Mean, dB & Median, dB & RMS, dB & Max. abs., dB \\\\
\\midrule
""" + "\n".join(body) + """
\\bottomrule
\\end{tabular}
\\end{table}
"""


def latex_table_center_channels(center: pd.DataFrame) -> str:
    display = center.copy()
    display["abs_wl"] = (display["gnpy_wavelength_nm"] - 1550.0).abs()
    display = display.sort_values(["spans", "requested_power_offset_db", "abs_wl"])
    rows = []
    for _, row in display.iterrows():
        rows.append(
            f"{row['requested_power_offset_db']:+.0f} & {int(row['spans'])} & "
            f"{row['gnpy_wavelength_nm']:.3f} & {row['residual_db']:.4f} & "
            f"{row['ase_snr_gap_db']:.4f} & {row['nli_snr_gap_db']:.4f} & "
            f"{row['signal_power_gap_db']:.4f} \\\\"
        )
    return """\\begin{table}[htbp]
\\centering
\\caption{Centre-channel bias audit rows nearest 1550 nm. The one- and eight-span cases are the most direct checks requested by the review audit; four-span rows are retained for continuity across the reproduced matrix.}
\\label{tab:bias-audit-center}
\\small
\\begin{tabular}{@{}rrrrrrr@{}}
\\toprule
Offset, dB & Spans & Wavelength, nm & GSNR residual & ASE gap & NLI gap & Signal gap \\\\
\\midrule
""" + "\n".join(rows) + """
\\bottomrule
\\end{tabular}
\\end{table}
"""


def main() -> int:
    ASSETS.mkdir(parents=True, exist_ok=True)
    reference = pd.read_csv(require(GENERATED / "cband_launch_power_sweep_reference_rows.csv"))
    comparison = pd.read_csv(require(GENERATED / "cband_launch_power_sweep_model_comparison.csv"))
    summary = json.loads(require(GENERATED / "cband_launch_power_sweep_summary.json").read_text(encoding="utf-8"))
    cfg = load_matched_config()

    records: list[dict[str, Any]] = []
    for (offset, spans), group in reference.groupby(["requested_power_offset_db", "spans"], sort=True):
        group = group.sort_values("frequency_thz").reset_index(drop=True)
        grid = exact_grid_from_reported(group)
        effective_power = float(group["gnpy_effective_channel_power_dbm"].median())
        link = LinkModel(grid, cfg)
        result = link.evaluate_recursive(link.flat_launch_w(effective_power), int(spans))
        signal_w = np.asarray(result.launch_power_w, dtype=float)
        model_ase_snr = snr_db(signal_w, np.asarray(result.noise_budget.ase_receiver_w, dtype=float))
        model_nli_snr = snr_db(signal_w, np.asarray(result.nli_w, dtype=float))
        model_trx_snr = snr_db(signal_w, np.asarray(result.transceiver_noise_w, dtype=float))
        model_signal_dbm = dbm_from_w(signal_w)

        comp = comparison[
            (comparison["requested_power_offset_db"] == offset)
            & (comparison["spans"] == spans)
        ].sort_values("frequency_thz").reset_index(drop=True)
        if len(comp) != len(group):
            raise RuntimeError(f"Row mismatch for offset={offset}, spans={spans}")

        gnpy_combined = combine_snr_db(
            group["osnr_ase_signal_bw_db"].to_numpy(float),
            group["snr_nli_signal_bw_db"].to_numpy(float),
            np.full(len(group), TRANSCEIVER_SNR_DB),
        )
        for idx, item in group.iterrows():
            row = comp.loc[idx]
            # cband_launch_power_sweep_reference_rows.csv stores the per-condition
            # median reported power as gnpy_effective_channel_power_dbm. Older raw
            # parser frames used gnpy_channel_power_dbm. Accept both names so the
            # bias audit is robust to either evidence schema. The power sweep already
            # enforces <= 0.10 dB channel-power spread, and the observed spread is
            # <= 0.01 dB, so the effective value is the correct manuscript-level
            # signal-power reference.
            if "gnpy_channel_power_dbm" in item.index:
                gnpy_power_dbm = float(item["gnpy_channel_power_dbm"])
            elif "gnpy_effective_channel_power_dbm" in item.index:
                gnpy_power_dbm = float(item["gnpy_effective_channel_power_dbm"])
            elif "gnpy_effective_channel_power_dbm" in row.index:
                gnpy_power_dbm = float(row["gnpy_effective_channel_power_dbm"])
            else:
                raise KeyError(
                    "Could not find a GNPy channel/effective power column in the bias-audit inputs"
                )

            records.append(
                {
                    "source_id": row["source_id"],
                    "requested_power_offset_db": float(offset),
                    "spans": int(spans),
                    "channel": int(item["channel"]),
                    "gnpy_wavelength_nm": float(item["gnpy_wavelength_nm"]),
                    "gnpy_channel_power_dbm": gnpy_power_dbm,
                    "model_signal_power_dbm": float(model_signal_dbm[idx]),
                    "signal_power_gap_db": float(model_signal_dbm[idx] - gnpy_power_dbm),
                    "gnpy_ase_snr_db": float(item["osnr_ase_signal_bw_db"]),
                    "model_ase_snr_db": float(model_ase_snr[idx]),
                    "ase_snr_gap_db": float(model_ase_snr[idx] - item["osnr_ase_signal_bw_db"]),
                    "gnpy_nli_snr_db": float(item["snr_nli_signal_bw_db"]),
                    "model_nli_snr_db": float(model_nli_snr[idx]),
                    "nli_snr_gap_db": float(model_nli_snr[idx] - item["snr_nli_signal_bw_db"]),
                    "model_trx_snr_db": float(model_trx_snr[idx]),
                    "gnpy_reconstructed_gsnr_db": float(gnpy_combined[idx]),
                    "gnpy_reported_gsnr_db": float(item["gnpy_gsnr_db"]),
                    "gnpy_reconstruction_gap_db": float(gnpy_combined[idx] - item["gnpy_gsnr_db"]),
                    "model_gsnr_db": float(row["model_recursive_gsnr_db"]),
                    "residual_db": float(row["residual_db"]),
                }
            )

    frame = pd.DataFrame(records)
    frame.to_csv(BIAS_ROWS, index=False)

    audit_summary = {
        "note": "Bias audit for the scenario-matched C-band matrix. GNPy component terms are taken from the route report; model component terms are computed from the recursive LinkResult noise budget. Signal-power comparison uses the GNPy per-channel power when present, otherwise the per-condition effective reported channel power used by the aligned sweep. This audit identifies candidate sources for the systematic offset but is not experimental calibration.",
        "rows": int(len(frame)),
        "operating_conditions": int(frame.groupby(["requested_power_offset_db", "spans"]).ngroups),
        "residual_db": metric(frame["residual_db"].to_numpy(float)),
        "ase_snr_gap_db": metric(frame["ase_snr_gap_db"].to_numpy(float)),
        "nli_snr_gap_db": metric(frame["nli_snr_gap_db"].to_numpy(float)),
        "signal_power_gap_db": metric(frame["signal_power_gap_db"].to_numpy(float)),
        "gnpy_reconstruction_gap_db": metric(frame["gnpy_reconstruction_gap_db"].to_numpy(float)),
        "centre_channel_rows": "releases/pnc-v1.0/generated/joc_bias_audit_rows.csv",
        "interpretation_rule": "A component gap whose mean has the same sign and similar magnitude to the GSNR residual is a stronger candidate for the constant offset. If several terms are comparable, the audit should be reported as unresolved multi-parameter/device-model bias rather than forced attribution.",
        "principal_results_from_sweep": summary["overall"],
    }
    BIAS_SUMMARY.write_text(json.dumps(audit_summary, indent=2), encoding="utf-8")
    BIAS_TABLE.write_text(latex_table_summary(audit_summary), encoding="utf-8")

    centre_rows = []
    for (offset, spans), group in frame.groupby(["requested_power_offset_db", "spans"], sort=True):
        idx = (group["gnpy_wavelength_nm"] - 1550.0).abs().idxmin()
        centre_rows.append(frame.loc[idx])
    centre = pd.DataFrame(centre_rows)
    BIAS_CENTER_TABLE.write_text(latex_table_center_channels(centre), encoding="utf-8")

    print(json.dumps(audit_summary, indent=2))
    print(f"Wrote {BIAS_ROWS}")
    print(f"Wrote {BIAS_SUMMARY}")
    print(f"Wrote {BIAS_TABLE}")
    print(f"Wrote {BIAS_CENTER_TABLE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
