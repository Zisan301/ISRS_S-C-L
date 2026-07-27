# Journal of Optical Communications Manuscript Outline

Working title:
A Reproducible Recursive GSNR Estimation Framework for Wideband Optical Links with Held-Out C-Band GNPy Cross-Tool Validation

1. Introduction
- Explain wideband optical transmission and the need for fast GSNR/QoT estimation.
- Explain why S+C+L modelling is attractive.
- State the problem: wideband validation is difficult and overclaiming must be avoided.
- State this paper's scope: framework supports S+C+L grids; external validation here is C-band GNPy.

2. Related Work
- GN/EGN models.
- ISRS-aware optical transmission modelling.
- GNPy and cross-tool validation.
- Wideband optical-system modelling.
- Reproducible simulation workflows.

3. Proposed Framework
3.1 Wavelength grid and launch-power model
3.2 Wavelength-dependent fibre attenuation
3.3 Raman/ISRS power-profile modelling
3.4 Amplifier and ASE model
3.5 ISRS-aware NLI estimation
3.6 Recursive multi-span GSNR evaluation
3.7 Receiver/noise mapping
3.8 Residual calibration and validation protocol

4. Reproducibility Package
- Dedicated release folder.
- One-command reproduction script.
- Frozen validation data.
- Generated outputs.
- S/C/L claim guard.

5. Results
5.1 Recursive versus analytical multi-span evaluation
5.2 Held-out C-band GNPy validation
5.3 Raw versus corrected validation performance
5.4 Grouped validation: leave-one-wavelength-out and leave-one-span-out
5.5 S/C/L validation readiness and limitations

6. Discussion
- What the current evidence supports.
- Why the result is useful despite C-band-only external validation.
- Why full S+C+L validation is not claimed.
- Future work: S/L GNPy or SSFM references, sensitivity analysis, network-level application.

7. Conclusion
- Summarize recursive framework and reproducible C-band GNPy validation.
- Clearly state that broader S/L and waveform-level validation remain future work.
