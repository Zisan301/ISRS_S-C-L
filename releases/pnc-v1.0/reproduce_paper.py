from pathlib import Path
import csv
import json
import math
import hashlib
import platform
import sys
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "validation_data"
RESULTS = ROOT / "results"
RESULTS.mkdir(exist_ok=True)

heldout_file = DATA / "heldout_row_level_comparison.csv"
metrics_file = DATA / "validation_metrics.json"
gate_file = DATA / "validation_gate.json"

required_files = [heldout_file, metrics_file, gate_file]
missing = [str(p) for p in required_files if not p.exists()]
if missing:
    raise SystemExit("Missing required files:\n" + "\n".join(missing))

def metric_values(values):
    n = len(values)
    return {
        "n": n,
        "rmse_db": math.sqrt(sum(v * v for v in values) / n),
        "mae_db": sum(abs(v) for v in values) / n,
        "bias_db": sum(values) / n,
        "max_abs_error_db": max(abs(v) for v in values),
    }

with heldout_file.open("r", encoding="utf-8-sig", newline="") as f:
    rows = list(csv.DictReader(f))

raw_residuals = [float(r["raw_residual_db"]) for r in rows]
corrected_residuals = [float(r["corrected_residual_db"]) for r in rows]

computed = {
    "heldout_raw_from_rows": metric_values(raw_residuals),
    "heldout_corrected_from_rows": metric_values(corrected_residuals),
}

paper_metrics = json.loads(metrics_file.read_text(encoding="utf-8-sig"))
paper_gate = json.loads(gate_file.read_text(encoding="utf-8-sig"))

def close(a, b, tol=0.002):
    return abs(float(a) - float(b)) <= tol

checks = []
checks.append(("raw RMSE", computed["heldout_raw_from_rows"]["rmse_db"], paper_metrics["raw_heldout"]["rmse_db"]))
checks.append(("raw MAE", computed["heldout_raw_from_rows"]["mae_db"], paper_metrics["raw_heldout"]["mae_db"]))
checks.append(("raw bias", computed["heldout_raw_from_rows"]["bias_db"], paper_metrics["raw_heldout"]["bias_db"]))
checks.append(("corrected RMSE", computed["heldout_corrected_from_rows"]["rmse_db"], paper_metrics["corrected_heldout"]["rmse_db"]))
checks.append(("corrected MAE", computed["heldout_corrected_from_rows"]["mae_db"], paper_metrics["corrected_heldout"]["mae_db"]))
checks.append(("corrected bias", computed["heldout_corrected_from_rows"]["bias_db"], paper_metrics["corrected_heldout"]["bias_db"]))
checks.append(("corrected max abs error", computed["heldout_corrected_from_rows"]["max_abs_error_db"], paper_metrics["corrected_heldout"]["max_abs_error_db"]))

failed = []
for name, observed, expected in checks:
    if not close(observed, expected):
        failed.append((name, observed, expected))

output = {
    "generated_at_utc": datetime.now(timezone.utc).isoformat(),
    "python": sys.version,
    "platform": platform.platform(),
    "source_rows": str(heldout_file.relative_to(ROOT)),
    "computed": computed,
    "paper_reported": {
        "raw_heldout": paper_metrics["raw_heldout"],
        "corrected_heldout": paper_metrics["corrected_heldout"],
        "validation_gate": paper_gate,
    },
    "checks_passed": len(failed) == 0,
    "failed_checks": failed,
}

(RESULTS / "generated_validation_reproduction.json").write_text(
    json.dumps(output, indent=2),
    encoding="utf-8"
)

with (RESULTS / "generated_table4_heldout_rows.csv").open("w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=rows[0].keys())
    writer.writeheader()
    writer.writerows(rows)

with (RESULTS / "generated_table3_validation_gate.csv").open("w", encoding="utf-8", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["requirement", "observed", "threshold", "passed"])
    for key, value in paper_gate.items():
        writer.writerow([key, value["observed"], value["threshold"], value["passed"]])

if failed:
    print("FAILED: reproduced values do not match paper-reported metrics.")
    for name, observed, expected in failed:
        print(f"{name}: observed={observed:.6f}, expected={expected}")
    raise SystemExit(1)

print("PASS: held-out validation rows reproduce the paper-reported metrics.")
print(f"Raw held-out RMSE: {computed['heldout_raw_from_rows']['rmse_db']:.3f} dB")
print(f"Corrected held-out RMSE: {computed['heldout_corrected_from_rows']['rmse_db']:.3f} dB")
print(f"Corrected held-out bias: {computed['heldout_corrected_from_rows']['bias_db']:.3f} dB")
print(f"Generated: {RESULTS / 'generated_validation_reproduction.json'}")
print(f"Generated: {RESULTS / 'generated_table4_heldout_rows.csv'}")
print(f"Generated: {RESULTS / 'generated_table3_validation_gate.csv'}")
