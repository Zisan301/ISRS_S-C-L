"""Reproduce the revised JOC evidence package.

This runner preserves the legacy held-out diagnostic, regenerates the local
post-model calibration and grouped checks, runs the power/loading-aligned
C-band GNPy robustness study, executes the S/C/L claim guard, and generates
replacement manuscript figures/tables.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "releases" / "pnc-v1.0" / "generated"

COMMANDS = [
    {
        "name": "legacy_recursive_heldout_diagnostic",
        "command": [sys.executable, "scripts/compare_recursive_heldout_cband.py"],
        "outputs": [
            "releases/pnc-v1.0/generated/recursive_heldout_cband_row_comparison.csv",
            "releases/pnc-v1.0/generated/recursive_heldout_cband_metrics.json",
        ],
    },
    {
        "name": "local_residual_calibration",
        "command": [sys.executable, "scripts/train_recursive_cband_correction.py"],
        "outputs": [
            "releases/pnc-v1.0/generated/recursive_cband_correction_summary.json",
            "releases/pnc-v1.0/generated/recursive_cband_heldout_corrected_candidates.csv",
        ],
    },
    {
        "name": "grouped_calibration_checks",
        "command": [sys.executable, "scripts/evaluate_recursive_cband_grouped_cv.py"],
        "outputs": [
            "releases/pnc-v1.0/generated/recursive_cband_grouped_cv_summary.json",
        ],
    },
    {
        "name": "power_loading_aligned_cband_gnpy_robustness",
        "command": [sys.executable, "scripts/run_cband_launch_power_sweep.py"],
        "outputs": [
            "releases/pnc-v1.0/generated/cband_launch_power_sweep_reference_rows.csv",
            "releases/pnc-v1.0/generated/cband_launch_power_sweep_model_comparison.csv",
            "releases/pnc-v1.0/generated/cband_launch_power_sweep_anchor_comparison.csv",
            "releases/pnc-v1.0/generated/cband_launch_power_sweep_summary.json",
        ],
    },
    {
        "name": "scl_claim_guard",
        "command": [sys.executable, "scripts/check_scl_external_validation_matrix.py"],
        "outputs": [
            "releases/pnc-v1.0/generated/scl_external_validation_readiness.json",
        ],
        "non_blocking": True,
    },
    {
        "name": "joc_revision_assets",
        "command": [sys.executable, "scripts/generate_joc_revision_assets.py"],
        "outputs": [
            "releases/pnc-v1.0/generated/joc_revision_assets/joc_revision_asset_summary.json",
            "releases/pnc-v1.0/generated/joc_revision_assets/figures/figure-3-legacy-heldout-rmse.pdf",
            "releases/pnc-v1.0/generated/joc_revision_assets/figures/figure-5-power-aligned-parity.pdf",
            "releases/pnc-v1.0/generated/joc_revision_assets/figures/figure-6-power-aligned-robustness.pdf",
            "releases/pnc-v1.0/generated/joc_revision_assets/generated/joc_revision_numbers.tex",
            "releases/pnc-v1.0/generated/joc_revision_assets/generated/table_matched_power.tex",
            "releases/pnc-v1.0/generated/joc_revision_assets/generated/table_matched_span.tex",
            "releases/pnc-v1.0/generated/joc_revision_assets/generated/table_power_reference_audit.tex",
        ],
    },
]


def run(item: dict) -> dict:
    print("\n" + "=" * 80)
    print(f"RUN {item['name']}")
    print(" ".join(item["command"]))
    print("=" * 80)
    environment = os.environ.copy()
    environment["PNC_RESULTS_DIR"] = str(RESULTS)
    completed = subprocess.run(
        item["command"],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
        env=environment,
    )
    print(completed.stdout)
    missing = [path for path in item["outputs"] if not (ROOT / path).exists()]
    passed = (completed.returncode == 0 or item.get("non_blocking", False)) and not missing
    return {
        "name": item["name"],
        "returncode": completed.returncode,
        "passed": passed,
        "non_blocking": bool(item.get("non_blocking", False)),
        "missing_outputs": missing,
        "stdout_tail": completed.stdout[-3000:],
    }


def main() -> int:
    RESULTS.mkdir(parents=True, exist_ok=True)
    runs = [run(item) for item in COMMANDS]
    passed = all(item["passed"] for item in runs)
    summary = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "suite": "joc_revision_reproduction",
        "passed": passed,
        "runs": runs,
        "note": (
            "The matched sweep is the principal C-band robustness evidence. "
            "The old nine-row held-out comparison remains a disclosed diagnostic because its legacy "
            "reference-plane assumptions are not used as the principal validation claim."
        ),
    }
    if passed:
        matched = json.loads((RESULTS / "cband_launch_power_sweep_summary.json").read_text(encoding="utf-8"))
        summary["headline_metrics"] = {
            "matched_rows": matched["rows"],
            "matched_operating_conditions": matched["operating_conditions"],
            "matched_rmse_db": matched["overall"]["rmse_db"],
            "matched_mae_db": matched["overall"]["mae_db"],
            "matched_bias_db": matched["overall"]["bias_db"],
            "matched_max_abs_error_db": matched["overall"]["max_abs_error_db"],
        }
    output = RESULTS / "joc_revision_reproduction_suite.json"
    output.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print("\n" + "=" * 80)
    print("PASS: JOC revision reproduction completed." if passed else "FAILED: JOC revision reproduction failed.")
    print(f"Generated: {output}")
    if passed:
        print(json.dumps(summary["headline_metrics"], indent=2))
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

