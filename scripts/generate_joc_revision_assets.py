from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
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


def save_figure(fig: plt.Figure, stem: str) -> list[str]:
    pdf = FIGURES / f"{stem}.pdf"
    png = FIGURES / f"{stem}.png"
    fig.tight_layout()
    fig.savefig(pdf, bbox_inches="tight")
    fig.savefig(png, dpi=600, bbox_inches="tight")
    plt.close(fig)
    return [str(pdf.relative_to(ROOT)), str(png.relative_to(ROOT))]


def latex_escape(text: str) -> str:
    replacements = {
        "&": r"\&",
        "%": r"\%",
        "_": r"\_",
        "#": r"\#",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text


def metric_table_rows(grouped: dict[str, dict[str, Any]], label: str) -> list[str]:
    rows = []
    for key, metrics in sorted(grouped.items(), key=lambda item: float(item[0])):
        rows.append(
            f"{label.format(float(key))} & {int(metrics['n'])} & "
            f"{metrics['rmse_db']:.4f} & {metrics['mae_db']:.4f} & "
            f"{metrics['bias_db']:.4f} & {metrics['max_abs_error_db']:.4f} \\\\"
        )
    return rows


def write_numbers(summary: dict[str, Any], correction: dict[str, Any], grouped: dict[str, Any]) -> Path:
    best = correction["best_model_by_calibration_leave_one_out_rmse"]
    raw = correction["model_summaries"]["none"]["heldout_raw"]
    corrected = correction["model_summaries"][best]["heldout_corrected"]
    low = min(float(item["gnpy_effective_channel_power_dbm"]) for item in summary["power_reference_audit"])
    high = max(float(item["gnpy_effective_channel_power_dbm"]) for item in summary["power_reference_audit"])
    text = f"""% Auto-generated. Do not edit manually.
\\newcommand{{\\MatchedSweepRows}}{{{int(summary['rows'])}}}
\\newcommand{{\\MatchedConditions}}{{{int(summary['operating_conditions'])}}}
\\newcommand{{\\MatchedChannels}}{{{int(summary['channels_per_condition'])}}}
\\newcommand{{\\MatchedOverallRMSE}}{{{summary['overall']['rmse_db']:.4f}}}
\\newcommand{{\\MatchedOverallMAE}}{{{summary['overall']['mae_db']:.4f}}}
\\newcommand{{\\MatchedOverallBias}}{{{summary['overall']['bias_db']:.4f}}}
\\newcommand{{\\MatchedOverallMaxError}}{{{summary['overall']['max_abs_error_db']:.4f}}}
\\newcommand{{\\MatchedMinPower}}{{{low:.2f}}}
\\newcommand{{\\MatchedMaxPower}}{{{high:.2f}}}
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
\\caption{Power-aligned C-band cross-tool error grouped by effective channel power.}
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
\\caption{Power-aligned C-band cross-tool error grouped by span count.}
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

    audit_rows = []
    for item in sorted(summary["power_reference_audit"], key=lambda x: (x["requested_power_offset_db"], x["spans"])):
        audit_rows.append(
            f"{item['requested_power_offset_db']:+.1f} & {int(item['spans'])} & "
            f"{item['gnpy_effective_channel_power_dbm']:.2f} & "
            f"{item['model_launch_power_dbm']:.2f} & "
            f"{item['channel_power_spread_db']:.3f} & {int(item['channels'])} \\\\"
        )
    audit_tex = """\\begin{table}[htbp]
\\centering
\\caption{Power-reference audit for the matched GNPy sweep. The GNPy command-line value is an offset; the model uses the effective power reported for the propagated channels.}
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
    return [power_path, span_path, audit_path]


def figure_legacy_heldout(correction: dict[str, Any], comparison_metrics: dict[str, Any]) -> list[str]:
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
        ax.text(bar.get_x() + bar.get_width() / 2, value + max(values) * 0.025, f"{value:.3f}", ha="center", va="bottom")
    ax.set_ylabel("RMSE (dB)")
    ax.set_ylim(0, max(values) * 1.20)
    ax.grid(True, axis="y", linewidth=0.5, alpha=0.35)
    return save_figure(fig, "figure-3-legacy-heldout-rmse")


def figure_parity(rows: pd.DataFrame) -> list[str]:
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
    ax.plot([low - pad, high + pad], [low - pad, high + pad], linestyle="--", linewidth=1, label="Ideal agreement")
    ax.set_xlabel("GNPy GSNR (dB)")
    ax.set_ylabel("Recursive-model GSNR (dB)")
    ax.set_xlim(low - pad, high + pad)
    ax.set_ylim(low - pad, high + pad)
    ax.set_aspect("equal", adjustable="box")
    ax.grid(True, linewidth=0.5, alpha=0.35)
    ax.legend(frameon=False)
    return save_figure(fig, "figure-5-power-aligned-parity")


def figure_robustness(rows: pd.DataFrame, summary: dict[str, Any]) -> list[str]:
    fig, axes = plt.subplots(1, 2, figsize=(8.0, 3.4), sharey=True)

    by_power = sorted(summary["by_effective_launch_power_dbm"].items(), key=lambda item: float(item[0]))
    power_x = [float(key) for key, _ in by_power]
    power_y = [float(metrics["rmse_db"]) for _, metrics in by_power]
    axes[0].plot(power_x, power_y, marker="o")
    axes[0].set_xlabel("Effective channel power (dBm)")
    axes[0].set_ylabel("RMSE versus GNPy (dB)")
    axes[0].grid(True, linewidth=0.5, alpha=0.35)
    axes[0].text(0.02, 0.96, "A", transform=axes[0].transAxes, va="top", fontweight="bold")

    by_span = sorted(summary["by_span"].items(), key=lambda item: float(item[0]))
    span_x = [int(float(key)) for key, _ in by_span]
    span_y = [float(metrics["rmse_db"]) for _, metrics in by_span]
    axes[1].plot(span_x, span_y, marker="s")
    axes[1].set_xlabel("Span count")
    axes[1].set_xticks(span_x)
    axes[1].grid(True, linewidth=0.5, alpha=0.35)
    axes[1].text(0.02, 0.96, "B", transform=axes[1].transAxes, va="top", fontweight="bold")
    return save_figure(fig, "figure-6-power-aligned-robustness")


def write_copy_manifest(paths: list[Path]) -> Path:
    lines = [
        "Copy these generated files into the Overleaf project:",
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

    generated: list[Path] = []
    generated.extend(Path(ROOT / item) for item in figure_legacy_heldout(correction, comparison_metrics))
    generated.extend(Path(ROOT / item) for item in figure_parity(matched_rows))
    generated.extend(Path(ROOT / item) for item in figure_robustness(matched_rows, matched_summary))
    generated.append(write_numbers(matched_summary, correction, grouped))
    generated.extend(write_metric_tables(matched_summary))
    manifest = write_copy_manifest(generated)
    generated.append(manifest)

    summary = {
        "generated_files": [str(path.relative_to(ROOT)) for path in generated],
        "matched_rows": matched_summary["rows"],
        "matched_operating_conditions": matched_summary["operating_conditions"],
        "matched_overall_metrics": matched_summary["overall"],
        "claim_policy": matched_summary["claim_policy"],
    }
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

