"""Train recursive residual correction on calibration rows and test on held-out rows.

This script uses:
- calibration rows: preliminary_cband_external_validation_comparisons.csv
- held-out rows: heldout_row_level_comparison.csv

It evaluates the current recursive model, fits correction candidates using only
calibration rows, reports leave-one-out calibration error, then applies the same
correction to held-out rows.
"""

from __future__ import annotations

import json
import os
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


def load_config(path: Path) -> dict[str, Any]:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("Config YAML root must be a mapping")
    cfg = apply_defaults(raw)
    cfg["grid"]["mode"] = "paper_240_subset"
    validate_config(cfg, base_dir=path.parent)
    return cfg


def design_matrix(wavelength_nm: np.ndarray, spans: np.ndarray, model: str) -> np.ndarray:
    wl = np.asarray(wavelength_nm, dtype=float)
    sp = np.asarray(spans, dtype=float)

    if model == "none":
        return np.zeros((wl.size, 0))
    if model == "constant":
        return np.ones((wl.size, 1))
    if model == "wavelength_linear":
        return np.column_stack([np.ones(wl.size), wl - 1550.0])
    if model == "span_log_linear":
        return np.column_stack([np.ones(wl.size), np.log10(sp)])
    if model == "wavelength_span_linear":
        return np.column_stack([np.ones(wl.size), wl - 1550.0, np.log10(sp)])

    raise ValueError(f"Unknown correction model: {model}")


def fit_predict(
    train_wavelength: np.ndarray,
    train_spans: np.ndarray,
    train_residual: np.ndarray,
    test_wavelength: np.ndarray,
    test_spans: np.ndarray,
    model: str,
) -> tuple[np.ndarray, list[float]]:
    if model == "none":
        return np.zeros_like(np.asarray(test_wavelength, dtype=float)), []

    x_train = design_matrix(train_wavelength, train_spans, model)
    x_test = design_matrix(test_wavelength, test_spans, model)

    coef, *_ = np.linalg.lstsq(x_train, train_residual, rcond=None)
    pred = x_test @ coef
    return pred, [float(x) for x in coef]


def metric_dict(residual: np.ndarray) -> dict[str, float]:
    residual = np.asarray(residual, dtype=float)
    return {
        "n": int(residual.size),
        "rmse_db": float(np.sqrt(np.mean(residual**2))),
        "mae_db": float(np.mean(np.abs(residual))),
        "bias_db": float(np.mean(residual)),
        "max_abs_error_db": float(np.max(np.abs(residual))),
    }


def leave_one_out(frame: pd.DataFrame, model: str) -> dict[str, Any]:
    residuals: list[float] = []

    for idx in frame.index:
        train = frame.drop(index=idx)
        test = frame.loc[[idx]]

        pred, _ = fit_predict(
            train["wavelength_nm"].to_numpy(float),
            train["spans"].to_numpy(float),
            train["recursive_raw_residual_db"].to_numpy(float),
            test["wavelength_nm"].to_numpy(float),
            test["spans"].to_numpy(float),
            model,
        )

        corrected_residual = float(test["recursive_raw_residual_db"].iloc[0] - pred[0])
        residuals.append(corrected_residual)

    return metric_dict(np.asarray(residuals, dtype=float))


def evaluate_rows(source: pd.DataFrame, link: LinkModel, launch: np.ndarray, reference_column: str) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []

    for item in source.to_dict(orient="records"):
        spans = int(item["spans"])
        target_wavelength = float(item["wavelength_nm"])
        channel = int(link.grid.nearest_index_nm(target_wavelength))
        nearest_wavelength = float(link.grid.wavelengths_nm[channel])
        reference = float(item[reference_column])

        result = link.evaluate_recursive(launch, spans)
        recursive_raw = float(result.gsnr_db[channel])

        rows.append(
            {
                "spans": spans,
                "wavelength_nm": target_wavelength,
                "nearest_grid_channel": channel,
                "nearest_grid_wavelength_nm": nearest_wavelength,
                "wavelength_error_nm": nearest_wavelength - target_wavelength,
                "gnpy_gsnr_db": reference,
                "recursive_raw_model_gsnr_db": recursive_raw,
                "recursive_raw_residual_db": recursive_raw - reference,
            }
        )

    return pd.DataFrame(rows)


def main() -> int:
    validation_dir = ROOT / "releases" / "pnc-v1.0" / "validation_data"
    output_dir = Path(os.environ.get("PNC_RESULTS_DIR", ROOT / "releases" / "pnc-v1.0" / "results"))
    output_dir.mkdir(parents=True, exist_ok=True)

    calibration_path = validation_dir / "preliminary_cband_external_validation_comparisons.csv"
    heldout_path = validation_dir / "heldout_row_level_comparison.csv"

    calibration_source = pd.read_csv(calibration_path)
    calibration_source = calibration_source[
        (calibration_source["metric"].astype(str) == "gsnr_db")
        & (calibration_source["strategy"].astype(str) == "flat")
        & (calibration_source["spans"].astype(int).isin([1, 4, 8]))
    ].copy()

    heldout_source = pd.read_csv(heldout_path)

    cfg = load_config(ROOT / "config_q2_final.yaml")
    grid = build_grid(cfg["grid"])
    link = LinkModel(grid, cfg)
    launch = link.flat_launch_w(float(cfg["launch"]["flat_power_dbm_per_channel"]))

    calibration = evaluate_rows(calibration_source, link, launch, "reference_value")
    heldout = evaluate_rows(heldout_source, link, launch, "gnpy_gsnr_db")

    models = [
        "none",
        "constant",
        "wavelength_linear",
        "span_log_linear",
        "wavelength_span_linear",
    ]

    summaries: dict[str, Any] = {}
    corrected_frames: list[pd.DataFrame] = []

    for model in models:
        pred_cal, coef = fit_predict(
            calibration["wavelength_nm"].to_numpy(float),
            calibration["spans"].to_numpy(float),
            calibration["recursive_raw_residual_db"].to_numpy(float),
            calibration["wavelength_nm"].to_numpy(float),
            calibration["spans"].to_numpy(float),
            model,
        )

        pred_holdout, _ = fit_predict(
            calibration["wavelength_nm"].to_numpy(float),
            calibration["spans"].to_numpy(float),
            calibration["recursive_raw_residual_db"].to_numpy(float),
            heldout["wavelength_nm"].to_numpy(float),
            heldout["spans"].to_numpy(float),
            model,
        )

        cal_corrected = calibration["recursive_raw_residual_db"].to_numpy(float) - pred_cal
        heldout_corrected = heldout["recursive_raw_residual_db"].to_numpy(float) - pred_holdout

        summaries[model] = {
            "coefficients": coef,
            "calibration_raw": metric_dict(calibration["recursive_raw_residual_db"].to_numpy(float)),
            "calibration_corrected_in_sample": metric_dict(cal_corrected),
            "calibration_corrected_leave_one_out": leave_one_out(calibration, model),
            "heldout_raw": metric_dict(heldout["recursive_raw_residual_db"].to_numpy(float)),
            "heldout_corrected": metric_dict(heldout_corrected),
        }

        frame = heldout.copy()
        frame.insert(0, "correction_model", model)
        frame["predicted_residual_correction_db"] = pred_holdout
        frame["recursive_corrected_model_gsnr_db"] = frame["recursive_raw_model_gsnr_db"] - pred_holdout
        frame["recursive_corrected_residual_db"] = heldout_corrected
        corrected_frames.append(frame)

    best_by_loo = min(
        models,
        key=lambda name: summaries[name]["calibration_corrected_leave_one_out"]["rmse_db"],
    )

    summary = {
        "note": "Diagnostic only. Correction is trained on calibration rows and evaluated on held-out rows.",
        "config": "config_q2_final.yaml",
        "grid_mode": cfg["grid"]["mode"],
        "n_channels": int(grid.n_channels),
        "calibration_file": str(calibration_path.relative_to(ROOT)),
        "heldout_file": str(heldout_path.relative_to(ROOT)),
        "calibration_rows": int(len(calibration)),
        "heldout_rows": int(len(heldout)),
        "candidate_models": models,
        "best_model_by_calibration_leave_one_out_rmse": best_by_loo,
        "model_summaries": summaries,
        "safe_current_claim": (
            "Use recursive raw held-out RMSE unless a correction model has acceptable "
            "calibration leave-one-out behavior and improves held-out performance without leakage."
        ),
    }

    calibration.to_csv(output_dir / "recursive_cband_calibration_rows.csv", index=False)
    heldout.to_csv(output_dir / "recursive_cband_heldout_raw_rows.csv", index=False)
    pd.concat(corrected_frames, ignore_index=True).to_csv(
        output_dir / "recursive_cband_heldout_corrected_candidates.csv",
        index=False,
    )
    (output_dir / "recursive_cband_correction_summary.json").write_text(
        json.dumps(summary, indent=2),
        encoding="utf-8",
    )

    print(json.dumps(summary, indent=2))
    print()
    print("Wrote:")
    print(output_dir / "recursive_cband_calibration_rows.csv")
    print(output_dir / "recursive_cband_heldout_raw_rows.csv")
    print(output_dir / "recursive_cband_heldout_corrected_candidates.csv")
    print(output_dir / "recursive_cband_correction_summary.json")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
