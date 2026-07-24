from __future__ import annotations

from scripts.generate_full_scl_validation_plan import build_validation_plan


def test_full_scl_validation_plan_is_complete_and_leakage_free() -> None:
    frame = build_validation_plan()

    assert len(frame) == 54
    assert set(frame["band"]) == {"S", "C", "L"}
    assert set(frame["split"]) == {"calibration", "heldout"}
    assert set(frame["spans"]) == {1, 4, 8}

    for band in ("S", "C", "L"):
        band_rows = frame[frame["band"] == band]
        calibration = set(
            band_rows.loc[band_rows["split"] == "calibration", "requested_wavelength_nm"]
        )
        heldout = set(
            band_rows.loc[band_rows["split"] == "heldout", "requested_wavelength_nm"]
        )
        assert len(calibration) == 3
        assert len(heldout) == 3
        assert calibration.isdisjoint(heldout)


def test_each_validation_identity_has_all_span_counts() -> None:
    frame = build_validation_plan()
    grouped = frame.groupby(["split", "band", "requested_wavelength_nm"])["spans"].apply(set)
    assert all(spans == {1, 4, 8} for spans in grouped)
