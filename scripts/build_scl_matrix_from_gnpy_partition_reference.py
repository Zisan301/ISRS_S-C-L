from __future__ import annotations

import json
import re
import sys
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

INPUT_PATH = ROOT / "external_validation" / "gnpy" / "scl_partition_reference_20260726.csv"
OUTPUT_PATH = ROOT / "releases" / "pnc-v1.0" / "validation_data" / "scl_external_validation_matrix.csv"
SUMMARY_PATH = ROOT / "releases" / "pnc-v1.0" / "generated" / "scl_external_validation_matrix_build_summary.json"

COLUMNS = [
    "source_id",
    "validation_split",
    "source_type",
    "tool_version",
    "configuration_hash",
    "date",
    "provenance_reference",
    "independent",
    "band",
    "wavelength_nm",
    "spans",
    "span_length_km",
    "channel_power_dbm",
    "metric",
    "metric_unit",
    "reference_value",
    "reference_uncertainty",
    "model_value",
    "matched_wavelength_nm",
    "wavelength_error_nm",
    "matched",
    "residual",
    "notes",
]


def load_config(path: Path) -> dict[str, Any]:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("Config YAML root must be a mapping")
    cfg = apply_defaults(raw)
    validate_config(cfg, base_dir=path.parent)
    return cfg


def extract_channel_power(notes: str) -> float:
    match = re.search(r"channel_power_dbm=([+-]?\d+(?:\.\d+)?)", str(notes))
    if match:
        return float(match.group(1))
    return float("nan")


def metric_dict(residuals: list[float]) -> dict[str, float | int | None]:
    if not residuals:
        return {
            "n": 0,
            "rmse_db": None,
            "mae_db": None,
            "bias_db": None,
            "max_abs_error_db": None,
        }

    arr = np.asarray(residuals, dtype=float)
    return {
        "n": int(arr.size),
        "rmse_db": float(np.sqrt(np.mean(arr**2))),
        "mae_db": float(np.mean(np.abs(arr))),
        "bias_db": float(np.mean(arr)),
        "max_abs_error_db": float(np.max(np.abs(arr))),
    }


def main() -> int:
    if not INPUT_PATH.exists():
        raise SystemExit(f"Missing input file: {INPUT_PATH}")

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY_PATH.parent.mkdir(parents=True, exist_ok=True)

    source = pd.read_csv(INPUT_PATH)

    cfg = load_config(ROOT / "config_q2_final.yaml")
    grid = build_grid(cfg["grid"])
    link = LinkModel(grid, cfg)
    launch = link.flat_launch_w(float(cfg["launch"]["flat_power_dbm_per_channel"]))
    span_length_km = float(cfg["fiber"]["span_length_km"])

    rows: list[dict[str, Any]] = []
    residuals: list[float] = []

    for item in source.to_dict(orient="records"):
        target_wavelength = float(item["wavelength_nm"])
        spans = int(item["spans"])
        channel = int(grid.nearest_index_nm(target_wavelength))
        matched_wavelength = float(grid.wavelengths_nm[channel])
        wavelength_error = matched_wavelength - target_wavelength

        result = link.evaluate_recursive(launch, spans)
        model_value = float(result.gsnr_db[channel])
        reference_value = float(item["reference_value"])
        residual = model_value - reference_value
        residuals.append(residual)

        notes = str(item.get("notes", ""))
        notes = (
            notes
            + " Converted into release S/C/L validation matrix from GNPy band-partition run. "
            + "Current default GNPy example contributes C-band rows only; S/L rows remain missing."
        )

        rows.append(
            {
                "source_id": item["source_id"],
                "validation_split": "heldout",
                "source_type": item["source_type"],
                "tool_version": item["tool_version"],
                "configuration_hash": item["configuration_hash"],
                "date": item["date"],
                "provenance_reference": item["provenance_reference"],
                "independent": str(item["independent"]).lower(),
                "band": item["band"],
                "wavelength_nm": f"{target_wavelength:.6f}",
                "spans": spans,
                "span_length_km": f"{span_length_km:.2f}",
                "channel_power_dbm": f"{extract_channel_power(item.get('notes', '')):.2f}",
                "metric": item["metric"],
                "metric_unit": item["metric_unit"],
                "reference_value": f"{reference_value:.6f}",
                "reference_uncertainty": item["reference_uncertainty"],
                "model_value": f"{model_value:.6f}",
                "matched_wavelength_nm": f"{matched_wavelength:.6f}",
                "wavelength_error_nm": f"{wavelength_error:.6f}",
                "matched": "true" if abs(wavelength_error) <= 1.0 else "false",
                "residual": f"{residual:.6f}",
                "notes": notes,
            }
        )

    out = pd.DataFrame(rows, columns=COLUMNS)
    out.to_csv(OUTPUT_PATH, index=False)

    summary = {
        "note": "This matrix currently contains real GNPy C-band rows only. It is not full S+C+L validation.",
        "input_file": str(INPUT_PATH.relative_to(ROOT)),
        "output_file": str(OUTPUT_PATH.relative_to(ROOT)),
        "rows": int(len(out)),
        "bands_present": sorted(out["band"].astype(str).unique().tolist()),
        "spans_present": sorted([int(x) for x in out["spans"].unique().tolist()]),
        "metrics": metric_dict(residuals),
        "claim_policy": "Do not claim full S+C+L validation until S, C, and L rows pass the SCL checker.",
    }

    SUMMARY_PATH.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print(json.dumps(summary, indent=2))
    print()
    print(f"Wrote: {OUTPUT_PATH}")
    print(f"Wrote: {SUMMARY_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())