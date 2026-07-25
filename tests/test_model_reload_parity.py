from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from xgboost import XGBRegressor

from rogii_geo.inference import (
    build_competition_output,
    build_full_well_output,
    build_inference_features,
    build_prediction_frame,
)
from rogii_geo.models.artifact_loader import load_artifact_bundle
from rogii_geo.training.artifacts import export_artifact_bundle
from rogii_geo.training.config import TrainingConfig
from rogii_geo.training.dataset import MaskedDatasets
from rogii_geo.training.pipeline import run_parity_check
from rogii_geo.training.trainer import TrainedModels, predict_absolute_tvt
from tests.fixtures import make_trailing_mask_well


def _export_tiny_bundle(tmp_path: Path):
    feature_columns = ["MD", "GR", "last_known_tvt", "linear_tvt_projection"]
    train_df = pd.DataFrame(
        {
            "MD": np.arange(20, dtype=float),
            "GR": 40.0 + np.arange(20),
            "last_known_tvt": np.full(20, 1000.0),
            "linear_tvt_projection": 1000.0 + 0.5 * np.arange(20),
            "actual_tvt": 1000.0 + 0.4 * np.arange(20),
            "residual_target": -0.1 * np.arange(20),
            "well_id": ["w"] * 20,
        }
    )
    medians = train_df[feature_columns].median()
    model = XGBRegressor(
        n_estimators=5,
        max_depth=2,
        learning_rate=0.3,
        objective="reg:squarederror",
        tree_method="hist",
        verbosity=0,
        random_state=0,
    )
    X = train_df[feature_columns].to_numpy(dtype=np.float32)
    y = train_df["residual_target"].to_numpy(dtype=np.float32)
    model.fit(X, y)

    config = TrainingConfig()
    config.xgb_params = {
        "n_estimators": 5,
        "max_depth": 2,
        "learning_rate": 0.3,
        "objective": "reg:squarederror",
        "tree_method": "hist",
        "verbosity": 0,
        "random_state": 0,
    }
    trained = TrainedModels(
        feature_columns=feature_columns,
        medians=medians,
        missing_median_features=[],
        xgb_model=model,
        et_model=None,
        validation_comparison=pd.DataFrame(
            [{"model": config.selected_model, "rmse": 0.1, "mae": 0.1, "n_rows": 20, "n_wells": 1}]
        ),
        per_well_metrics=pd.DataFrame(
            [{"well_id": "w", "model": config.selected_model, "rmse": 0.1, "mae": 0.1, "n_rows": 20}]
        ),
        fit_rows=20,
        train_rows=20,
        val_rows=20,
        train_wells=1,
        val_wells=1,
        selected_model_metrics={
            "model": config.selected_model,
            "rmse": 0.1,
            "mae": 0.1,
            "n_rows": 20,
            "n_wells": 1,
        },
        include_extra_trees=False,
    )
    datasets = MaskedDatasets(
        train_df=train_df,
        val_df=train_df.copy(),
        feature_columns=feature_columns,
        train_well_ids=["w"],
        val_well_ids=["w"],
        mask_summary=pd.DataFrame([{"well_id": "w", "mask_name": "natural", "hidden_rows": 20}]),
        dataset_summary=pd.DataFrame([{"split": "train", "n_wells": 1, "n_rows": 20}]),
    )
    artifact_dir = tmp_path / "v_parity"
    artifact_dir.mkdir()
    export_artifact_bundle(
        artifact_dir,
        model_version="v_parity",
        trained=trained,
        datasets=datasets,
        config=config,
        project_root=tmp_path,
    )
    return trained, datasets, config, artifact_dir


def test_xgboost_native_reload_parity(tmp_path: Path):
    trained, datasets, config, artifact_dir = _export_tiny_bundle(tmp_path)
    max_diff = run_parity_check(trained, datasets, config, artifact_dir, max_rows=20)
    assert max_diff <= 1e-6

    bundle = load_artifact_bundle(artifact_dir, verify=True)
    assert bundle.et_model is None
    assert bundle.xgb_model is not None
    assert bundle.feature_columns == trained.feature_columns

    in_memory = predict_absolute_tvt(
        datasets.val_df,
        trained.feature_columns,
        trained.medians,
        xgb_model=trained.xgb_model,
        et_model=None,
        alpha_last_known=config.alpha_last_known,
        weight_extra_trees=config.weight_extra_trees,
        weight_xgboost=config.weight_xgboost,
        selected_model=config.selected_model,
    )
    reloaded = bundle.predict_masked_frame(datasets.val_df)
    np.testing.assert_allclose(in_memory, reloaded, atol=1e-6)


def test_output_contracts_with_inference_helpers():
    well = make_trailing_mask_well(n_known=12, n_hidden=5)
    feat, known_mask = build_inference_features(well, "wellxyz")
    preds = np.full(int((~known_mask).sum()), 123.0)
    frame = build_prediction_frame(
        feat,
        known_mask,
        preds,
        model_name="blend_lastknown_0.70_ensemble",
    )
    competition = build_competition_output(frame)
    assert list(competition.columns) == ["id", "tvt"]

    full = build_full_well_output(
        feat,
        known_mask,
        preds,
        model_name="blend_lastknown_0.70_ensemble",
    )
    np.testing.assert_allclose(
        full.loc[known_mask, "predicted_tvt"],
        full.loc[known_mask, "TVT_input"],
    )
