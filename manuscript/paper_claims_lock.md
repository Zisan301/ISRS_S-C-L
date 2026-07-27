# Journal of Optical Communications Claims Lock

Target journal:
Journal of Optical Communications

Safe title:
A Reproducible Recursive GSNR Estimation Framework for Wideband Optical Links with Held-Out C-Band GNPy Cross-Tool Validation

Core safe claim:
The framework supports wideband S+C+L wavelength-grid modelling, but the present external cross-tool validation is restricted to held-out C-band GNPy cases.

Current reproducible evidence:
- Recursive raw held-out C-band RMSE: 0.5266 dB.
- Recursive corrected held-out C-band RMSE: 0.2190 dB.
- Leave-one-wavelength-out grouped CV RMSE: 0.1717 dB.
- Leave-one-span-out grouped CV RMSE: 0.1304 dB.
- S/C/L claim guard result: not ready for full S+C+L external validation.
- Bands currently present in external validation matrix: C only.
- Missing external validation bands: S and L.

Allowed claims:
- The software framework implements a wideband S+C+L optical-link GSNR estimation workflow.
- Recursive multi-span propagation replaces the earlier analytical span-scaling approximation.
- C-band GNPy cross-tool validation is reproducible using the release workflow.
- Post-model residual calibration improves the selected held-out C-band cases, but it is not proof of full physical-model accuracy across S+C+L.

Forbidden claims:
- Do not claim full S+C+L external validation.
- Do not claim experimental validation.
- Do not claim SSFM validation.
- Do not claim network-planning validation.
- Do not claim the model is universally accurate across arbitrary S+C+L deployments.
- Do not reuse the old corrected RMSE of 0.389 dB as the main current recursive result.

Limitations to state clearly:
- S-band and L-band external reference rows are missing.
- The default GNPy EDFA example produced C-band-compatible validation rows only.
- SSFM validation is not included in the present version.
- Network-level routing/modulation experiments are not included in the present version.
