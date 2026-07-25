from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from rogii_geo.constants import META_COLUMNS
from rogii_geo.training.config import TrainingConfig
from rogii_geo.training.dataset import resolve_feature_columns, split_wells, subsample_fit_rows
from rogii_geo.training.masking import (
    build_masked_rows_for_well,
    choose_cut,
    find_natural_cut,
    subsample_hidden,
)
from tests.fixtures import make_trailing_mask_well


def test_find_natural_cut_and_choose_cut_deterministic():
    df = make_trailing_mask_well(n_known=60, n_hidden=40)
    cut = find_natural_cut(df.sort_values("MD").reset_index(drop=True))
    assert cut == 60

    rng_a = np.random.default_rng(42)
    rng_b = np.random.default_rng(42)
    a = choose_cut(100, 60, [0.70, 0.75], rng_a)
    b = choose_cut(100, 60, [0.70, 0.75], rng_b)
    assert a == b
    assert a is not None
    assert a[0] == "natural"


def test_subsample_hidden_is_evenly_spaced_and_deterministic():
    frame = pd.DataFrame({"x": np.arange(1000)})
    a = subsample_hidden(frame, 10)
    b = subsample_hidden(frame, 10)
    assert len(a) == 10
    pd.testing.assert_frame_equal(a, b)
    assert list(a["x"]) == list(np.linspace(0, 999, 10).astype(int))


def test_masked_rows_residual_and_no_feature_leakage():
    well = make_trailing_mask_well(n_known=60, n_hidden=40, start_tvt=1000.0, slope=1.0)
    rng = np.random.default_rng(0)
    hidden, summary = build_masked_rows_for_well(
        well,
        "w1",
        [0.4],
        rng,
        min_known_rows=20,
        min_hidden_rows=10,
        max_hidden_rows_per_mask=25,
    )
    assert summary is not None
    assert not hidden.empty
    assert len(hidden) <= 25
    np.testing.assert_allclose(
        hidden["residual_target"],
        hidden["actual_tvt"] - hidden["linear_tvt_projection"],
    )
    features = resolve_feature_columns(hidden)
    forbidden = {
        "TVT",
        "TVT_input",
        "sim_TVT_input",
        "actual_tvt",
        "residual_target",
    }
    assert not (set(features) & forbidden)
    assert not (set(features) & META_COLUMNS)


def test_grouped_split_has_no_well_overlap():
    wells = [f"w{i}" for i in range(20)]
    train, val = split_wells(wells, test_size=0.2, random_state=42)
    assert set(train).isdisjoint(set(val))
    assert len(train) + len(val) == 20


def test_subsample_fit_rows_cap():
    df = pd.DataFrame({"a": np.arange(100)})
    out = subsample_fit_rows(df, max_rows=30, random_state=42)
    assert len(out) == 30
    out2 = subsample_fit_rows(df, max_rows=30, random_state=42)
    pd.testing.assert_frame_equal(out, out2)
