# GNPy default example S/C/L limitation

Date: 2026-07-26

A band-partition S+C+L spectrum was tested with GNPy 2.14.1 using the default edfa_example_network-derived topology.

Observed result:
- GNPy propagated 63 channels.
- The channel frequency range was approximately 192.17465 THz to 195.27465 THz.
- This corresponds to approximately 1560 nm to 1535 nm, i.e. C-band only.

Interpretation:
- The default GNPy EDFA example is not sufficient for full S+C+L external validation.
- Current GNPy evidence remains C-band external validation only.
- S-band and L-band validation require custom S/L-compatible equipment configuration, SSFM reference data, or another traceable external source.

Claim policy:
- Do not claim full S+C+L external validation until S, C, and L rows all pass the SCL validation checker.
