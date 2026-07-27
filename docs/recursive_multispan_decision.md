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

## Recursive C-band correction and grouped-CV update

A recursive C-band residual-correction diagnostic was trained only on the calibration rows:

- Calibration wavelengths: 1535, 1550, 1560 nm
- Calibration spans: 1, 4, 8
- Calibration rows: 9
- Held-out rows: 9

Candidate correction models were compared using calibration leave-one-out, leave-one-wavelength-out, and leave-one-span-out tests.

Best diagnostic model:

- Model: wavelength_span_linear
- Form: residual = a + b*(wavelength_nm - 1550) + c*log10(spans)

Grouped-CV results on calibration rows only:

- Leave-one-wavelength-out RMSE: 0.172 dB
- Leave-one-span-out RMSE: 0.130 dB

Held-out C-band diagnostic result:

- Recursive raw held-out RMSE: 0.527 dB
- Recursive corrected held-out RMSE: 0.219 dB
- Recursive corrected held-out max absolute error: 0.279 dB

Decision:

The old 0.389 dB corrected claim is retired. The new diagnostic C-band claim is that recursive span-by-span propagation gives 0.527 dB raw held-out RMSE, and a calibration-only wavelength/span residual correction reduces the held-out RMSE to 0.219 dB on the 9-row C-band held-out set.

Limitation:

This remains C-band diagnostic evidence only. It is not full S+C+L external validation and not final journal evidence until regenerated in a clean clone and expanded to wider validation cases.
