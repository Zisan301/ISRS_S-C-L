# PNC v1.0 frozen validation evidence

This folder contains the frozen evidence package for the manuscript version targeting Springer Photonic Network Communications.

## Supported claim

This release supports a reproducible held-out C-band GNPy cross-tool verification package for the current manuscript evidence.

The framework scope is S+C+L optical-link modelling, but the currently frozen held-out external verification is local C-band only.

## Reproduce paper validation numbers

From the repository root, run:

python releases/pnc-v1.0/reproduce_paper.py

Expected key output:

PASS: held-out validation rows reproduce the paper-reported metrics.
Raw held-out RMSE: 2.804 dB
Corrected held-out RMSE: 0.389 dB
Corrected held-out bias: 0.211 dB

## Important limitation

The files in validation_data/ freeze the manuscript-reported validation rows and metrics. Before final journal submission, the same values should be regenerated from the original simulator/GNPy workflow in a clean clone.

Do not claim full S+C+L external validation until S-band, C-band and L-band held-out references are committed and reproduced.

## Key files

- reproduce_paper.py: regenerates validation tables and metric checks.
- validation_data/heldout_row_level_comparison.csv: held-out row-level comparison.
- validation_data/validation_metrics.json: manuscript-reported metrics.
- validation_data/validation_gate.json: validation gate thresholds and pass/fail status.
- MANIFEST.json: file hashes and environment metadata.
