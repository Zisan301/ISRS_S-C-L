from pathlib import Path

path = Path("releases/pnc-v1.0/reproduce_recursive_diagnostics.py")
lines = path.read_text(encoding="utf-8-sig").splitlines()

fixed = []
removed = False

for i, line in enumerate(lines):
    # Remove the accidental extra closing brace after the launch-power headline metrics block.
    if (
        line.strip() == "}"
        and i > 0
        and "cband_launch_power_sweep_max_abs_error_db" in lines[i - 1]
    ):
        removed = True
        continue
    fixed.append(line)

if not removed:
    raise SystemExit("Did not find the accidental extra brace. Send me lines 135-160 of reproduce_recursive_diagnostics.py.")

path.write_text("\n".join(fixed) + "\n", encoding="utf-8")
print("Fixed unmatched brace in reproduction runner.")