from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from rogii_geo.features import (
    add_last_known_and_slope_features,
    engineer_horizontal_features,
    prepare_well_frame,
)
from rogii_geo.validation import (
    has_clean_prediction_boundary,
    identify_prediction_sections,
    validate_horizontal_well,
)
from tests.fixtures import make_dirty_boundary_well, make_trailing_mask_well


def test_engineer_horizontal_features_preserves_original_row_index_through_md_sort():
    df = make_trailing_mask_well(n_known=5, n_hidden=5)
    # Shuffle MD order so sort must restore original indices via column.
    df = df.sample(frac=1.0, random_state=0)
    feat = engineer_horizontal_features(df, "w1")
    assert "original_row_index" in feat.columns
    assert feat["MD"].is_monotonic_increasing
    # Round-trip: reconstructing by original index recovers values.
    assert set(feat["original_row_index"]) == set(df.index.astype(int))


def test_prepare_well_frame_attaches_tvt_input_and_formation():
    df = make_trailing_mask_well()
    feat = prepare_well_frame(df, "w1")
    assert "TVT_input" in feat.columns
    assert "BUDA" in feat.columns
    assert feat["TVT_input"].isna().sum() == 10


def test_add_last_known_uses_only_known_prefix():
    df = make_trailing_mask_well(n_known=20, n_hidden=10, start_tvt=1000.0, slope=1.0)
    feat = prepare_well_frame(df, "w1")
    known_mask = feat["TVT_input"].notna().to_numpy()
    out = add_last_known_and_slope_features(feat, known_mask, tvt_source_column="TVT_input")

    expected_last = float(feat.loc[known_mask, "TVT_input"].iloc[-1])
    assert out["last_known_tvt"].iloc[0] == pytest.approx(expected_last)
    # Hidden rows share the same last-known constant from the prefix.
    assert out.loc[~known_mask, "last_known_tvt"].nunique() == 1
    assert np.isfinite(out.loc[~known_mask, "linear_tvt_projection"]).all()


def test_clean_boundary_validation():
    clean = make_trailing_mask_well()
    dirty = make_dirty_boundary_well()
    assert has_clean_prediction_boundary(clean) is True
    assert has_clean_prediction_boundary(dirty) is False

    ok = validate_horizontal_well(clean, "clean")
    bad = validate_horizontal_well(dirty, "dirty")
    assert ok.ok
    assert ok.n_known == 20
    assert ok.n_prediction == 10
    assert not bad.ok
    assert any("clean trailing mask" in e for e in bad.errors)


def test_missing_required_columns_rejected():
    df = make_trailing_mask_well().drop(columns=["GR"])
    result = validate_horizontal_well(df, "bad")
    assert not result.ok
    assert any("Missing required columns" in e for e in result.errors)


def test_identify_prediction_sections():
    df = make_trailing_mask_well(n_known=3, n_hidden=2)
    known, pred = identify_prediction_sections(df)
    assert known.sum() == 3
    assert pred.sum() == 2
