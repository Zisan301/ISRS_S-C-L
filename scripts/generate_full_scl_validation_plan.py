"""Generate the calibration and held-out validation matrix for full S+C+L studies."""
from __future__ import annotations

import argparse
from itertools import product
from pathlib import Path

import pandas as pd

CALIBRATION_WAVELENGTHS_NM: dict[str, tuple[float, ...]] = {
    "S": (1470.0, 1495.0, 1520.0),
    "C": (1535.0, 1550.0, 1560.0),
    "L": (1570.0, 1595.0, 1615.0),
}

HELDOUT_WAVELENGTHS_NM: dict[str, tuple[float, ...]] = {
    "S": (1480.0, 1505.0, 1525.0),
    "C": (1540.0, 1545.0, 1555.0),
    "L": (1580.0, 1605.0, 1620.0),
}

SPAN_COUNTS: tuple[int, ...] = (1, 4, 8)


def build_validation_plan() -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    split_map = {
        "calibration": CALIBRATION_WAVELENGTHS_NM,
        "heldout": HELDOUT_WAVELENGTHS_NM,
    }
    for split, wavelengths_by_band in split_map.items():
        for band, wavelengths in wavelengths_by_band.items():
            for wavelength_nm, spans in product(wavelengths, SPAN_COUNTS):
                rows.append(
                    {
                        "split": split,
                        "band": band,
                        "requested_wavelength_nm": wavelength_nm,
                        "spans": spans,
                        "strategy": "flat",
                        "metric": "gsnr_db",
                        "source_type": "GNPy",
                        "status": "pending",
                    }
                )

    frame = pd.DataFrame(rows).sort_values(
        ["split", "band", "spans", "requested_wavelength_nm"],
        ignore_index=True,
    )
    identity = ["split", "band", "requested_wavelength_nm", "spans", "strategy", "metric"]
    if frame.duplicated(identity).any():
        raise RuntimeError("Validation plan contains duplicate identities")

    calibration = frame[frame["split"] == "calibration"]
    heldout = frame[frame["split"] == "heldout"]
    overlap = calibration.merge(
        heldout,
        on=["band", "requested_wavelength_nm", "spans", "strategy", "metric"],
        how="inner",
    )
    if not overlap.empty:
        raise RuntimeError("Calibration and held-out identities overlap")

    expected_rows = 3 * 2 * 3 * 3
    if len(frame) != expected_rows:
        raise RuntimeError(f"Expected {expected_rows} validation rows, found {len(frame)}")
    return frame


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("validation_data/full_scl_validation_plan.csv"),
        help="CSV path for the generated validation matrix.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    frame = build_validation_plan()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(args.output, index=False)
    print(f"Wrote {len(frame)} rows to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
