# Photonic Network Communications submission upgrade plan

This plan is for upgrading the ISRS S+C+L manuscript and repository into a defensible Springer Photonic Network Communications submission.

## Current blocker

The manuscript currently presents a held-out GNPy result with corrected held-out RMSE near 0.389 dB over wavelengths around 1540, 1545 and 1555 nm. The public repository history currently contains only a preliminary C-band validation package, with a warning that it does not support a full S+C+L publication claim. Therefore, the first target is reproducibility alignment: the repository must reproduce exactly the numbers reported in the manuscript before language polishing or Springer formatting.

## Submission rule

Do not submit until a clean clone can reproduce every table and figure used in the manuscript from committed code, committed configuration files and committed validation data.

## Work package 1: freeze the PNC evidence release

Create this structure:

```text
releases/pnc-v1.0/
  config_pnc_final.yaml
  gnpy/
    equipment.json
    topology_1span.json
    topology_4span.json
    topology_8span.json
    spectral_information.json
  validation_data/
    calibration_gnpy.csv
    heldout_gnpy.csv
    ssfm_reference.csv
  results/
  figures/
  MANIFEST.json
  reproduce_paper.py
```

Acceptance criteria:

- `python releases/pnc-v1.0/reproduce_paper.py` regenerates all tables, figures and validation JSON files.
- The generated RMSE, MAE, bias, maximum absolute error and coverage values match the manuscript.
- `MANIFEST.json` records file hashes, Git commit SHA, Python version, dependency versions and run date.
- The main README points to this release folder and explains the supported claim.

## Work package 2: correct the claim level

With the current evidence, use a title like:

> A Reproducible ISRS-Aware GSNR Estimator for S+C+L Optical Links with Held-Out C-Band GNPy Cross-Tool Verification

This title honestly separates model scope from validation scope.

Avoid claiming full S+C+L validation until S-band, C-band and L-band external cases are committed and reproduced.

## Work package 3: improve physical-model evidence

Add or benchmark a recursive multi-span evaluation mode against the current simplified accumulation:

```python
def evaluate_recursive(self, launch_power_w, n_spans):
    signal = launch_power_w.copy()
    accumulated_ase = np.zeros_like(signal)
    accumulated_nli = np.zeros_like(signal)
    span_records = []

    for span_index in range(n_spans):
        span = self.span_model.evaluate(signal)
        accumulated_ase += span.total_ase_psd_w_per_hz * receiver_bandwidth
        accumulated_nli += span.nli.nli_power_w_per_span
        signal = span.amplifier.output_powers_w
        span_records.append({
            "span": span_index + 1,
            "output_power_w": signal.copy(),
            "accumulated_ase_w": accumulated_ase.copy(),
            "accumulated_nli_w": accumulated_nli.copy(),
        })

    total_noise = accumulated_ase + accumulated_nli + trx_noise
    return signal / total_noise, span_records
```

Acceptance criteria:

- Report the maximum GSNR difference between analytical scaling and recursive mode over wavelength and span count.
- If the difference is small, keep analytical mode and cite the benchmark.
- If the difference is large, use recursive mode for publication results.

## Work package 4: replace residual correction as the main story

The empirical residual correction may remain as post-model calibration, but it must not be presented as proof that the raw physical model has 0.389 dB accuracy.

Preferred direction:

- Fit physically meaningful bounded parameters: attenuation slope/scale, amplifier NF offset, Raman gain scale, nonlinear coefficient scale and NLI accumulation exponent.
- Freeze fitted parameters before held-out evaluation.
- Add grouped validation: leave-one-wavelength-out, leave-one-span-out and leave-one-launch-power-out.

## Work package 5: expand validation

Minimum stronger matrix:

- 5 S-band wavelengths, 5 C-band wavelengths and 5 L-band wavelengths.
- Span counts: 1, 4, 8 and 10.
- Launch powers: -2, 0 and +2 dBm/channel.
- Flat and shaped launch profiles.
- Full and partial spectral loading.
- 9 to 15 representative SSFM cases.

Main metrics:

- GSNR, ASE power, NLI power, received power tilt and error versus launch power.
- Report results by band, span count, launch power and loading condition.

## Work package 6: add PNC network-level experiment

Add one impairment-aware routing/modulation experiment using NSFNET, COST239 or BT-UK.

Compare:

1. conventional GN without ISRS;
2. raw ISRS-aware model;
3. calibrated ISRS-aware model.

Report:

- blocking probability;
- accepted lightpath requests;
- selected modulation formats;
- false-feasible and false-infeasible lightpaths;
- average GSNR margin;
- total carried traffic;
- runtime.

This is important because Photonic Network Communications is network-focused.

## Work package 7: rewrite manuscript

Mandatory paper edits:

- Revise title and abstract so that validation scope is not overstated.
- Expand Methods with coupled Raman equations, amplifier/ASE model, ISRS-aware NLI computation, multi-span accumulation and GSNR-to-BER/EVM/GMI/NGMI mapping.
- Add S+C+L grid, power evolution, ISRS tilt, ASE/NLI/TRX decomposition and GSNR-vs-wavelength figures.
- Move row-level held-out table to supplementary material.
- Remove the sentence saying the results support submission.
- Add exact GitHub tag, commit SHA and Zenodo DOI in Data availability.
- Add ORCID identifiers and fix any invalid author email formatting.
- Export all plots as vector PDF/EPS, without chart titles inside the figures.
- Increase references to about 25-35 targeted recent and foundational sources.

## Immediate next command sequence

```bash
git checkout -b pnc-submission-upgrade
mkdir -p docs releases/pnc-v1.0/{gnpy,validation_data,results,figures}
python -m pytest -q
```

Then copy the exact manuscript evidence into `releases/pnc-v1.0/` and build the reproduction script.
