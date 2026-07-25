from __future__ import annotations

import numpy as np
import pytest

from rogii_geo.inference import (
    build_competition_output,
    build_full_well_output,
    build_inference_features,
    build_prediction_frame,
)
from rogii_geo.models import (
    ProductionRecipe,
    apply_residual_model,
    blend_last_known_with_ensemble,
    models_required_by_config,
    parse_blend_alpha,
    resolve_final_predictions,
    weighted_ensemble,
)
from tests.fixtures import make_trailing_mask_well


def test_production_recipe_requires_xgboost_only():
    recipe = ProductionRecipe.from_metadata()
    required = models_required_by_config(recipe.config)
    assert required["xgboost"] is True
    assert required["extra_trees"] is False
    assert recipe.config.selected_model == "blend_lastknown_0.70_ensemble"
    assert recipe.config.alpha_last_known == pytest.approx(0.70)
    assert recipe.config.weight_extra_trees == pytest.approx(0.0)
    assert recipe.config.weight_xgboost == pytest.approx(1.0)


def test_parse_blend_alpha():
    assert parse_blend_alpha("blend_lastknown_0.70_ensemble") == pytest.approx(0.70)
    assert parse_blend_alpha("blend_lastknown_0.85_ensemble") == pytest.approx(0.85)


def test_weighted_ensemble_skips_zero_weight_component():
    xgb = np.array([10.0, 20.0])
    out = weighted_ensemble(None, xgb, weight_extra_trees=0.0, weight_xgboost=1.0)
    np.testing.assert_allclose(out, xgb)

    with pytest.raises(RuntimeError, match="Extra Trees"):
        weighted_ensemble(None, xgb, weight_extra_trees=0.2, weight_xgboost=0.8)


def test_blend_formula_matches_selected_recipe():
    last_known = np.array([100.0, 100.0])
    ensemble = np.array([110.0, 130.0])
    blended = blend_last_known_with_ensemble(last_known, ensemble, 0.70)
    expected = 0.70 * last_known + 0.30 * ensemble
    np.testing.assert_allclose(blended, expected)


def test_apply_residual_model():
    proj = np.array([100.0, 200.0])
    resid = np.array([1.5, -2.0])
    np.testing.assert_allclose(apply_residual_model(proj, resid), [101.5, 198.0])


def test_resolve_final_predictions_blend_with_xgb_only_ensemble():
    import pandas as pd

    df = pd.DataFrame(
        {
            "pred_last_known": [100.0, 100.0],
            "pred_xgboost": [110.0, 130.0],
        }
    )
    preds = resolve_final_predictions(
        df,
        "blend_lastknown_0.70_ensemble",
        weight_extra_trees=0.0,
        weight_xgboost=1.0,
    )
    expected = 0.70 * df["pred_last_known"] + 0.30 * df["pred_xgboost"]
    np.testing.assert_allclose(preds, expected.to_numpy())


def test_inference_outputs_competition_and_full_well():
    well = make_trailing_mask_well(n_known=8, n_hidden=4)
    feat, known_mask = build_inference_features(well, "abc123")
    n_hidden = int((~known_mask).sum())
    fake_preds = np.linspace(1.0, n_hidden, n_hidden)

    pred_frame = build_prediction_frame(
        feat,
        known_mask,
        fake_preds,
        model_name="blend_lastknown_0.70_ensemble",
    )
    competition = build_competition_output(pred_frame)
    assert list(competition.columns) == ["id", "tvt"]
    assert len(competition) == n_hidden
    assert competition["id"].iloc[0].startswith("abc123_")

    full = build_full_well_output(
        feat,
        known_mask,
        fake_preds,
        model_name="blend_lastknown_0.70_ensemble",
    )
    assert "predicted_tvt" in full.columns
    assert "prediction_source" in full.columns
    assert (full.loc[known_mask, "prediction_source"] == "known").all()
    assert (full.loc[~known_mask.to_numpy(), "prediction_source"] == "model").all()
    np.testing.assert_allclose(
        full.loc[known_mask, "predicted_tvt"],
        full.loc[known_mask, "TVT_input"],
    )
