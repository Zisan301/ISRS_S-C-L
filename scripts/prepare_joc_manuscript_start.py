from pathlib import Path

ROOT = Path.cwd()
MANUSCRIPT = ROOT / "manuscript"
MANUSCRIPT.mkdir(exist_ok=True)

claims_lock = """# Journal of Optical Communications Claims Lock

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
"""

outline = """# Journal of Optical Communications Manuscript Outline

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
"""

main_tex = r"""\documentclass[twocolumn]{article}

\usepackage{amsmath}
\usepackage{graphicx}
\usepackage{booktabs}
\usepackage{siunitx}
\usepackage{hyperref}

\title{A Reproducible Recursive GSNR Estimation Framework for Wideband Optical Links with Held-Out C-Band GNPy Cross-Tool Validation}

\author{
Author One\\
Department / University\\
Email
\and
Author Two\\
Department / University\\
Email
}

\date{}

\begin{document}

\maketitle

\begin{abstract}
Wideband optical transmission over S+C+L wavelength grids requires fast and reproducible quality-of-transmission estimation. This paper presents a recursive GSNR estimation framework for wideband optical links, incorporating wavelength-dependent fibre parameters, Raman/ISRS-aware power evolution, amplifier noise accumulation, nonlinear interference estimation, and receiver-noise terms. The framework supports S+C+L grid construction; however, the present external cross-tool validation is intentionally restricted to held-out C-band GNPy cases because the available default GNPy EDFA example generated C-band-compatible validation rows only. A recursive multi-span evaluation mode replaces an earlier analytical span-scaling approximation. In the reproduced C-band validation set, the recursive raw held-out RMSE is 0.5266 dB. A post-model residual calibration reduces the held-out RMSE to 0.2190 dB, with grouped leave-one-wavelength-out and leave-one-span-out checks. A release-level reproduction script and validation-claim guard are provided to prevent unsupported S+C+L validation claims. The results demonstrate a reproducible C-band cross-tool validation workflow for a wideband-capable GSNR estimator, while S-band, L-band, SSFM, and network-level validation remain future work.
\end{abstract}

\textbf{Keywords:} optical communications; GSNR; ISRS; GNPy; wideband transmission; reproducibility

\section{Introduction}
Wideband optical communication systems increasingly require fast quality-of-transmission estimation across broad wavelength grids. Accurate generalized signal-to-noise ratio (GSNR) estimation is important for link design, planning studies, and performance comparison. However, validation across S+C+L bands remains difficult because external reference data, amplifier models, and simulation assumptions must be carefully aligned.

This work presents a reproducible recursive GSNR estimation framework for wideband optical links. The framework supports S+C+L wavelength-grid construction, but the external cross-tool validation reported in this paper is restricted to held-out C-band GNPy cases. This limitation is stated explicitly to avoid claiming broader validation than the current evidence supports.

\section{Related Work}
This section will review GN/EGN modelling, ISRS-aware transmission models, GNPy-based optical-link simulation, and reproducible optical-communication workflows.

\section{Proposed Framework}

\subsection{Wavelength Grid and Launch Power}
Let the channel index be \(i\), wavelength be \(\lambda_i\), optical frequency be \(f_i=c/\lambda_i\), and launch power be \(P_i(0)\). A flat launch profile can be written as
\begin{equation}
P_i(0)=P_0,
\end{equation}
where \(P_0\) is the per-channel launch power.

\subsection{Raman/ISRS Power Evolution}
The longitudinal channel power evolution may be represented as
\begin{equation}
\frac{dP_i(z)}{dz}
=
-\alpha_i P_i(z)
+
\sum_{j \neq i} g_R(f_j-f_i) P_j(z)P_i(z),
\end{equation}
where \(\alpha_i\) is the wavelength-dependent attenuation coefficient and \(g_R\) denotes the Raman gain interaction term.

\subsection{ASE Noise}
For span \(s\), the amplified spontaneous emission contribution can be expressed as
\begin{equation}
N_{\mathrm{ASE},i}^{(s)}
=
n_{\mathrm{sp},i}^{(s)} h f_i
\left(G_i^{(s)}-1\right)B,
\end{equation}
where \(n_{\mathrm{sp}}\) is the spontaneous-emission factor, \(G_i^{(s)}\) is amplifier gain, and \(B\) is the receiver noise bandwidth.

\subsection{Nonlinear Interference}
The nonlinear interference term is represented as
\begin{equation}
N_{\mathrm{NLI},i}^{(s)}
=
\eta_i^{(s)} \left(P_i^{(s)}\right)^3,
\end{equation}
where \(\eta_i^{(s)}\) is an ISRS-aware nonlinear coefficient derived from the span power profile.

\subsection{Recursive Multi-Span Accumulation}
Instead of scaling a single-span estimate analytically, the recursive mode updates the signal and noise terms span by span:
\begin{equation}
N_{\mathrm{tot},i}^{(S)}
=
\sum_{s=1}^{S}
\left(
N_{\mathrm{ASE},i}^{(s)}
+
N_{\mathrm{NLI},i}^{(s)}
\right)
+
N_{\mathrm{TRX},i}.
\end{equation}

The final GSNR is computed as
\begin{equation}
\mathrm{GSNR}_i
=
10\log_{10}
\left(
\frac{P_i^{(S)}}{N_{\mathrm{tot},i}^{(S)}}
\right).
\end{equation}

\subsection{Residual Calibration}
A post-model residual calibration is evaluated only as a correction layer:
\begin{equation}
\hat{G}_{i,\mathrm{corr}}
=
\hat{G}_{i,\mathrm{raw}} - \hat{r}_i,
\end{equation}
where \(\hat{r}_i\) is estimated from calibration rows and then evaluated on held-out rows.

\section{Reproducibility Package}
The project contains a release-level reproduction workflow that regenerates the current diagnostic outputs. A validation-claim guard checks whether full S+C+L external validation is supported. In the present version, the guard blocks the full S+C+L claim because only C-band rows are available.

\section{Results}

\subsection{Recursive Held-Out C-Band Validation}
The recursive raw held-out C-band RMSE is 0.5266 dB. With post-model residual calibration, the held-out RMSE is 0.2190 dB.

\subsection{Grouped Validation}
The grouped leave-one-wavelength-out RMSE is 0.1717 dB, and the grouped leave-one-span-out RMSE is 0.1304 dB for the selected correction model.

\subsection{S+C+L Validation Readiness}
The S/C/L validation guard reports that full S+C+L validation is not yet supported, because S-band and L-band external rows are missing.

\section{Discussion}
The current evidence supports a reproducible C-band GNPy cross-tool validation workflow for a wideband-capable recursive GSNR estimator. It does not support a claim of full S+C+L external validation. Additional S-band and L-band external references, SSFM comparisons, sensitivity analysis, and network-level experiments are required before generalizing the reported accuracy across arbitrary S+C+L deployments.

\section{Conclusion}
This paper presents a reproducible recursive GSNR estimation framework for wideband optical-link modelling. The current release reproduces held-out C-band GNPy validation results and demonstrates improved performance after post-model residual calibration. The study intentionally limits its validation claims to C-band cross-tool evidence. Broader S-band, L-band, SSFM, and network-level validation remain future work.

\bibliographystyle{unsrt}
\bibliography{references}

\end{document}
"""

(MANUSCRIPT / "paper_claims_lock.md").write_text(claims_lock, encoding="utf-8")
(MANUSCRIPT / "joc_manuscript_outline.md").write_text(outline, encoding="utf-8")
(MANUSCRIPT / "main.tex").write_text(main_tex, encoding="utf-8")

print("Created:")
print(MANUSCRIPT / "paper_claims_lock.md")
print(MANUSCRIPT / "joc_manuscript_outline.md")
print(MANUSCRIPT / "main.tex")