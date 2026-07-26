"""Run PNC recursive diagnostic reproduction suite.

This is a release-level convenience runner. It regenerates the recursive
diagnostic evidence files used by the PNC upgrade branch.

It intentionally keeps the old reproduce_paper.py unchanged because that script
reproduces the frozen manuscript-row package. This runner is for the newer
recursive diagnostic package.
"""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "releases" / "pnc-v1.0" / "results"

COMMANDS = [
    {
        "name": "recursive_heldout_cband_comparison",
        "command": [sys.executable, "scripts/compare_recursive_heldout_cband.py"],
        "expected_outputs": [
            "releases/pnc-v1.0/results/recursive_heldout_cband_row_comparison.csv",
            "releases/pnc-v1.0/results/recursive_heldout_cband_metrics.json",
        ],
    },
    {
        "name": "recursive_cband_correction",
        "command": [sys.executable, "scripts/train_recursive_cband_correction.py"],
        "expected_outputs": [
            "releases/pnc-v1.0/results/recursive_cband_calibration_rows.csv",
            "releases/pnc-v1.0/results/recursive_cband_heldout_raw_rows.csv",
            "releases/pnc-v1.0/results/recursive_cband_heldout_corrected_candidates.csv",
            "releases/pnc-v1.0/results/recursive_cband_correction_summary.json",
        ],
    },
    {
        "name": "recursive_cband_grouped_cv",
        "command": [sys.executable, "scripts/evaluate_recursive_cband_grouped_cv.py"],
        "expected_outputs": [
            "releases/pnc-v1.0/results/recursive_cband_grouped_cv_summary.json",
        ],
    },
]


def run_command(item: dict) -> dict:
    print()
    print("=" * 80)
    print(f"RUN {item['name']}")
    print(" ".join(item["command"]))
    print("=" * 80)

    completed = subprocess.run(
        item["command"],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )

    print(completed.stdout)

    missing_outputs = [
        path for path in item["expected_outputs"]
        if not (ROOT / path).exists()
    ]

    return {
        "name": item["name"],
        "command": item["command"],
        "returncode": completed.returncode,
        "passed": completed.returncode == 0 and not missing_outputs,
        "missing_outputs": missing_outputs,
        "stdout_tail": completed.stdout[-4000:],
    }


def load_json(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def main() -> int:
    RESULTS.mkdir(parents=True, exist_ok=True)

    runs = [run_command(item) for item in COMMANDS]

    summary = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "python": sys.version,
        "suite": "pnc_recursive_diagnostics",
        "note": (
            "Diagnostic reproduction suite only. This is not full journal evidence "
            "and not full S+C+L external validation."
        ),
        "runs": runs,
        "passed": all(item["passed"] for item in runs),
    }

    if summary["passed"]:
        correction = load_json("releases/pnc-v1.0/results/recursive_cband_correction_summary.json")
        grouped = load_json("releases/pnc-v1.0/results/recursive_cband_grouped_cv_summary.json")

        best = correction["best_model_by_calibration_leave_one_out_rmse"]
        summary["headline_metrics"] = {
            "best_correction_model_by_calibration_loo": best,
            "recursive_raw_heldout_rmse_db": correction["model_summaries"]["none"]["heldout_raw"]["rmse_db"],
            "recursive_corrected_heldout_rmse_db": correction["model_summaries"][best]["heldout_corrected"]["rmse_db"],
            "recursive_corrected_heldout_max_abs_error_db": correction["model_summaries"][best]["heldout_corrected"]["max_abs_error_db"],
            "leave_one_wavelength_out_best_model": grouped["best_model_by_leave_one_wavelength_out_rmse"],
            "leave_one_wavelength_out_rmse_db": grouped["models"][best]["leave_one_wavelength_out"]["overall"]["rmse_db"],
            "leave_one_span_out_best_model": grouped["best_model_by_leave_one_span_out_rmse"],
            "leave_one_span_out_rmse_db": grouped["models"][best]["leave_one_span_out"]["overall"]["rmse_db"],
        }

    output_path = RESULTS / "recursive_diagnostic_reproduction_suite.json"
    output_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print()
    print("=" * 80)
    if summary["passed"]:
        print("PASS: recursive diagnostic reproduction suite completed.")
        print(json.dumps(summary.get("headline_metrics", {}), indent=2))
        print(f"Generated: {output_path}")
        return 0

    print("FAILED: recursive diagnostic reproduction suite failed.")
    print(f"Generated: {output_path}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
