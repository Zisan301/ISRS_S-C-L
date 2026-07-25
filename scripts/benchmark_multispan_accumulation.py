"""Benchmark analytical multi-span scaling against recursive span-by-span propagation.

This is diagnostic evidence only. It does not make the project publication-ready.
It tests whether the current approximation

    ASE_N = N * ASE_1
    NLI_N = N^(1+epsilon) * NLI_1

is close to a recursive model that re-evaluates Raman, amplification, ASE and NLI
after every span.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from isrs_scl.fiber.amplification import reference_bandwidth_01nm_hz
from isrs_scl.link import LinkModel
from isrs_scl.system.grid import build_grid
from isrs_scl.system.parameters import apply_defaults, validate_config


def db(power_w: np.ndarray) -> np.ndarray:
    return 10.0 * np.log10(np.maximum(power_w, 1e-30))


def dbm(power_w: np.ndarray | float) -> np.ndarray:
    return 10.0 * np.log10(np.maximum(np.asarray(power_w, dtype=float), 1e-30) / 1e-3)


def load_config(path: Path, grid_mode: str) -> dict[str, Any]:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("Config YAML root must be a mapping")
    cfg = apply_defaults(raw)
    cfg["grid"]["mode"] = grid_mode
    validate_config(cfg, base_dir=path.parent)
    return cfg


def recursive_accumulation(
    model: LinkModel,
    launch_power_w: np.ndarray,
    n_spans: int,
    nli_model: str | None,
) -> tuple[np.ndarray, pd.DataFrame]:
    if n_spans < 1:
        raise ValueError("n_spans must be positive")

    signal = np.asarray(launch_power_w, dtype=float).copy()
    ase_psd = np.zeros_like(signal)
    nli_power = np.zeros_like(signal)

    receiver_bw = None
    span_rows: list[dict[str, float | int]] = []

    for span_index in range(n_spans):
        span = model.span_model.evaluate(signal, nli_model)
        amp = span.amplifier

        optical_bw = float(
            getattr(amp, "optical_noise_bandwidth_hz", model.span_model.amplifier.noise_bandwidth_hz)
        )
        receiver_bw = float(getattr(amp, "receiver_equivalent_noise_bandwidth_hz", optical_bw))

        ase_psd += span.total_ase_psd_w_per_hz
        nli_power += span.nli.nli_power_w_per_span

        output_signal = np.asarray(amp.output_signal_w, dtype=float)

        span_rows.append(
            {
                "span": span_index + 1,
                "mean_input_power_dbm": float(dbm(np.mean(signal))),
                "mean_output_power_dbm": float(dbm(np.mean(output_signal))),
                "max_abs_amp_residual_db": float(np.max(np.abs(amp.residual_db))),
                "mean_accumulated_ase_receiver_w": float(np.mean(ase_psd * receiver_bw)),
                "mean_accumulated_nli_w": float(np.mean(nli_power)),
            }
        )

        signal = output_signal.copy()

    if receiver_bw is None:
        raise RuntimeError("Recursive loop did not execute")

    trx_snr = 10.0 ** (float(model.cfg["nli"]["transceiver_snr_db"]) / 10.0)
    trx_noise = signal / trx_snr
    ase_receiver = ase_psd * float(receiver_bw)
    total_noise = ase_receiver + nli_power + trx_noise

    if np.any(total_noise <= 0) or not np.isfinite(total_noise).all():
        raise FloatingPointError("Recursive accumulation produced invalid total noise")

    recursive_gsnr_db = 10.0 * np.log10(np.maximum(signal, 1e-30) / total_noise)

    return recursive_gsnr_db, pd.DataFrame(span_rows)


def summarize_delta(frame: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []

    group_cols = ["launch_power_dbm", "n_spans", "band"]
    for keys, group in frame.groupby(group_cols, sort=True):
        launch_power_dbm, n_spans, band = keys
        delta = group["delta_recursive_minus_analytical_db"].to_numpy(dtype=float)
        rows.append(
            {
                "launch_power_dbm": float(launch_power_dbm),
                "n_spans": int(n_spans),
                "band": str(band),
                "channels": int(delta.size),
                "mean_delta_db": float(np.mean(delta)),
                "mean_abs_delta_db": float(np.mean(np.abs(delta))),
                "rmse_delta_db": float(np.sqrt(np.mean(delta**2))),
                "p95_abs_delta_db": float(np.quantile(np.abs(delta), 0.95)),
                "max_abs_delta_db": float(np.max(np.abs(delta))),
            }
        )

    for keys, group in frame.groupby(["launch_power_dbm", "n_spans"], sort=True):
        launch_power_dbm, n_spans = keys
        delta = group["delta_recursive_minus_analytical_db"].to_numpy(dtype=float)
        rows.append(
            {
                "launch_power_dbm": float(launch_power_dbm),
                "n_spans": int(n_spans),
                "band": "ALL",
                "channels": int(delta.size),
                "mean_delta_db": float(np.mean(delta)),
                "mean_abs_delta_db": float(np.mean(np.abs(delta))),
                "rmse_delta_db": float(np.sqrt(np.mean(delta**2))),
                "p95_abs_delta_db": float(np.quantile(np.abs(delta), 0.95)),
                "max_abs_delta_db": float(np.max(np.abs(delta))),
            }
        )

    return pd.DataFrame(rows)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config_q2_final.yaml")
    parser.add_argument("--grid-mode", default="paper_240_subset", choices=["paper_240_subset", "full_scl"])
    parser.add_argument("--spans", nargs="+", type=int, default=[1, 4, 8, 10])
    parser.add_argument("--launch-powers-dbm", nargs="+", type=float, default=[-2.0, 0.0, 2.0])
    parser.add_argument("--nli-model", default=None)
    parser.add_argument("--threshold-db", type=float, default=0.25)
    parser.add_argument("--output-dir", default="releases/pnc-v1.0/results")
    args = parser.parse_args()

    cfg_path = Path(args.config)
    cfg = load_config(cfg_path, args.grid_mode)
    grid = build_grid(cfg["grid"])
    model = LinkModel(grid, cfg)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    channel_frames: list[pd.DataFrame] = []
    span_record_frames: list[pd.DataFrame] = []

    for launch_power_dbm in args.launch_powers_dbm:
        launch = model.flat_launch_w(launch_power_dbm)

        for n_spans in args.spans:
            analytical = model.evaluate(launch, n_spans, args.nli_model)
            recursive_gsnr_db, span_records = recursive_accumulation(
                model, launch, n_spans, args.nli_model
            )

            delta = recursive_gsnr_db - analytical.gsnr_db

            channel_frames.append(
                pd.DataFrame(
                    {
                        "launch_power_dbm": float(launch_power_dbm),
                        "n_spans": int(n_spans),
                        "channel": np.arange(grid.n_channels),
                        "band": grid.bands,
                        "wavelength_nm": grid.wavelengths_nm,
                        "analytical_gsnr_db": analytical.gsnr_db,
                        "recursive_gsnr_db": recursive_gsnr_db,
                        "delta_recursive_minus_analytical_db": delta,
                    }
                )
            )

            span_records.insert(0, "launch_power_dbm", float(launch_power_dbm))
            span_records.insert(1, "n_spans_target", int(n_spans))
            span_record_frames.append(span_records)

    channel_delta = pd.concat(channel_frames, ignore_index=True)
    summary = summarize_delta(channel_delta)
    span_records_all = pd.concat(span_record_frames, ignore_index=True)

    channel_path = output_dir / "multispan_accumulation_channel_deltas.csv"
    summary_path = output_dir / "multispan_accumulation_summary.csv"
    records_path = output_dir / "multispan_accumulation_span_records.csv"
    json_path = output_dir / "multispan_accumulation_benchmark.json"

    channel_delta.to_csv(channel_path, index=False)
    summary.to_csv(summary_path, index=False)
    span_records_all.to_csv(records_path, index=False)

    max_abs_delta = float(summary["max_abs_delta_db"].max())
    benchmark = {
        "config": str(cfg_path),
        "grid_mode": args.grid_mode,
        "n_channels": int(grid.n_channels),
        "spans": [int(x) for x in args.spans],
        "launch_powers_dbm": [float(x) for x in args.launch_powers_dbm],
        "nli_model": args.nli_model or str(cfg["nli"]["primary_model"]),
        "threshold_db": float(args.threshold_db),
        "max_abs_delta_db": max_abs_delta,
        "within_threshold": bool(max_abs_delta <= float(args.threshold_db)),
        "outputs": {
            "channel_deltas_csv": str(channel_path),
            "summary_csv": str(summary_path),
            "span_records_csv": str(records_path),
        },
        "interpretation": (
            "If within_threshold is true, analytical multi-span scaling may be defensible "
            "for this tested grid/power/span matrix. If false, recursive propagation should "
            "be used or the approximation limits must be reported."
        ),
    }

    json_path.write_text(json.dumps(benchmark, indent=2), encoding="utf-8")

    print(json.dumps(benchmark, indent=2))
    print()
    print("Summary by band:")
    print(summary.to_string(index=False))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
