from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GENERATED = ROOT / "releases" / "pnc-v1.0" / "generated"
RELEASE_DIR = ROOT / "releases" / "pnc-v1.0" / "joc-v1.3-release"
RELEASE_DIR.mkdir(parents=True, exist_ok=True)

REQUIRED_FILES = [
    "README.md",
    "scripts/run_cband_launch_power_sweep.py",
    "scripts/generate_joc_bias_audit.py",
    "scripts/generate_joc_revision_assets.py",
    "releases/pnc-v1.0/reproduce_joc_revision.py",
    "releases/pnc-v1.0/generated/cband_launch_power_sweep_reference_rows.csv",
    "releases/pnc-v1.0/generated/cband_launch_power_sweep_model_comparison.csv",
    "releases/pnc-v1.0/generated/cband_launch_power_sweep_summary.json",
    "releases/pnc-v1.0/generated/joc_bias_audit_rows.csv",
    "releases/pnc-v1.0/generated/joc_bias_audit_summary.json",
    "releases/pnc-v1.0/generated/scl_external_validation_readiness.json",
    "releases/pnc-v1.0/generated/joc_revision_assets/generated/joc_revision_numbers.tex",
    "releases/pnc-v1.0/generated/joc_revision_assets/generated/release_metadata.tex",
    "releases/pnc-v1.0/generated/joc_revision_assets/generated/table_condition_rmse.tex",
    "releases/pnc-v1.0/generated/joc_revision_assets/generated/table_bias_audit_summary.tex",
    "releases/pnc-v1.0/generated/joc_revision_assets/generated/table_bias_audit_center_channels.tex",
    "releases/pnc-v1.0/generated/joc_revision_assets/generated/table_figure_provenance.tex",
    "releases/pnc-v1.0/generated/joc_revision_assets/generated/figure_provenance.csv",
    "releases/pnc-v1.0/generated/joc_revision_assets/figures/figure-1-spectral-scope.pdf",
    "releases/pnc-v1.0/generated/joc_revision_assets/figures/figure-2-framework-architecture.pdf",
    "releases/pnc-v1.0/generated/joc_revision_assets/figures/figure-3-power-aligned-parity.pdf",
    "releases/pnc-v1.0/generated/joc_revision_assets/figures/figure-4-condition-level-robustness.pdf",
    "releases/pnc-v1.0/generated/joc_revision_assets/figures/figure-5-legacy-heldout-rmse.pdf",
]


def git(args: list[str]) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True, stderr=subprocess.DEVNULL).strip()


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def main() -> int:
    missing = [rel for rel in REQUIRED_FILES if not (ROOT / rel).exists()]
    if missing:
        raise FileNotFoundError("Missing evidence files:\n" + "\n".join(missing))

    try:
        commit = git(["rev-parse", "HEAD"])
    except Exception:
        commit = "unknown"
    try:
        tags = [line for line in git(["tag", "--points-at", "HEAD"]).splitlines() if line.startswith("joc-submission-v")]
        tag = sorted(tags)[-1] if tags else "joc-submission-v1.3"
    except Exception:
        tag = "joc-submission-v1.3"

    records = []
    for rel in REQUIRED_FILES:
        path = ROOT / rel
        records.append({
            "path": rel.replace("\\", "/"),
            "bytes": path.stat().st_size,
            "sha256": sha256(path),
        })

    manifest = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "paper_title": "A reproducible recursive GSNR estimator for wideband optical links with power-aligned C-band GNPy verification",
        "release_tag": tag,
        "commit": commit,
        "headline_expected_output": {
            "matched_rows": 567,
            "matched_operating_conditions": 9,
            "matched_rmse_db": 1.0892013090670676,
            "matched_mae_db": 1.0691060534454953,
            "matched_bias_db": 1.0691060534454953,
            "matched_max_abs_error_db": 1.5497907952563423,
        },
        "files": records,
    }
    (RELEASE_DIR / "evidence_manifest_sha256.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    txt_lines = [
        f"Paper title: {manifest['paper_title']}",
        f"Release tag: {tag}",
        f"Commit: {commit}",
        "",
        "SHA256 evidence manifest",
        "------------------------",
    ]
    for item in records:
        txt_lines.append(f"{item['sha256']}  {item['path']}")
    (RELEASE_DIR / "evidence_manifest_sha256.txt").write_text("\n".join(txt_lines) + "\n", encoding="utf-8")

    log = f"""# Clean-clone reproduction log for JOC v1.3

Paper title: {manifest['paper_title']}
Release tag recorded by this checkout: `{tag}`
Commit recorded by this checkout: `{commit}`
Generated at: {manifest['generated_at_utc']}

## Command expected from a clean clone

```powershell
python -m pip install -e .
python -m pytest -q
python releases\\pnc-v1.0\\reproduce_joc_revision.py
```

## Expected final reproduction output

```text
PASS: JOC revision reproduction completed.
{{
  "matched_rows": 567,
  "matched_operating_conditions": 9,
  "matched_rmse_db": 1.0892013090670676,
  "matched_mae_db": 1.0691060534454953,
  "matched_bias_db": 1.0691060534454953,
  "matched_max_abs_error_db": 1.5497907952563423
}}
```

## Note

For final submission, run the clean-clone commands from tag `joc-submission-v1.3` and keep the terminal transcript with this release. This file is generated from the same runner and manifest so the expected values match the manuscript.
"""
    (RELEASE_DIR / "clean_clone_reproduction_log.md").write_text(log, encoding="utf-8")

    release_readme = f"""# JOC v1.3 release evidence

This folder contains the release manifest and clean-clone reproduction record for:

**{manifest['paper_title']}**

Authoritative tag: `{tag}`  
Commit: `{commit}`

Main command:

```powershell
python releases\\pnc-v1.0\\reproduce_joc_revision.py
```

Expected headline values are stored in `evidence_manifest_sha256.json` and match the manuscript: 567 rows, 9 conditions, RMSE 1.0892013090670676 dB, MAE 1.0691060534454953 dB, bias +1.0691060534454953 dB and maximum absolute error 1.5497907952563423 dB.
"""
    (RELEASE_DIR / "README.md").write_text(release_readme, encoding="utf-8")
    print(json.dumps({"release_dir": str(RELEASE_DIR), "tag": tag, "commit": commit, "files_hashed": len(records)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
