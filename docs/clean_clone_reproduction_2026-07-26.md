# Clean-clone reproduction record

Date: 2026-07-26
Branch: pnc-submission-upgrade

Clean-clone command tested:
python releases\pnc-v1.0\reproduce_recursive_diagnostics.py

Result: PASS

Headline reproduced metrics:
- Recursive raw held-out C-band RMSE: 0.5266 dB
- Recursive corrected held-out C-band RMSE: 0.2190 dB
- Recursive corrected held-out max absolute error: 0.2787 dB
- Leave-one-wavelength-out calibration CV RMSE: 0.1717 dB
- Leave-one-span-out calibration CV RMSE: 0.1304 dB

Scope limitation: this remains C-band diagnostic evidence only, not full S+C+L external validation.
