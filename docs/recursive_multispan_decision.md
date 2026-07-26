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
