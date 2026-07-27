# JOC v1.3 release evidence

This folder contains the release manifest and clean-clone reproduction record for:

**A reproducible recursive GSNR estimator for wideband optical links with power-aligned C-band GNPy verification**

Authoritative tag: `joc-submission-v1.3`  
Commit: `95aba239d71f60c587ab42cd2709462d87764d2f`

Main command:

```powershell
python releases\pnc-v1.0\reproduce_joc_revision.py
```

Expected headline values are stored in `evidence_manifest_sha256.json` and match the manuscript: 567 rows, 9 conditions, RMSE 1.0892013090670676 dB, MAE 1.0691060534454953 dB, bias +1.0691060534454953 dB and maximum absolute error 1.5497907952563423 dB.
