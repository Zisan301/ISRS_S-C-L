"""Reproduce the JOC v1.3 evidence package.

This runner regenerates the principal scenario-matched C-band matrix, the
legacy recursive diagnostic, local calibration checks, all manuscript figures,
figure provenance, the focused bias audit, and the release SHA-256 manifest.
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
        "name": "scenario_matched_cband_gnpy_robustness",
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
        "name": "bias_audit",
        "command": [sys.executable, "scripts/generate_joc_bias_audit.py"],
        "outputs": [
            "releases/pnc-v1.0/generated/joc_bias_audit_rows.csv",
            "releases/pnc-v1.0/generated/joc_bias_audit_summary.json",
            "releases/pnc-v1.0/generated/joc_revision_assets/generated/table_bias_audit_summary.tex",
            "releases/pnc-v1.0/generated/joc_revision_assets/generated/table_bias_audit_center_channels.tex",
        ],
    },
    {
        "name": "all_joc_manuscript_assets_and_provenance",
        "command": [sys.executable, "scripts/generate_joc_revision_assets.py"],
        "outputs": [
            "releases/pnc-v1.0/generated/joc_revision_assets/joc_revision_asset_summary.json",
            "releases/pnc-v1.0/generated/joc_revision_assets/figures/figure-1-spectral-scope.pdf",
            "releases/pnc-v1.0/generated/joc_revision_assets/figures/figure-2-framework-architecture.pdf",
            "releases/pnc-v1.0/generated/joc_revision_assets/figures/figure-3-power-aligned-parity.pdf",
            "releases/pnc-v1.0/generated/joc_revision_assets/figures/figure-4-condition-level-robustness.pdf",
            "releases/pnc-v1.0/generated/joc_revision_assets/figures/figure-5-legacy-heldout-rmse.pdf",
            "releases/pnc-v1.0/generated/joc_revision_assets/generated/joc_revision_numbers.tex",
            "releases/pnc-v1.0/generated/joc_revision_assets/generated/release_metadata.tex",
            "releases/pnc-v1.0/generated/joc_revision_assets/generated/table_condition_rmse.tex",
            "releases/pnc-v1.0/generated/joc_revision_assets/generated/table_figure_provenance.tex",
            "releases/pnc-v1.0/generated/joc_revision_assets/generated/figure_provenance.csv",
            "releases/pnc-v1.0/generated/joc_revision_assets/generated/figure_provenance.json",
        ],
    },
    {
        "name": "release_manifest_and_clean_clone_record",
        "command": [sys.executable, "scripts/build_joc_v13_release_artifacts.py"],
        "outputs": [
            "releases/pnc-v1.0/joc-v1.3-release/README.md",
            "releases/pnc-v1.0/joc-v1.3-release/evidence_manifest_sha256.json",
            "releases/pnc-v1.0/joc-v1.3-release/evidence_manifest_sha256.txt",
            "releases/pnc-v1.0/joc-v1.3-release/clean_clone_reproduction_log.md",
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
        "stdout_tail": completed.stdout[-4000:],
    }


def main() -> int:
    RESULTS.mkdir(parents=True, exist_ok=True)
    runs = [run(item) for item in COMMANDS]
    passed = all(item["passed"] for item in runs)

    summary = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "suite": "joc_v13_reproduction",
        "passed": passed,
        "runs": runs,
        "note": (
            "The scenario-matched sweep is the principal C-band evidence. "
            "The bias audit is generated from GNPy-reported ASE/NLI terms and the recursive model noise budget. "
            "Every manuscript figure is regenerated by the project workflow. Figures 1 and 2 are explanatory; "
            "all other figures read numerical values directly from reproduced CSV/JSON files."
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
