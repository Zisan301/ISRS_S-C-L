from pathlib import Path

path = Path("releases/pnc-v1.0/reproduce_recursive_diagnostics.py")
text = path.read_text(encoding="utf-8-sig")
original = text

old = '''    {
        "name": "recursive_cband_grouped_cv",
        "command": [sys.executable, "scripts/evaluate_recursive_cband_grouped_cv.py"],
        "expected_outputs": [
            "releases/pnc-v1.0/generated/recursive_cband_grouped_cv_summary.json",
        ],
    },
    {
        "name": "scl_external_validation_claim_guard",
        "command": [sys.executable, "scripts/check_scl_external_validation_matrix.py"],
        "expected_outputs": [
            "releases/pnc-v1.0/generated/scl_external_validation_readiness.json",
        ],
        "non_blocking": True,
    },'''

new = '''    {
        "name": "recursive_cband_grouped_cv",
        "command": [sys.executable, "scripts/evaluate_recursive_cband_grouped_cv.py"],
        "expected_outputs": [
            "releases/pnc-v1.0/generated/recursive_cband_grouped_cv_summary.json",
        ],
    },
    {
        "name": "cband_launch_power_sweep",
        "command": [sys.executable, "scripts/run_cband_launch_power_sweep.py"],
        "expected_outputs": [
            "releases/pnc-v1.0/generated/cband_launch_power_sweep_reference_rows.csv",
            "releases/pnc-v1.0/generated/cband_launch_power_sweep_model_comparison.csv",
            "releases/pnc-v1.0/generated/cband_launch_power_sweep_summary.json",
        ],
    },
    {
        "name": "scl_external_validation_claim_guard",
        "command": [sys.executable, "scripts/check_scl_external_validation_matrix.py"],
        "expected_outputs": [
            "releases/pnc-v1.0/generated/scl_external_validation_readiness.json",
        ],
        "non_blocking": True,
    },'''

if old not in text:
    raise SystemExit("Could not find reproduction command block to patch.")

text = text.replace(old, new)

old_metrics = '''            "leave_one_span_out_best_model": grouped["best_model_by_leave_one_span_out_rmse"],
            "leave_one_span_out_rmse_db": grouped["models"][best]["leave_one_span_out"]["overall"]["rmse_db"],
        }'''

new_metrics = '''            "leave_one_span_out_best_model": grouped["best_model_by_leave_one_span_out_rmse"],
            "leave_one_span_out_rmse_db": grouped["models"][best]["leave_one_span_out"]["overall"]["rmse_db"],
        }

        launch_power_summary_path = ROOT / "releases/pnc-v1.0/generated/cband_launch_power_sweep_summary.json"
        if launch_power_summary_path.exists():
            launch_power = json.loads(launch_power_summary_path.read_text(encoding="utf-8"))
            summary["headline_metrics"]["cband_launch_power_sweep_rows"] = launch_power.get("rows")
            summary["headline_metrics"]["cband_launch_power_sweep_rmse_db"] = launch_power.get("overall", {}).get("rmse_db")
            summary["headline_metrics"]["cband_launch_power_sweep_max_abs_error_db"] = launch_power.get("overall", {}).get("max_abs_error_db")
        }'''

if old_metrics not in text:
    raise SystemExit("Could not find headline metrics block to patch.")

text = text.replace(old_metrics, new_metrics)

if text == original:
    raise SystemExit("No changes made.")

path.write_text(text, encoding="utf-8")
print("Patched reproduction suite with C-band launch-power sweep.")