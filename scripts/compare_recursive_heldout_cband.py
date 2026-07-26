"""Compare frozen analytical held-out evidence against current recursive evaluation.

This script does not claim final journal validation. It checks whether the old
C-band held-out GNPy comparison changes after switching the model path from
analytical multi-span scaling to recursive span-by-span propagation.
"""

from __future__ import annotations

import json
import os
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


def rmse(x: np.ndarray) -> float:
    return float(np.sqrt(np.mean(np.asarray(x, dtype=float) ** 2)))


def metrics(residual: np.ndarray) -> dict[str, float]:
    residual = np.asarray(residual, dtype=float)
    return {
        "n": int(residual.size),
        "rmse_db": rmse(residual),
        "mae_db": float(np.mean(np.abs(residual))),
        "bias_db": float(np.mean(residual)),
        "max_abs_error_db": float(np.max(np.abs(residual))),
    }


def load_config(path: Path) -> dict[str, Any]:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("Config root must be a mapping")
    cfg = apply_defaults(raw)
    cfg["grid"]["mode"] = "paper_240_subset"
    validate_config(cfg, base_dir=path.parent)
    return cfg


def parse_residual_correction(metrics_json: dict[str, Any]) -> tuple[float, float, float]:
    formula = str(metrics_json["residual_correction"]["formula"])
    # Example: r_hat(lambda) = 2.5433 - 0.008743*(lambda - 1550) dB
    match = re.search(
        r"=\s*([+-]?\d+(?:\.\d+)?)\s*([+-])\s*(\d+(?:\.\d+)?)\*\(lambda\s*-\s*(\d+(?:\.\d+)?)\)",
        formula,
    )
    if not match:
        raise ValueError(f"Could not parse residual correction formula: {formula}")

    intercept = float(match.group(1))
    sign = -1.0 if match.group(2) == "-" else 1.0
    slope = sign * float(match.group(3))
    center_nm = float(match.group(4))
    return intercept, slope, center_nm


def correction_db(wavelength_nm: np.ndarray, intercept: float, slope: float, center_nm: float) -> np.ndarray:
    return intercept + slope * (np.asarray(wavelength_nm, dtype=float) - center_nm)


def main() -> int:
    output_dir = Path(os.environ.get("PNC_RESULTS_DIR", ROOT / "releases" / "pnc-v1.0" / "results"))
    output_dir.mkdir(parents=True, exist_ok=True)

    heldout_path = ROOT / "releases" / "pnc-v1.0" / "validation_data" / "heldout_row_level_comparison.csv"
    metrics_path = ROOT / "releases" / "pnc-v1.0" / "validation_data" / "validation_metrics.json"

    heldout = pd.read_csv(heldout_path)
    metrics_json = json.loads(metrics_path.read_text(encoding="utf-8-sig"))

    intercept, slope, center_nm = parse_residual_correction(metrics_json)

    cfg = load_config(ROOT / "config_q2_final.yaml")
    grid = build_grid(cfg["grid"])
    link = LinkModel(grid, cfg)
    launch = link.flat_launch_w(float(cfg["launch"]["flat_power_dbm_per_channel"]))

    rows: list[dict[str, Any]] = []

    for item in heldout.to_dict(orient="records"):
        spans = int(item["spans"])
        target_wavelength = float(item["wavelength_nm"])
        channel = int(grid.nearest_index_nm(target_wavelength))
        actual_wavelength = float(grid.wavelengths_nm[channel])

        analytical = link.evaluate(launch, spans)
        recursive = link.evaluate_recursive(launch, spans)

        analytical_raw = float(analytical.gsnr_db[channel])
        recursive_raw = float(recursive.gsnr_db[channel])

        analytical_corr = analytical_raw - float(correction_db(np.array([target_wavelength]), intercept, slope, center_nm)[0])
        recursive_corr = recursive_raw - float(correction_db(np.array([target_wavelength]), intercept, slope, center_nm)[0])

        gnpy = float(item["gnpy_gsnr_db"])

        rows.append(
            {
                "spans": spans,
                "target_wavelength_nm": target_wavelength,
                "nearest_grid_channel": channel,
                "nearest_grid_wavelength_nm": actual_wavelength,
                "wavelength_error_nm": actual_wavelength - target_wavelength,
                "gnpy_gsnr_db": gnpy,

                "frozen_raw_model_gsnr_db": float(item["raw_model_gsnr_db"]),
                "current_analytical_raw_model_gsnr_db": analytical_raw,
                "current_recursive_raw_model_gsnr_db": recursive_raw,

                "frozen_corrected_model_gsnr_db": float(item["corrected_model_gsnr_db"]),
                "current_analytical_corrected_model_gsnr_db": analytical_corr,
                "current_recursive_corrected_model_gsnr_db": recursive_corr,

                "frozen_raw_residual_db": float(item["raw_residual_db"]),
                "current_analytical_raw_residual_db": analytical_raw - gnpy,
                "current_recursive_raw_residual_db": recursive_raw - gnpy,

                "frozen_corrected_residual_db": float(item["corrected_residual_db"]),
                "current_analytical_corrected_residual_db": analytical_corr - gnpy,
                "current_recursive_corrected_residual_db": recursive_corr - gnpy,

                "recursive_minus_analytical_raw_db": recursive_raw - analytical_raw,
                "recursive_minus_frozen_raw_db": recursive_raw - float(item["raw_model_gsnr_db"]),
            }
        )

    frame = pd.DataFrame(rows)

    summary = {
        "note": "Diagnostic comparison only; this is not final journal evidence.",
        "config": "config_q2_final.yaml",
        "grid_mode": cfg["grid"]["mode"],
        "n_channels": int(grid.n_channels),
        "residual_correction": {
            "intercept_db": intercept,
            "slope_db_per_nm": slope,
            "center_nm": center_nm,
            "warning": "Same old wavelength-linear post-model correction is applied for comparability only.",
        },
        "frozen_raw": metrics(frame["frozen_raw_residual_db"].to_numpy(float)),
        "frozen_corrected": metrics(frame["frozen_corrected_residual_db"].to_numpy(float)),
        "current_analytical_raw": metrics(frame["current_analytical_raw_residual_db"].to_numpy(float)),
        "current_analytical_corrected": metrics(frame["current_analytical_corrected_residual_db"].to_numpy(float)),
        "current_recursive_raw": metrics(frame["current_recursive_raw_residual_db"].to_numpy(float)),
        "current_recursive_corrected": metrics(frame["current_recursive_corrected_residual_db"].to_numpy(float)),
        "recursive_vs_analytical": metrics(frame["recursive_minus_analytical_raw_db"].to_numpy(float)),
        "max_abs_wavelength_error_nm": float(np.max(np.abs(frame["wavelength_error_nm"].to_numpy(float)))),
        "decision": (
            "If recursive corrected error is materially worse than frozen corrected error, "
            "the manuscript numbers must be regenerated and the old 0.389 dB claim must not be reused."
        ),
    }

    frame_path = output_dir / "recursive_heldout_cband_row_comparison.csv"
    summary_path = output_dir / "recursive_heldout_cband_metrics.json"

    frame.to_csv(frame_path, index=False)
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print(json.dumps(summary, indent=2))
    print()
    print("Wrote:")
    print(frame_path)
    print(summary_path)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
