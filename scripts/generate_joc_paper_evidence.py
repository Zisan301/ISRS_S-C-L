from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
GENERATED = ROOT / "releases" / "pnc-v1.0" / "generated"
FIGURES = GENERATED / "joc_figures"
TABLES = GENERATED / "joc_tables"
SUMMARY_PATH = GENERATED / "joc_paper_evidence_summary.json"

FIGURES.mkdir(parents=True, exist_ok=True)
TABLES.mkdir(parents=True, exist_ok=True)


def require(path: Path) -> Path:
    if not path.exists():
        raise FileNotFoundError(
            f"Missing required reproduced output: {path}\n"
            "Run: python releases\\pnc-v1.0\\reproduce_recursive_diagnostics.py"
        )
    return path


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(require(path).read_text(encoding="utf-8"))


def metric_row(label: str, metrics: dict[str, Any]) -> dict[str, Any]:
    return {
        "Evidence": label,
        "N": metrics.get("n"),
        "RMSE (dB)": metrics.get("rmse_db"),
        "MAE (dB)": metrics.get("mae_db"),
        "Bias (dB)": metrics.get("bias_db"),
        "Max abs. error (dB)": metrics.get("max_abs_error_db"),
    }


def save_figure(fig: plt.Figure, name: str) -> list[str]:
    pdf = FIGURES / f"{name}.pdf"
    png = FIGURES / f"{name}.png"
    fig.tight_layout()
    fig.savefig(pdf, bbox_inches="tight")
    fig.savefig(png, dpi=300, bbox_inches="tight")
    plt.close(fig)
    return [str(pdf.relative_to(ROOT)), str(png.relative_to(ROOT))]


def write_table(df: pd.DataFrame, name: str) -> list[str]:
    csv_path = TABLES / f"{name}.csv"
    tex_path = TABLES / f"{name}.tex"

    df.to_csv(csv_path, index=False)

    tex = df.to_latex(
        index=False,
        escape=True,
        float_format=lambda value: f"{value:.4f}",
    )
    tex_path.write_text(tex, encoding="utf-8")

    return [str(csv_path.relative_to(ROOT)), str(tex_path.relative_to(ROOT))]


def figure_recursive_vs_analytical(frame: pd.DataFrame) -> list[str]:
    fig, ax = plt.subplots(figsize=(6.0, 4.0))

    for spans, group in frame.groupby("spans"):
        group = group.sort_values("target_wavelength_nm")
        ax.plot(
            group["target_wavelength_nm"],
            group["recursive_minus_analytical_raw_db"],
            marker="o",
            linestyle="-",
            label=f"{int(spans)} span(s)",
        )

    ax.axhline(0.0, linestyle="--", linewidth=1)
    ax.set_xlabel("Target wavelength (nm)")
    ax.set_ylabel("Recursive - analytical GSNR (dB)")
    ax.legend(frameon=False)
    ax.grid(True, linewidth=0.5, alpha=0.4)

    return save_figure(fig, "fig1_recursive_vs_analytical")


def figure_gnpy_vs_recursive(frame: pd.DataFrame) -> list[str]:
    fig, ax = plt.subplots(figsize=(4.8, 4.8))

    ax.scatter(
        frame["gnpy_gsnr_db"],
        frame["current_recursive_raw_model_gsnr_db"],
        marker="o",
    )

    lo = min(frame["gnpy_gsnr_db"].min(), frame["current_recursive_raw_model_gsnr_db"].min())
    hi = max(frame["gnpy_gsnr_db"].max(), frame["current_recursive_raw_model_gsnr_db"].max())
    pad = 0.5
    ax.plot([lo - pad, hi + pad], [lo - pad, hi + pad], linestyle="--", linewidth=1)

    ax.set_xlabel("GNPy GSNR (dB)")
    ax.set_ylabel("Recursive model GSNR (dB)")
    ax.set_aspect("equal", adjustable="box")
    ax.grid(True, linewidth=0.5, alpha=0.4)

    return save_figure(fig, "fig2_gnpy_vs_recursive_cband")


def figure_raw_corrected_rmse(correction: dict[str, Any], grouped: dict[str, Any], launch_summary: dict[str, Any]) -> list[str]:
    best = correction["best_model_by_calibration_leave_one_out_rmse"]

    labels = [
        "Held-out raw",
        "Held-out corrected",
        "LO wavelength",
        "LO span",
        "Launch sweep raw",
    ]
    values = [
        correction["model_summaries"]["none"]["heldout_raw"]["rmse_db"],
        correction["model_summaries"][best]["heldout_corrected"]["rmse_db"],
        grouped["models"][best]["leave_one_wavelength_out"]["overall"]["rmse_db"],
        grouped["models"][best]["leave_one_span_out"]["overall"]["rmse_db"],
        launch_summary["overall"]["rmse_db"],
    ]

    fig, ax = plt.subplots(figsize=(7.0, 4.0))
    ax.bar(labels, values)
    ax.set_ylabel("RMSE (dB)")
    ax.tick_params(axis="x", rotation=25)
    ax.grid(True, axis="y", linewidth=0.5, alpha=0.4)

    return save_figure(fig, "fig3_validation_rmse_summary")


def figure_grouped_cv(grouped: dict[str, Any], correction: dict[str, Any]) -> list[str]:
    best = correction["best_model_by_calibration_leave_one_out_rmse"]
    model_data = grouped["models"][best]

    wl_groups = model_data["leave_one_wavelength_out"]["groups"]
    span_groups = model_data["leave_one_span_out"]["groups"]

    labels = [f"λ {item['heldout_group']}" for item in wl_groups] + [
        f"S {item['heldout_group']}" for item in span_groups
    ]
    values = [item["rmse_db"] for item in wl_groups] + [item["rmse_db"] for item in span_groups]

    fig, ax = plt.subplots(figsize=(7.0, 4.0))
    ax.plot(labels, values, marker="o", linestyle="-")
    ax.set_ylabel("Grouped-CV RMSE (dB)")
    ax.tick_params(axis="x", rotation=25)
    ax.grid(True, linewidth=0.5, alpha=0.4)

    return save_figure(fig, "fig4_grouped_cv_rmse")


def figure_launch_power_sweep(launch_rows: pd.DataFrame, launch_summary: dict[str, Any]) -> list[str]:
    by_power = launch_summary["by_launch_power_dbm"]
    powers = sorted(float(power) for power in by_power.keys())
    rmse = [by_power[str(power)]["rmse_db"] if str(power) in by_power else by_power[f"{power:.1f}"]["rmse_db"] for power in powers]

    fig, ax = plt.subplots(figsize=(6.0, 4.0))
    ax.plot(powers, rmse, marker="o", linestyle="-")
    ax.set_xlabel("Requested launch power (dBm/channel)")
    ax.set_ylabel("RMSE versus GNPy (dB)")
    ax.grid(True, linewidth=0.5, alpha=0.4)

    return save_figure(fig, "fig5_cband_launch_power_sweep")


def figure_validation_readiness(readiness: dict[str, Any]) -> list[str]:
    rows_by_band = readiness.get("rows_by_band", {})
    labels = ["S", "C", "L"]
    values = [rows_by_band.get(label, 0) for label in labels]

    fig, ax = plt.subplots(figsize=(5.0, 4.0))
    ax.bar(labels, values)
    ax.set_xlabel("Band")
    ax.set_ylabel("External validation rows")
    ax.grid(True, axis="y", linewidth=0.5, alpha=0.4)

    return save_figure(fig, "fig6_validation_readiness_by_band")


def main() -> int:
    heldout_frame = pd.read_csv(require(GENERATED / "recursive_heldout_cband_row_comparison.csv"))
    launch_rows = pd.read_csv(require(GENERATED / "cband_launch_power_sweep_model_comparison.csv"))

    correction = load_json(GENERATED / "recursive_cband_correction_summary.json")
    grouped = load_json(GENERATED / "recursive_cband_grouped_cv_summary.json")
    launch_summary = load_json(GENERATED / "cband_launch_power_sweep_summary.json")
    readiness = load_json(GENERATED / "scl_external_validation_readiness.json")

    best = correction["best_model_by_calibration_leave_one_out_rmse"]

    generated_files: list[str] = []
    generated_files += figure_recursive_vs_analytical(heldout_frame)
    generated_files += figure_gnpy_vs_recursive(heldout_frame)
    generated_files += figure_raw_corrected_rmse(correction, grouped, launch_summary)
    generated_files += figure_grouped_cv(grouped, correction)
    generated_files += figure_launch_power_sweep(launch_rows, launch_summary)
    generated_files += figure_validation_readiness(readiness)

    validation_table = pd.DataFrame(
        [
            metric_row(
                "Recursive raw held-out C-band",
                correction["model_summaries"]["none"]["heldout_raw"],
            ),
            metric_row(
                f"Post-model corrected held-out C-band ({best})",
                correction["model_summaries"][best]["heldout_corrected"],
            ),
            metric_row(
                f"Leave-one-wavelength-out grouped CV ({best})",
                grouped["models"][best]["leave_one_wavelength_out"]["overall"],
            ),
            metric_row(
                f"Leave-one-span-out grouped CV ({best})",
                grouped["models"][best]["leave_one_span_out"]["overall"],
            ),
            metric_row(
                "C-band launch-power sweep",
                launch_summary["overall"],
            ),
        ]
    )

    launch_table_rows = []
    for power, metrics in sorted(
        launch_summary["by_launch_power_dbm"].items(),
        key=lambda item: float(item[0]),
    ):
        row = metric_row(f"{float(power):+.1f} dBm/channel", metrics)
        launch_table_rows.append(row)

    launch_table = pd.DataFrame(launch_table_rows)

    readiness_table = pd.DataFrame(
        [
            {
                "Item": "Ready for full S+C+L claim",
                "Value": str(readiness.get("ready_for_scl_claim", False)),
            },
            {
                "Item": "Bands present",
                "Value": ", ".join(readiness.get("bands_present", [])),
            },
            {
                "Item": "S rows",
                "Value": readiness.get("rows_by_band", {}).get("S", 0),
            },
            {
                "Item": "C rows",
                "Value": readiness.get("rows_by_band", {}).get("C", 0),
            },
            {
                "Item": "L rows",
                "Value": readiness.get("rows_by_band", {}).get("L", 0),
            },
            {
                "Item": "Claim policy",
                "Value": readiness.get("claim_policy", ""),
            },
        ]
    )

    generated_files += write_table(validation_table, "table1_validation_summary")
    generated_files += write_table(launch_table, "table2_launch_power_sweep_summary")
    generated_files += write_table(readiness_table, "table3_validation_readiness")

    summary = {
        "note": "JOC paper evidence generator. Generated figures contain no internal titles; captions should be written in the manuscript.",
        "best_correction_model": best,
        "figure_directory": str(FIGURES.relative_to(ROOT)),
        "table_directory": str(TABLES.relative_to(ROOT)),
        "generated_files": generated_files,
        "headline_numbers": {
            "recursive_raw_heldout_rmse_db": correction["model_summaries"]["none"]["heldout_raw"]["rmse_db"],
            "recursive_corrected_heldout_rmse_db": correction["model_summaries"][best]["heldout_corrected"]["rmse_db"],
            "leave_one_wavelength_out_rmse_db": grouped["models"][best]["leave_one_wavelength_out"]["overall"]["rmse_db"],
            "leave_one_span_out_rmse_db": grouped["models"][best]["leave_one_span_out"]["overall"]["rmse_db"],
            "cband_launch_power_sweep_rmse_db": launch_summary["overall"]["rmse_db"],
            "ready_for_scl_claim": readiness.get("ready_for_scl_claim", False),
        },
        "claim_policy": "Use as JOC C-band cross-tool validation evidence only. Do not claim full S+C+L external validation.",
    }

    SUMMARY_PATH.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    generated_files.append(str(SUMMARY_PATH.relative_to(ROOT)))

    print(json.dumps(summary, indent=2))
    print()
    print("Generated JOC evidence files:")
    for file in generated_files:
        print(f"- {file}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())