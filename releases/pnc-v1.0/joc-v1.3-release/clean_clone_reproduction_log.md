# Clean-clone reproduction log for JOC v1.3

Paper title: A reproducible recursive GSNR estimator for wideband optical links with power-aligned C-band GNPy verification
Release tag recorded by this checkout: `joc-submission-v1.2`
Commit recorded by this checkout: `b321d334094b70257bb3c18dee1d3c09aee2c676`
Generated at: 2026-07-27T19:26:07.788210+00:00

## Command expected from a clean clone

```powershell
python -m pip install -e .
python -m pytest -q
python releases\pnc-v1.0\reproduce_joc_revision.py
```

## Expected final reproduction output

```text
PASS: JOC revision reproduction completed.
{
  "matched_rows": 567,
  "matched_operating_conditions": 9,
  "matched_rmse_db": 1.0892013090670676,
  "matched_mae_db": 1.0691060534454953,
  "matched_bias_db": 1.0691060534454953,
  "matched_max_abs_error_db": 1.5497907952563423
}
```

## Note

For final submission, run the clean-clone commands from tag `joc-submission-v1.3` and keep the terminal transcript with this release. This file is generated from the same runner and manifest so the expected values match the manuscript.
