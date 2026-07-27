\# JOC code-side readiness note



Date: 2026-07-27



Target journal:

Journal of Optical Communications



Current code-side status:

\- Recursive multi-span evaluation is implemented.

\- Held-out C-band GNPy validation is reproducible.

\- Post-model residual calibration is evaluated separately from the raw recursive model.

\- Grouped leave-one-wavelength-out and leave-one-span-out validation are included.

\- Compact C-band launch-power robustness sweep is included.

\- JOC figure and table evidence generation is included.

\- S/C/L validation claim guard is included and blocks unsupported full S+C+L claims.

\- Clean-clone reproduction was tested before tagging.



Safe manuscript claim:

The framework supports wideband S+C+L modelling, but the present external GNPy cross-tool validation is restricted to C-band cases.



Forbidden manuscript claim:

Do not claim full S+C+L external validation, SSFM validation, experimental validation, or network-level validation in this JOC version.



Code-side conclusion:

The code is ready to support manual manuscript writing after the clean-clone reproduction passes.

