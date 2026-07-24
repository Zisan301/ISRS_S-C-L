"""Summarize full S/C/L grid and result coverage for S- and L-band studies.

This utility is intentionally lightweight: it verifies the configured optical
band coverage before a heavy simulation run and can also summarize generated
channel_performance.csv and band_summary.csv outputs after the run.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd

from isrs_scl.system.grid import build_grid
from isrs_scl.system.parameters import load_config


def _band_table(frame: pd.DataFrame) -> pd.DataFrame:
    grouped = (
        frame.groupby("band", sort=False)
        .agg(
            channels=("channel", "count"),
            lambda_min_nm=("wavelength_nm", "min"),
            lambda_max_nm=("wavelength_nm", "max"),
            frequency_min_thz=("frequency_thz", "min"),
            frequency_max_thz=("frequency_thz", "max"),
        )
        .reset_index()
    )
    return grouped


def summarize_config(config_path: Path) -> tuple[dict[str, Any], pd.DataFrame]:
    cfg = load_config(config_path)
    grid = build_grid(cfg["grid"])
    grid_frame = grid.to_frame()
    bands = _band_table(grid_frame)
    summary = {
        "config": str(config_path),
        "grid_mode": cfg["grid"]["mode"],
        "channels_total": int(grid.n_channels),
        "bandwidth_thz": float(grid.bandwidth_hz / 1e12),
        "s_band_channels": int((grid_frame["band"] == "S").sum()),
        "c_band_channels": int((grid_frame["band"] == "C").sum()),
        "l_band_channels": int((grid_frame["band"] == "L").sum()),
        "wavelength_min_nm": float(grid_frame["wavelength_nm"].min()),
        "wavelength_max_nm": float(grid_frame["wavelength_nm"].max()),
    }
    return summary, bands


def summarize_results(results_dir: Path) -> dict[str, Any]:
    output: dict[str, Any] = {"results_dir": str(results_dir)}
    channel_path = results_dir / "channel_performance.csv"
    band_path = results_dir / "band_summary.csv"
    if channel_path.exists():
        channel = pd.read_csv(channel_path)
        output["channel_performance_rows"] = int(len(channel))
        if {"band", "strategy", "spans", "gsnr_db", "ngmi"}.issubset(channel.columns):
            adaptive = channel[channel["strategy"].astype(str).str.lower() == "adaptive"].copy()
            if not adaptive.empty:
                by_band = adaptive.groupby("band", sort=False).agg(
                    rows=("band", "count"),
                    min_gsnr_db=("gsnr_db", "min"),
                    mean_gsnr_db=("gsnr_db", "mean"),
                    min_ngmi=("ngmi", "min"),
                    mean_ngmi=("ngmi", "mean"),
                )
                output["adaptive_by_band"] = by_band.reset_index().to_dict(orient="records")
    if band_path.exists():
        band_summary = pd.read_csv(band_path)
        output["band_summary_rows"] = int(len(band_summary))
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="config_q2_final.yaml", type=Path)
    parser.add_argument("--results-dir", type=Path, help="Optional completed run results directory")
    parser.add_argument("--output-json", type=Path, help="Optional path for machine-readable summary")
    parser.add_argument("--band-csv", type=Path, help="Optional path for per-band grid coverage CSV")
    args = parser.parse_args()

    summary, bands = summarize_config(args.config)
    if args.results_dir is not None:
        summary["results"] = summarize_results(args.results_dir)

    print(json.dumps(summary, indent=2, sort_keys=True))
    print("\nPer-band grid coverage:")
    print(bands.to_string(index=False))

    if args.output_json is not None:
        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        args.output_json.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    if args.band_csv is not None:
        args.band_csv.parent.mkdir(parents=True, exist_ok=True)
        bands.to_csv(args.band_csv, index=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
