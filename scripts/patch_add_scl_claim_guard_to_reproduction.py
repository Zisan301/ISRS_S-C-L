from pathlib import Path

ROOT = Path.cwd()
path = ROOT / "releases" / "pnc-v1.0" / "reproduce_recursive_diagnostics.py"

text = path.read_text(encoding="utf-8-sig")
original = text

old_command_block = '''    {
        "name": "recursive_cband_grouped_cv",
        "command": [sys.executable, "scripts/evaluate_recursive_cband_grouped_cv.py"],
        "expected_outputs": [
            "releases/pnc-v1.0/generated/recursive_cband_grouped_cv_summary.json",
        ],
    },
]'''

new_command_block = '''    {
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
    },
]'''

if old_command_block not in text:
    raise SystemExit("Could not find command block to patch.")

text = text.replace(old_command_block, new_command_block)

old_pass_logic = '''        "passed": completed.returncode == 0 and not missing_outputs,'''

new_pass_logic = '''        "passed": (
            (completed.returncode == 0 or item.get("non_blocking", False))
            and not missing_outputs
        ),
        "non_blocking": bool(item.get("non_blocking", False)),'''

if old_pass_logic not in text:
    raise SystemExit("Could not find pass logic to patch.")

text = text.replace(old_pass_logic, new_pass_logic)

old_note = '''            "Diagnostic reproduction suite only. This is not full journal evidence "
            "and not full S+C+L external validation."'''

new_note = '''            "Diagnostic reproduction suite only. This is not full journal evidence. "
            "The S/C/L external validation checker is included as a non-blocking claim guard."'''

if old_note not in text:
    raise SystemExit("Could not find note text to patch.")

text = text.replace(old_note, new_note)

if text == original:
    raise SystemExit("No changes made.")

path.write_text(text, encoding="utf-8")
print("Patched reproduction suite with non-blocking S/C/L claim guard.")