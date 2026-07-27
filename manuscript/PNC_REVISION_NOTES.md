# PNC manuscript revision notes

Recommended safe title:
A Reproducible ISRS-Aware GSNR Estimator for S+C+L Optical Links with Held-Out C-Band GNPy Cross-Tool Verification

Safe claim:
The framework targets ISRS-aware S+C+L optical-link GSNR modelling.
The currently frozen external held-out GNPy verification is local C-band only.

Do not claim:
Full S+C+L external validation.
Experimental validation.
Final journal-ready evidence before clean-clone regeneration from simulator/GNPy workflow.

Current reproducible evidence:
releases/pnc-v1.0/reproduce_paper.py reproduces the manuscript-reported held-out validation metrics.

Required paper edits:
1. Revise title and abstract.
2. Rewrite contribution list.
3. Expand Methods with real model details.
4. Move row-level Table 4 to supplementary material later.
5. Remove any sentence saying the paper supports submission.
6. Add exact GitHub release, commit SHA, and later Zenodo DOI in Data availability.
