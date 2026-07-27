from __future__ import annotations

import copy
import csv
import json
import math
import subprocess
import sys
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch
import numpy as np
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from isrs_scl.system.grid import build_grid
from isrs_scl.system.parameters import apply_defaults, validate_config

GENERATED = ROOT / "releases" / "pnc-v1.0" / "generated"
OUTPUT = GENERATED / "joc_revision_assets"
FIGURES = OUTPUT / "figures"
TABLES = OUTPUT / "generated"
SUMMARY_PATH = OUTPUT / "joc_revision_asset_summary.json"

for directory in (OUTPUT, FIGURES, TABLES):
    directory.mkdir(parents=True, exist_ok=True)

plt.rcParams.update(
    {
        "font.family": "sans-serif",
        "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
        "font.size": 9,
        "axes.labelsize": 9,
        "legend.fontsize": 8,
        "xtick.labelsize": 8,
        "ytick.labelsize": 8,
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
    }
)


def require(path: Path) -> Path:
    if not path.exists():
        raise FileNotFoundError(
            f"Missing required file: {path}\n"
            "Run python releases\\pnc-v1.0\\reproduce_joc_revision.py first."
        )
    return path


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(require(path).read_text(encoding="utf-8"))


def load_config() -> dict[str, Any]:
    config_path = ROOT / "config_q2_final.yaml"
    raw = yaml.safe_load(require(config_path).read_text(encoding="utf-8"))
    cfg = apply_defaults(raw)
    validate_config(cfg, base_dir=config_path.parent)
    return cfg


def save_figure(fig: plt.Figure, stem: str) -> list[Path]:
    pdf = FIGURES / f"{stem}.pdf"
    png = FIGURES / f"{stem}.png"
    fig.tight_layout()
    fig.savefig(pdf, bbox_inches="tight")
    fig.savefig(png, dpi=600, bbox_inches="tight")
    plt.close(fig)
    return [pdf, png]


def latex_escape(text: str) -> str:
    replacements = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "_": r"\_",
        "#": r"\#",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text


def git_release_metadata() -> tuple[str, str]:
    try:
        commit = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT,
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        commit = "unknown"

    try:
        tags = subprocess.check_output(
            ["git", "tag", "--points-at", "HEAD"],
            cwd=ROOT,
            text=True,
            stderr=subprocess.DEVNULL,
        ).splitlines()
    except (OSError, subprocess.CalledProcessError):
        tags = []

    release_tags = sorted(tag.strip() for tag in tags if tag.strip().startswith("joc-submission-v"))
    tag = release_tags[-1] if release_tags else "joc-submission-v1.3"
    return tag, commit


def write_release_metadata() -> Path:
    tag, commit = git_release_metadata()
    short = commit[:12] if commit != "unknown" else commit
    text = f"""% Auto-generated from the current Git checkout.
\\newcommand{{\\CodeTag}}{{\\texttt{{{latex_escape(tag)}}}}}
\\newcommand{{\\CodeCommitFull}}{{{latex_escape(commit)}}}
\\newcommand{{\\CodeCommit}}{{\\href{{https://github.com/Zisan301/ISRS_S-C-L/commit/{commit}}}{{\\texttt{{{latex_escape(short)}}}}}}}
"""
    path = TABLES / "release_metadata.tex"
    path.write_text(text, encoding="utf-8")
    return path


def metric_table_rows(grouped: dict[str, dict[str, Any]], label: str) -> list[str]:
    rows: list[str] = []
    for key, metrics in sorted(grouped.items(), key=lambda item: float(item[0])):
        rows.append(
            f"{label.format(float(key))} & {int(metrics['n'])} & "
            f"{metrics['rmse_db']:.4f} & {metrics['mae_db']:.4f} & "
            f"{metrics['bias_db']:.4f} & {metrics['max_abs_error_db']:.4f} \\\\"
        )
    return rows


def write_numbers(
    summary: dict[str, Any],
    correction: dict[str, Any],
    grouped: dict[str, Any],
) -> Path:
    best = correction["best_model_by_calibration_leave_one_out_rmse"]
    raw = correction["model_summaries"]["none"]["heldout_raw"]
    corrected = correction["model_summaries"][best]["heldout_corrected"]
    low = min(float(item["gnpy_effective_channel_power_dbm"]) for item in summary["power_reference_audit"])
    high = max(float(item["gnpy_effective_channel_power_dbm"]) for item in summary["power_reference_audit"])

    centered_rms = math.sqrt(
        max(
            0.0,
            float(summary["overall"]["rmse_db"]) ** 2
            - float(summary["overall"]["bias_db"]) ** 2,
        )
    )
    condition_rmse = [float(item["rmse_db"]) for item in summary["condition_metrics"]]
    span_rmse = [float(item["rmse_db"]) for item in summary["by_span"].values()]

    text = f"""% Auto-generated. Do not edit manually.
\\newcommand{{\\MatchedSweepRows}}{{{int(summary['rows'])}}}
\\newcommand{{\\MatchedConditions}}{{{int(summary['operating_conditions'])}}}
\\newcommand{{\\MatchedChannels}}{{{int(summary['channels_per_condition'])}}}
\\newcommand{{\\MatchedOverallRMSE}}{{{summary['overall']['rmse_db']:.4f}}}
\\newcommand{{\\MatchedOverallMAE}}{{{summary['overall']['mae_db']:.4f}}}
\\newcommand{{\\MatchedOverallBias}}{{{summary['overall']['bias_db']:.4f}}}
\\newcommand{{\\MatchedOverallMaxError}}{{{summary['overall']['max_abs_error_db']:.4f}}}
\\newcommand{{\\MatchedCenteredRMS}}{{{centered_rms:.4f}}}
\\newcommand{{\\MatchedMinPower}}{{{low:.2f}}}
\\newcommand{{\\MatchedMaxPower}}{{{high:.2f}}}
\\newcommand{{\\ConditionMinRMSE}}{{{min(condition_rmse):.4f}}}
\\newcommand{{\\ConditionMaxRMSE}}{{{max(condition_rmse):.4f}}}
\\newcommand{{\\SpanMinRMSE}}{{{min(span_rmse):.4f}}}
\\newcommand{{\\SpanMaxRMSE}}{{{max(span_rmse):.4f}}}
\\newcommand{{\\LegacyRawRMSE}}{{{raw['rmse_db']:.4f}}}
\\newcommand{{\\LegacyCorrectedRMSE}}{{{corrected['rmse_db']:.4f}}}
\\newcommand{{\\GroupedWavelengthRMSE}}{{{grouped['models'][best]['leave_one_wavelength_out']['overall']['rmse_db']:.4f}}}
\\newcommand{{\\GroupedSpanRMSE}}{{{grouped['models'][best]['leave_one_span_out']['overall']['rmse_db']:.4f}}}
"""
    path = TABLES / "joc_revision_numbers.tex"
    path.write_text(text, encoding="utf-8")
    return path


def write_metric_tables(summary: dict[str, Any]) -> list[Path]:
    by_power = summary["by_effective_launch_power_dbm"]
    power_rows = metric_table_rows(by_power, "{:+.2f} dBm/channel")
    power_tex = """\\begin{table}[htbp]
\\centering
\\caption{Scenario-matched C-band cross-tool error grouped by effective channel power.}
\\label{tab:matched-power}
\\begin{tabular}{lrrrrr}
\\toprule
Effective power & Rows & RMSE, dB & MAE, dB & Bias, dB & Max. error, dB \\\\
\\midrule
""" + "\n".join(power_rows) + """
\\bottomrule
\\end{tabular}
\\end{table}
"""
    power_path = TABLES / "table_matched_power.tex"
    power_path.write_text(power_tex, encoding="utf-8")

    by_span = summary["by_span"]
    span_rows = metric_table_rows(by_span, "{:.0f} span(s)")
    span_tex = """\\begin{table}[htbp]
\\centering
\\caption{Scenario-matched C-band cross-tool error grouped by span count.}
\\label{tab:matched-span}
\\begin{tabular}{lrrrrr}
\\toprule
Span group & Rows & RMSE, dB & MAE, dB & Bias, dB & Max. error, dB \\\\
\\midrule
""" + "\n".join(span_rows) + """
\\bottomrule
\\end{tabular}
\\end{table}
"""
    span_path = TABLES / "table_matched_span.tex"
    span_path.write_text(span_tex, encoding="utf-8")

    audit_rows: list[str] = []
    for item in sorted(
        summary["power_reference_audit"],
        key=lambda row: (row["requested_power_offset_db"], row["spans"]),
    ):
        audit_rows.append(
            f"{item['requested_power_offset_db']:+.1f} & {int(item['spans'])} & "
            f"{item['gnpy_effective_channel_power_dbm']:.2f} & "
            f"{item['model_launch_power_dbm']:.2f} & "
            f"{item['channel_power_spread_db']:.3f} & {int(item['channels'])} \\\\"
        )
    audit_tex = """\\begin{table}[htbp]
\\centering
\\caption{Power-reference audit for the matched GNPy sweep. The GNPy command-line value is an offset; the model uses the median effective power printed for the propagated channels.}
\\label{tab:power-audit}
\\begin{tabular}{rrrrrr}
\\toprule
Offset, dB & Spans & GNPy power, dBm & Model power, dBm & Spread, dB & Channels \\\\
\\midrule
""" + "\n".join(audit_rows) + """
\\bottomrule
\\end{tabular}
\\end{table}
"""
    audit_path = TABLES / "table_power_reference_audit.tex"
    audit_path.write_text(audit_tex, encoding="utf-8")

    condition_lookup = {
        (float(item["requested_power_offset_db"]), int(item["spans"])): item
        for item in summary["condition_metrics"]
    }
    condition_rows: list[str] = []
    for offset in sorted({key[0] for key in condition_lookup}):
        cells: list[str] = []
        for spans in (1, 4, 8):
            item = condition_lookup[(offset, spans)]
            cells.append(
                f"{float(item['rmse_db']):.4f} "
                f"({float(item['gnpy_effective_channel_power_dbm']):.2f})"
            )
        condition_rows.append(
            f"${offset:+.0f}$ dB & " + " & ".join(cells) + r" \\"
        )
    condition_tex = """\\begin{table}[htbp]
\\centering
\\caption{Condition-level RMSE for the nine principal C-band scenarios. Each cell reports RMSE in dB, with the median GNPy-reported channel power in dBm shown in parentheses.}
\\label{tab:condition-rmse}
\\small
\\begin{tabular}{@{}lccc@{}}
\\toprule
Requested power offset & 1 span & 4 spans & 8 spans \\\\
\\midrule
""" + "\n".join(condition_rows) + """
\\bottomrule
\\end{tabular}
\\end{table}
"""
    condition_path = TABLES / "table_condition_rmse.tex"
    condition_path.write_text(condition_tex, encoding="utf-8")

    return [power_path, span_path, audit_path, condition_path]


def figure_spectral_scope(
    cfg: dict[str, Any],
    matched_rows: pd.DataFrame,
) -> list[Path]:
    full_cfg = copy.deepcopy(cfg)
    full_cfg["grid"]["mode"] = "full_scl"
    full_grid = build_grid(full_cfg["grid"])

    subset_cfg = copy.deepcopy(cfg)
    subset_cfg["grid"]["mode"] = "paper_240_subset"
    subset_grid = build_grid(subset_cfg["grid"])

    full = full_grid.to_frame().sort_values("wavelength_nm")
    subset_min = float(np.min(subset_grid.wavelengths_nm))
    subset_max = float(np.max(subset_grid.wavelengths_nm))
    comparison_min = float(matched_rows["gnpy_wavelength_nm"].min())
    comparison_max = float(matched_rows["gnpy_wavelength_nm"].max())

    fig, ax = plt.subplots(figsize=(7.4, 3.4))
    band_markers = {"S": "^", "C": "o", "L": "s"}
    for band in ("S", "C", "L"):
        group = full[full["band"] == band]
        ax.scatter(
            group["wavelength_nm"],
            np.zeros(len(group)),
            marker=band_markers[band],
            s=9,
            label=f"{band} band",
        )

    ax.plot(
        [subset_min, subset_max],
        [-0.42, -0.42],
        linewidth=4,
        solid_capstyle="butt",
    )
    ax.plot(
        [comparison_min, comparison_max],
        [-0.82, -0.82],
        linewidth=7,
        solid_capstyle="butt",
    )
    ax.axvline(1530.0, linestyle="--", linewidth=1)
    ax.axvline(1565.0, linestyle="--", linewidth=1)
    ax.set_xlabel("Wavelength (nm)")
    ax.set_xlim(1460, 1625)
    ax.set_ylim(-1.05, 0.25)
    ax.set_yticks([0.0, -0.42, -0.82])
    ax.set_yticklabels(["Implemented grid", "Optional subset", "Compared block"])
    ax.grid(True, axis="x", linewidth=0.4, alpha=0.3)
    ax.legend(frameon=False, ncol=3, loc="upper center")
    return save_figure(fig, "figure-1-spectral-scope")


def figure_framework_architecture() -> list[Path]:
    labels = [
        "Exact-frequency\nS+C+L grid",
        "Coupled RK4\nRaman/ISRS",
        "Band-aware\namplifier + ASE",
        "Power-profile\nSCI/XCI model",
        "Recursive\nspan propagation",
        "GSNR and\nQoT metrics",
        "GNPy\ncomparison",
    ]

    fig, ax = plt.subplots(figsize=(10.0, 2.7))
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 3.5)
    ax.axis("off")

    box_w = 1.55
    box_h = 0.95
    y = 1.85
    x_positions = np.linspace(0.35, 12.1, len(labels))

    for index, (x, label) in enumerate(zip(x_positions, labels)):
        box = FancyBboxPatch(
            (x, y),
            box_w,
            box_h,
            boxstyle="round,pad=0.03",
            linewidth=1.0,
            facecolor="white",
        )
        ax.add_patch(box)
        ax.text(x + box_w / 2, y + box_h / 2, label, ha="center", va="center")
        if index < len(labels) - 1:
            arrow = FancyArrowPatch(
                (x + box_w, y + box_h / 2),
                (x_positions[index + 1], y + box_h / 2),
                arrowstyle="-|>",
                mutation_scale=10,
                linewidth=1.0,
            )
            ax.add_patch(arrow)

    lower = FancyBboxPatch(
        (2.0, 0.35),
        10.0,
        0.72,
        boxstyle="round,pad=0.03",
        linewidth=1.0,
        facecolor="white",
    )
    ax.add_patch(lower)
    ax.text(
        7.0,
        0.71,
        "One-command reproduction, figure provenance, grouped checks and explicit S/C/L claim guard",
        ha="center",
        va="center",
    )
    return save_figure(fig, "figure-2-framework-architecture")


def figure_parity(rows: pd.DataFrame) -> list[Path]:
    fig, ax = plt.subplots(figsize=(4.8, 4.4))
    markers = {1: "o", 4: "s", 8: "^"}
    for spans, group in rows.groupby("spans", sort=True):
        ax.scatter(
            group["gnpy_gsnr_db"],
            group["model_recursive_gsnr_db"],
            marker=markers.get(int(spans), "o"),
            s=18,
            alpha=0.65,
            label=f"{int(spans)} span(s)",
        )
    low = float(min(rows["gnpy_gsnr_db"].min(), rows["model_recursive_gsnr_db"].min()))
    high = float(max(rows["gnpy_gsnr_db"].max(), rows["model_recursive_gsnr_db"].max()))
    pad = 0.4
    ax.plot(
        [low - pad, high + pad],
        [low - pad, high + pad],
        linestyle="--",
        linewidth=1,
        label="Ideal agreement",
    )
    ax.set_xlabel("GNPy GSNR (dB)")
    ax.set_ylabel("Recursive-model GSNR (dB)")
    ax.set_xlim(low - pad, high + pad)
    ax.set_ylim(low - pad, high + pad)
    ax.set_aspect("equal", adjustable="box")
    ax.grid(True, linewidth=0.5, alpha=0.35)
    ax.legend(frameon=False)
    return save_figure(fig, "figure-3-power-aligned-parity")


def figure_condition_robustness(summary: dict[str, Any]) -> list[Path]:
    frame = pd.DataFrame(summary["condition_metrics"])
    fig, ax = plt.subplots(figsize=(6.4, 4.0))

    markers = {1: "o", 4: "s", 8: "^"}
    for spans, group in frame.groupby("spans", sort=True):
        group = group.sort_values("requested_power_offset_db")
        ax.plot(
            group["requested_power_offset_db"],
            group["rmse_db"],
            marker=markers.get(int(spans), "o"),
            label=f"{int(spans)} span(s)",
        )
        for _, row in group.iterrows():
            ax.annotate(
                f"{float(row['rmse_db']):.3f}",
                (float(row["requested_power_offset_db"]), float(row["rmse_db"])),
                xytext=(0, 7 if int(spans) == 1 else -12),
                textcoords="offset points",
                ha="center",
            )

    ax.set_xlabel("GNPy requested power offset (dB)")
    ax.set_ylabel("Condition-level RMSE (dB)")
    ax.set_xticks(sorted(frame["requested_power_offset_db"].unique()))
    ax.grid(True, linewidth=0.5, alpha=0.35)
    ax.legend(frameon=False)
    return save_figure(fig, "figure-4-condition-level-robustness")


def figure_legacy_heldout(
    correction: dict[str, Any],
    comparison_metrics: dict[str, Any],
) -> list[Path]:
    best = correction["best_model_by_calibration_leave_one_out_rmse"]
    labels = ["Analytical raw", "Recursive raw", "Post-model corrected"]
    values = [
        comparison_metrics["current_analytical_raw"]["rmse_db"],
        correction["model_summaries"]["none"]["heldout_raw"]["rmse_db"],
        correction["model_summaries"][best]["heldout_corrected"]["rmse_db"],
    ]
    hatches = ["//", "xx", ".."]
    fig, ax = plt.subplots(figsize=(5.8, 3.5))
    bars = ax.bar(labels, values, edgecolor="black")
    for bar, hatch, value in zip(bars, hatches, values):
        bar.set_hatch(hatch)
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            value + max(values) * 0.025,
            f"{value:.3f}",
            ha="center",
            va="bottom",
        )
    ax.set_ylabel("RMSE (dB)")
    ax.set_ylim(0, max(values) * 1.20)
    ax.grid(True, axis="y", linewidth=0.5, alpha=0.35)
    return save_figure(fig, "figure-5-legacy-heldout-rmse")


def figure_grouped_cv(
    grouped: dict[str, Any],
    correction: dict[str, Any],
) -> list[Path]:
    best = correction["best_model_by_calibration_leave_one_out_rmse"]
    model = grouped["models"][best]
    wavelength_groups = model["leave_one_wavelength_out"]["groups"]
    span_groups = model["leave_one_span_out"]["groups"]

    fig, axes = plt.subplots(1, 2, figsize=(8.0, 3.5), sharey=True)

    wl_x = np.arange(len(wavelength_groups))
    wl_y = [float(item["rmse_db"]) for item in wavelength_groups]
    axes[0].plot(wl_x, wl_y, marker="o")
    axes[0].set_xticks(wl_x)
    axes[0].set_xticklabels([f"{item['heldout_group']} nm" for item in wavelength_groups], rotation=15)
    axes[0].set_ylabel("RMSE (dB)")
    axes[0].grid(True, linewidth=0.5, alpha=0.35)
    axes[0].text(0.02, 0.96, "A", transform=axes[0].transAxes, va="top", fontweight="bold")
    for x, value in zip(wl_x, wl_y):
        axes[0].annotate(f"{value:.3f}", (x, value), xytext=(0, 6), textcoords="offset points", ha="center")

    span_x = np.arange(len(span_groups))
    span_y = [float(item["rmse_db"]) for item in span_groups]
    axes[1].plot(span_x, span_y, marker="o")
    axes[1].set_xticks(span_x)
    axes[1].set_xticklabels(
        [f"{item['heldout_group']} span" + ("s" if str(item["heldout_group"]) != "1" else "") for item in span_groups],
        rotation=15,
    )
    axes[1].grid(True, linewidth=0.5, alpha=0.35)
    axes[1].text(0.02, 0.96, "B", transform=axes[1].transAxes, va="top", fontweight="bold")
    for x, value in zip(span_x, span_y):
        axes[1].annotate(f"{value:.3f}", (x, value), xytext=(0, 6), textcoords="offset points", ha="center")

    return save_figure(fig, "figure-6-grouped-cross-validation")


def figure_validation_coverage(readiness: dict[str, Any]) -> list[Path]:
    labels = ["S", "C", "L"]
    values = [int(readiness.get("rows_by_band", {}).get(label, 0)) for label in labels]

    fig, ax = plt.subplots(figsize=(5.0, 3.5))
    bars = ax.bar(labels, values, edgecolor="black")
    for bar, value in zip(bars, values):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            value + 0.15,
            str(value),
            ha="center",
            va="bottom",
        )
    ax.set_xlabel("Optical band")
    ax.set_ylabel("Committed external-validation rows")
    ax.set_ylim(0, max(values + [1]) * 1.18)
    ax.grid(True, axis="y", linewidth=0.5, alpha=0.35)
    return save_figure(fig, "figure-s1-validation-coverage")


def figure_provenance_rows() -> list[dict[str, str]]:
    return [
        {
            "figure": "Figure 1",
            "role": "Explanatory configuration view",
            "generator": "scripts/generate_joc_revision_assets.py",
            "inputs": "config_q2_final.yaml; src/isrs_scl/system/grid.py; cband_launch_power_sweep_model_comparison.csv",
            "statement": "Full implemented grid, optional subset and exact compared C-band block. No performance metric is manually entered.",
        },
        {
            "figure": "Figure 2",
            "role": "Explanatory workflow schematic",
            "generator": "scripts/generate_joc_revision_assets.py",
            "inputs": "Tagged module architecture and reproduction workflow",
            "statement": "Author-generated schematic; contains no measured or simulated numerical result.",
        },
        {
            "figure": "Figure 3",
            "role": "Numerical result",
            "generator": "scripts/generate_joc_revision_assets.py",
            "inputs": "cband_launch_power_sweep_model_comparison.csv",
            "statement": "All 567 GNPy/model GSNR pairs are plotted directly from the reproduced CSV.",
        },
        {
            "figure": "Figure 4",
            "role": "Numerical result",
            "generator": "scripts/generate_joc_revision_assets.py",
            "inputs": "cband_launch_power_sweep_summary.json: condition_metrics",
            "statement": "Nine condition-level RMSE values are read directly from the reproduced summary.",
        },
        {
            "figure": "Figure 5",
            "role": "Numerical diagnostic",
            "generator": "scripts/generate_joc_revision_assets.py",
            "inputs": "recursive_heldout_cband_metrics.json; recursive_cband_correction_summary.json",
            "statement": "Legacy analytical, recursive and post-model RMSE values are read directly from reproduced JSON.",
        },
        {
            "figure": "Figure S2",
            "role": "Supplementary numerical diagnostic",
            "generator": "scripts/generate_joc_revision_assets.py",
            "inputs": "recursive_cband_grouped_cv_summary.json",
            "statement": "Grouped wavelength/span RMSE values are read directly from reproduced JSON.",
        },
        {
            "figure": "Figure S1",
            "role": "Supplementary numerical audit",
            "generator": "scripts/generate_joc_revision_assets.py",
            "inputs": "scl_external_validation_readiness.json",
            "statement": "Band-coverage counts and claim-guard status are read directly from reproduced JSON.",
        },
    ]


def write_figure_provenance() -> list[Path]:
    rows = figure_provenance_rows()

    csv_path = TABLES / "figure_provenance.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    json_path = TABLES / "figure_provenance.json"
    json_path.write_text(json.dumps(rows, indent=2), encoding="utf-8")

    tex_rows = []
    for row in rows:
        tex_rows.append(
            f"{latex_escape(row['figure'])} & "
            f"{latex_escape(row['role'])} & "
            f"\\path{{{row['generator']}}} & "
            f"{latex_escape(row['statement'])} \\\\"
        )

    tex = """\\begin{longtable}{@{}p{0.10\\textwidth}p{0.19\\textwidth}p{0.27\\textwidth}p{0.36\\textwidth}@{}}
\\caption{Figure provenance and relationship to reproduced project outputs.}
\\label{tab:figure-provenance}\\\\
\\toprule
Figure & Role & Generating source & Provenance statement \\\\
\\midrule
\\endfirsthead
\\toprule
Figure & Role & Generating source & Provenance statement \\\\
\\midrule
\\endhead
""" + "\n".join(tex_rows) + """
\\bottomrule
\\end{longtable}
"""
    tex_path = TABLES / "table_figure_provenance.tex"
    tex_path.write_text(tex, encoding="utf-8")
    return [csv_path, json_path, tex_path]


def write_copy_manifest(paths: list[Path]) -> Path:
    lines = [
        "Copy these regenerated files into the Overleaf project:",
        "",
    ]
    for path in paths:
        lines.append(str(path.relative_to(OUTPUT)).replace("\\", "/"))
    manifest = OUTPUT / "COPY_TO_OVERLEAF.txt"
    manifest.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return manifest


def main() -> int:
    matched_rows = pd.read_csv(require(GENERATED / "cband_launch_power_sweep_model_comparison.csv"))
    matched_summary = load_json(GENERATED / "cband_launch_power_sweep_summary.json")
    correction = load_json(GENERATED / "recursive_cband_correction_summary.json")
    grouped = load_json(GENERATED / "recursive_cband_grouped_cv_summary.json")
    comparison_metrics = load_json(GENERATED / "recursive_heldout_cband_metrics.json")
    readiness = load_json(GENERATED / "scl_external_validation_readiness.json")
    cfg = load_config()

    generated: list[Path] = []
    generated.extend(figure_spectral_scope(cfg, matched_rows))
    generated.extend(figure_framework_architecture())
    generated.extend(figure_parity(matched_rows))
    generated.extend(figure_condition_robustness(matched_summary))
    generated.extend(figure_legacy_heldout(correction, comparison_metrics))
    generated.extend(figure_grouped_cv(grouped, correction))
    generated.extend(figure_validation_coverage(readiness))
    generated.append(write_numbers(matched_summary, correction, grouped))
    generated.append(write_release_metadata())
    generated.extend(write_metric_tables(matched_summary))
    generated.extend(write_figure_provenance())

    # Bias-audit tables are generated by scripts/generate_joc_bias_audit.py.
    # Include them in the Overleaf copy manifest when present.
    for bias_table in (
        TABLES / "table_bias_audit_summary.tex",
        TABLES / "table_bias_audit_center_channels.tex",
    ):
        if bias_table.exists():
            generated.append(bias_table)

    manifest = write_copy_manifest(generated)
    generated.append(manifest)

    summary = {
        "generated_files": [str(path.relative_to(ROOT)) for path in generated],
        "matched_rows": matched_summary["rows"],
        "matched_operating_conditions": matched_summary["operating_conditions"],
        "matched_overall_metrics": matched_summary["overall"],
        "figure_policy": (
            "Figures 1 and 2 are explanatory outputs generated from the tagged configuration "
            "and code architecture. Figures 3-6 and Figure S1 are generated directly from "
            "reproduced CSV/JSON evidence. No numerical figure is manually redrawn."
        ),
        "claim_policy": matched_summary["claim_policy"],
    }
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
