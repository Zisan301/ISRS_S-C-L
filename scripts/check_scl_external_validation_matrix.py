from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
VALIDATION_DIR = ROOT / "releases" / "pnc-v1.0" / "validation_data"
RESULTS_DIR = ROOT / "releases" / "pnc-v1.0" / "generated"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

MATRIX_PATH = VALIDATION_DIR / "scl_external_validation_matrix.csv"
TEMPLATE_PATH = VALIDATION_DIR / "scl_external_validation_matrix_template.csv"
OUTPUT_PATH = RESULTS_DIR / "scl_external_validation_readiness.json"

REQUIRED_COLUMNS = [
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

REQUIRED_BANDS = {"S", "C", "L"}
REQUIRED_SPANS = {1, 4, 8}


def write_summary(summary: dict) -> int:
    OUTPUT_PATH.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    print()
    print(f"Wrote: {OUTPUT_PATH}")
    return 0 if summary.get("ready_for_scl_claim") else 1


def main() -> int:
    if not MATRIX_PATH.exists():
        return write_summary(
            {
                "ready_for_scl_claim": False,
                "reason": "scl_external_validation_matrix.csv is missing.",
                "template_available": str(TEMPLATE_PATH.relative_to(ROOT)),
                "required_next_action": (
                    "Copy the template to scl_external_validation_matrix.csv and replace template rows "
                    "with real S, C, and L external reference rows from GNPy, SSFM, or another traceable source."
                ),
            }
        )

    frame = pd.read_csv(MATRIX_PATH)

    missing_columns = [column for column in REQUIRED_COLUMNS if column not in frame.columns]
    if missing_columns:
        return write_summary(
            {
                "ready_for_scl_claim": False,
                "reason": "Required columns are missing.",
                "missing_columns": missing_columns,
            }
        )

    clean = frame.copy()
    for column in clean.columns:
        clean[column] = clean[column].astype(str).str.strip()

    template_like = clean.apply(
        lambda row: row.astype(str).str.contains("TO_FILL|template row", case=False, regex=True).any(),
        axis=1,
    )
    real = clean[~template_like].copy()

    if real.empty:
        return write_summary(
            {
                "ready_for_scl_claim": False,
                "reason": "Matrix contains no real validation rows.",
                "rows_total": int(len(frame)),
                "template_like_rows": int(template_like.sum()),
            }
        )

    real["band"] = real["band"].str.upper()
    real["spans_int"] = pd.to_numeric(real["spans"], errors="coerce").astype("Int64")
    real["residual_float"] = pd.to_numeric(real["residual"], errors="coerce")
    real["matched_bool"] = real["matched"].str.lower().isin(["true", "1", "yes"])
    real["independent_bool"] = real["independent"].str.lower().isin(["true", "1", "yes"])

    bands_present = set(real["band"].dropna())
    spans_present = set(int(x) for x in real["spans_int"].dropna().unique())

    gsnr_rows = real[real["metric"].str.lower() == "gsnr_db"]
    matched_rows = real[real["matched_bool"]]
    independent_rows = real[real["independent_bool"]]

    rows_by_band = {
        band: int((real["band"] == band).sum())
        for band in sorted(REQUIRED_BANDS)
    }

    issues: list[str] = []

    missing_bands = sorted(REQUIRED_BANDS - bands_present)
    if missing_bands:
        issues.append(f"Missing validation bands: {missing_bands}")

    missing_spans = sorted(REQUIRED_SPANS - spans_present)
    if missing_spans:
        issues.append(f"Missing required spans: {missing_spans}")

    if len(gsnr_rows) != len(real):
        issues.append("All real rows must use metric=gsnr_db for this validation gate.")

    if len(matched_rows) != len(real):
        issues.append("All real rows must be matched=true.")

    if len(independent_rows) != len(real):
        issues.append("All real rows must be independent=true.")

    for band in REQUIRED_BANDS:
        if rows_by_band[band] < 3:
            issues.append(f"Band {band} has fewer than 3 real validation rows.")

    residuals = real["residual_float"].dropna()
    if len(residuals) != len(real):
        issues.append("Some residual values are missing or non-numeric.")

    rmse = None
    max_abs_error = None
    if len(residuals) == len(real) and len(residuals) > 0:
        rmse = float((residuals.pow(2).mean()) ** 0.5)
        max_abs_error = float(residuals.abs().max())

    summary = {
        "ready_for_scl_claim": len(issues) == 0,
        "matrix_file": str(MATRIX_PATH.relative_to(ROOT)),
        "rows_total": int(len(frame)),
        "real_rows": int(len(real)),
        "template_like_rows": int(template_like.sum()),
        "bands_present": sorted(bands_present),
        "spans_present": sorted(spans_present),
        "rows_by_band": rows_by_band,
        "rmse_db": rmse,
        "max_abs_error_db": max_abs_error,
        "issues": issues,
        "claim_policy": (
            "Only claim full S+C+L external validation when ready_for_scl_claim is true. "
            "Until then, claim only C-band diagnostic validation."
        ),
    }

    return write_summary(summary)


if __name__ == "__main__":
    raise SystemExit(main())