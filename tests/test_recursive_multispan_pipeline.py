from pathlib import Path

import numpy as np
import yaml

from isrs_scl.experiments import _strategy_sweeps
from isrs_scl.link import LinkModel
from isrs_scl.system.grid import build_grid
from isrs_scl.system.parameters import apply_defaults, validate_config


def _small_cfg():
    raw = yaml.safe_load(Path("config_q2_final.yaml").read_text(encoding="utf-8"))
    cfg = apply_defaults(raw)
    cfg["grid"]["mode"] = "paper_240_subset"
    cfg["grid"]["subset_channels"] = 17
    cfg["raman"]["integration_step_m"] = 1600.0
    cfg["raman"]["save_step_m"] = 1600.0
    cfg["fiber"]["max_spans"] = 2
    cfg["optimization"]["target_spans"] = 2
    cfg["optimization"]["evaluation_spans"] = [1, 2]
    validate_config(cfg)
    return cfg


def test_recursive_link_evaluation_returns_finite_metrics():
    cfg = _small_cfg()
    grid = build_grid(cfg["grid"])
    link = LinkModel(grid, cfg)

    launch = link.flat_launch_w(0.0)
    result = link.evaluate_recursive(launch, 2)

    assert result.metric_basis == "recursive_physical_gsnr_awgn"
    assert result.gsnr_db.shape == launch.shape
    assert np.all(np.isfinite(result.gsnr_db))
    assert np.all(result.total_noise_w > 0.0)


def test_strategy_sweeps_use_recursive_metric_basis():
    cfg = _small_cfg()
    grid = build_grid(cfg["grid"])
    link = LinkModel(grid, cfg)

    profiles = {
        "flat": np.full(grid.n_channels, float(cfg["launch"]["flat_power_dbm_per_channel"]))
    }

    channel_table, strategy_summary, band_table = _strategy_sweeps(link, profiles, cfg)

    assert not channel_table.empty
    assert not strategy_summary.empty
    assert not band_table.empty
    assert set(strategy_summary["metric_basis"]) == {"recursive_physical_gsnr_awgn"}
