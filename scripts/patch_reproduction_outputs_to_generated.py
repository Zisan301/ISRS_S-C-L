from pathlib import Path

ROOT = Path.cwd()

def patch_file(path: str, replacements: list[tuple[str, str]]) -> None:
    p = ROOT / path
    text = p.read_text(encoding="utf-8-sig")
    original = text

    for old, new in replacements:
        if old not in text:
            raise SystemExit(f"Pattern not found in {path}:\n{old}")
        text = text.replace(old, new)

    if text != original:
        p.write_text(text, encoding="utf-8")

# 1) Make diagnostic scripts respect PNC_RESULTS_DIR

patch_file(
    "scripts/compare_recursive_heldout_cband.py",
    [
        ("import json\nimport re\nimport sys\n", "import json\nimport os\nimport re\nimport sys\n"),
        (
            '    output_dir = ROOT / "releases" / "pnc-v1.0" / "results"\n',
            '    output_dir = Path(os.environ.get("PNC_RESULTS_DIR", ROOT / "releases" / "pnc-v1.0" / "results"))\n',
        ),
    ],
)

patch_file(
    "scripts/train_recursive_cband_correction.py",
    [
        ("import json\nimport sys\n", "import json\nimport os\nimport sys\n"),
        (
            '    output_dir = ROOT / "releases" / "pnc-v1.0" / "results"\n',
            '    output_dir = Path(os.environ.get("PNC_RESULTS_DIR", ROOT / "releases" / "pnc-v1.0" / "results"))\n',
        ),
        (
            '        "calibration_file": str(calibration_path),\n        "heldout_file": str(heldout_path),\n',
            '        "calibration_file": str(calibration_path.relative_to(ROOT)),\n        "heldout_file": str(heldout_path.relative_to(ROOT)),\n',
        ),
    ],
)

patch_file(
    "scripts/evaluate_recursive_cband_grouped_cv.py",
    [
        ("import json\nfrom pathlib import Path\n", "import json\nimport os\nfrom pathlib import Path\n"),
        (
            '    output_dir = ROOT / "releases" / "pnc-v1.0" / "results"\n',
            '    output_dir = Path(os.environ.get("PNC_RESULTS_DIR", ROOT / "releases" / "pnc-v1.0" / "results"))\n',
        ),
        (
            '        "input_file": str(input_path),\n',
            '        "input_file": str(input_path.relative_to(ROOT)),\n',
        ),
    ],
)

# 2) Make release runner use ignored generated output folder

patch_file(
    "releases/pnc-v1.0/reproduce_recursive_diagnostics.py",
    [
        ("import json\nimport subprocess\n", "import json\nimport os\nimport subprocess\n"),
        (
            'RESULTS = ROOT / "releases" / "pnc-v1.0" / "results"\n',
            'RESULTS = ROOT / "releases" / "pnc-v1.0" / "generated"\n',
        ),
        (
            '            "releases/pnc-v1.0/results/recursive_heldout_cband_row_comparison.csv",\n            "releases/pnc-v1.0/results/recursive_heldout_cband_metrics.json",\n',
            '            "releases/pnc-v1.0/generated/recursive_heldout_cband_row_comparison.csv",\n            "releases/pnc-v1.0/generated/recursive_heldout_cband_metrics.json",\n',
        ),
        (
            '            "releases/pnc-v1.0/results/recursive_cband_calibration_rows.csv",\n            "releases/pnc-v1.0/results/recursive_cband_heldout_raw_rows.csv",\n            "releases/pnc-v1.0/results/recursive_cband_heldout_corrected_candidates.csv",\n            "releases/pnc-v1.0/results/recursive_cband_correction_summary.json",\n',
            '            "releases/pnc-v1.0/generated/recursive_cband_calibration_rows.csv",\n            "releases/pnc-v1.0/generated/recursive_cband_heldout_raw_rows.csv",\n            "releases/pnc-v1.0/generated/recursive_cband_heldout_corrected_candidates.csv",\n            "releases/pnc-v1.0/generated/recursive_cband_correction_summary.json",\n',
        ),
        (
            '            "releases/pnc-v1.0/results/recursive_cband_grouped_cv_summary.json",\n',
            '            "releases/pnc-v1.0/generated/recursive_cband_grouped_cv_summary.json",\n',
        ),
        (
            '    completed = subprocess.run(\n        item["command"],\n        cwd=ROOT,\n        text=True,\n        stdout=subprocess.PIPE,\n        stderr=subprocess.STDOUT,\n        check=False,\n    )\n',
            '    env = os.environ.copy()\n    env["PNC_RESULTS_DIR"] = str(RESULTS)\n\n    completed = subprocess.run(\n        item["command"],\n        cwd=ROOT,\n        text=True,\n        stdout=subprocess.PIPE,\n        stderr=subprocess.STDOUT,\n        check=False,\n        env=env,\n    )\n',
        ),
        (
            '            "recursive_raw_heldout_rmse_db": correction["model_summaries"]["none"]["heldout_raw"]["rmse_db"],\n',
            '            "generated_output_dir": str(RESULTS.relative_to(ROOT)),\n            "recursive_raw_heldout_rmse_db": correction["model_summaries"]["none"]["heldout_raw"]["rmse_db"],\n',
        ),
        (
            '        correction = load_json("releases/pnc-v1.0/results/recursive_cband_correction_summary.json")\n        grouped = load_json("releases/pnc-v1.0/results/recursive_cband_grouped_cv_summary.json")\n',
            '        correction = load_json("releases/pnc-v1.0/generated/recursive_cband_correction_summary.json")\n        grouped = load_json("releases/pnc-v1.0/generated/recursive_cband_grouped_cv_summary.json")\n',
        ),
    ],
)

# 3) Ignore generated folder and packaging metadata

gitignore = ROOT / ".gitignore"
text = gitignore.read_text(encoding="utf-8") if gitignore.exists() else ""

entries = [
    "",
    "# Python packaging metadata",
    "*.egg-info/",
    "",
    "# Generated release reproduction outputs",
    "releases/pnc-v1.0/generated/",
]

for entry in entries:
    if entry and entry not in text:
        text += "\n" + entry

gitignore.write_text(text.strip() + "\n", encoding="utf-8")

print("Patched reproduction outputs to ignored generated folder.")
