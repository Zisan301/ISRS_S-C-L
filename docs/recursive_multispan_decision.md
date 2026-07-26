# Recursive multi-span decision note

The original analytical multi-span accumulation mode used:

ASE_N = N * ASE_1
NLI_N = N^(1+epsilon) * NLI_1

A diagnostic benchmark compared this approximation against explicit recursive span-by-span propagation over the tested paper_240_subset matrix.

Result:

- Maximum absolute GSNR delta: 0.7920031143698871 dB
- Diagnostic tolerance: 0.25 dB
- Within tolerance: false

Decision:

The analytical multi-span scaling mode is not defensible as the publication-grade evidence path for the tested matrix. Recursive span-by-span propagation is now implemented and used in the study pipeline for optimizer evaluation, nominal sweeps, and waveform operating-point selection.

Important limitation:

The successful smoke run proves pipeline plumbing only. It is not journal evidence. Full recursive-mode validation must now regenerate the held-out C-band comparison and later the wider S/C/L validation matrix.

## Recursive held-out C-band diagnostic update

A follow-up diagnostic compared the frozen C-band held-out evidence with current analytical and recursive evaluations.

Key result:

- Frozen corrected RMSE: 0.389 dB
- Current recursive raw RMSE: 0.527 dB
- Current recursive raw bias: -0.457 dB
- Current recursive raw max absolute error: 0.925 dB
- Current recursive corrected RMSE using the old correction: 3.038 dB

Interpretation:

The old wavelength-linear residual correction must not be reused after switching to recursive propagation. It was fitted for the older model path and now overcorrects the recursive model. The safer current claim is the raw recursive held-out C-band diagnostic result: 0.527 dB RMSE over 9 held-out rows.

Decision:

Retire the old 0.389 dB corrected held-out claim unless a new correction is trained only on calibration rows and then evaluated on held-out rows. For now, report recursive raw performance as diagnostic evidence and clearly state that full journal evidence still requires clean regeneration and wider S/C/L validation.
