from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from xgboost import XGBRegressor

from rogii_geo.models.artifact_loader import load_artifact_bundle
from rogii_geo.models.config import EnsembleConfig, models_required_by_config
from rogii_geo.training.artifacts import (
    export_artifact_bundle,
    write_current_pointer,
)
from rogii_geo.checksums import sha256_file, verify_checksums
from rogii_geo.training.config import TrainingConfig
from rogii_geo.training.dataset import MaskedDatasets
from rogii_geo.training.trainer import TrainedModels


def _tiny_trained(tmp_path: Path) -> tuple[TrainedModels, MaskedDatasets, TrainingConfig]:
    feature_columns = ["MD", "GR", "last_known_tvt", "linear_tvt_projection"]
    train_df = pd.DataFrame(
        {
            "MD": [1.0, 2.0, 3.0, 4.0],
            "GR": [10.0, 11.0, np.nan, 13.0],
            "last_known_tvt": [100.0, 100.0, 100.0, 100.0],
            "linear_tvt_projection": [100.0, 101.0, 102.0, 103.0],
            "actual_tvt": [100.5, 101.2, 102.1, 103.4],
            "residual_target": [0.5, 0.2, 0.1, 0.4],
            "well_id": ["a", "a", "b", "b"],
        }
    )
    val_df = train_df.copy()
    medians = pd.Series({"MD": 2.5, "GR": 11.0, "last_known_tvt": 100.0, "linear_tvt_projection": 101.5})

    model = XGBRegressor(
        n_estimators=3,
        max_depth=2,
        learning_rate=0.5,
        objective="reg:squarederror",
        tree_method="hist",
        verbosity=0,
        random_state=42,
    )
    X = train_df[feature_columns].fillna(medians).to_numpy(dtype=np.float32)
    y = train_df["residual_target"].to_numpy(dtype=np.float32)
    model.fit(X, y)

    config = TrainingConfig()
    config.xgb_params = {
        "n_estimators": 3,
        "max_depth": 2,
        "learning_rate": 0.5,
        "objective": "reg:squarederror",
        "tree_method": "hist",
        "verbosity": 0,
        "random_state": 42,
    }

    trained = TrainedModels(
        feature_columns=feature_columns,
        medians=medians,
        missing_median_features=[],
        xgb_model=model,
        et_model=None,
        validation_comparison=pd.DataFrame(
            [{"model": config.selected_model, "rmse": 1.0, "mae": 0.5, "n_rows": 4, "n_wells": 2}]
        ),
        per_well_metrics=pd.DataFrame(
            [{"well_id": "a", "model": config.selected_model, "rmse": 1.0, "mae": 0.5, "n_rows": 2}]
        ),
        fit_rows=4,
        train_rows=4,
        val_rows=4,
        train_wells=2,
        val_wells=2,
        selected_model_metrics={
            "model": config.selected_model,
            "rmse": 1.0,
            "mae": 0.5,
            "n_rows": 4,
            "n_wells": 2,
        },
        include_extra_trees=False,
    )
    datasets = MaskedDatasets(
        train_df=train_df,
        val_df=val_df,
        feature_columns=feature_columns,
        train_well_ids=["a", "b"],
        val_well_ids=["a", "b"],
        mask_summary=pd.DataFrame([{"well_id": "a", "mask_name": "natural", "hidden_rows": 2}]),
        dataset_summary=pd.DataFrame([{"split": "train", "n_wells": 2, "n_rows": 4}]),
    )
    return trained, datasets, config


def test_feature_order_and_median_serialization(tmp_path: Path):
    trained, datasets, config = _tiny_trained(tmp_path)
    artifact_dir = tmp_path / "v_test"
    artifact_dir.mkdir()
    export_artifact_bundle(
        artifact_dir,
        model_version="v_test",
        trained=trained,
        datasets=datasets,
        config=config,
        project_root=tmp_path,
    )
    cols = json.loads((artifact_dir / "feature_columns.json").read_text(encoding="utf-8"))
    assert cols == trained.feature_columns
    medians = json.loads((artifact_dir / "feature_medians.json").read_text(encoding="utf-8"))
    assert list(medians.keys()) == trained.feature_columns
    assert all(np.isfinite(list(medians.values())))


def test_ensemble_config_required_optional_predictors(tmp_path: Path):
    trained, datasets, config = _tiny_trained(tmp_path)
    artifact_dir = tmp_path / "v_test"
    artifact_dir.mkdir()
    export_artifact_bundle(
        artifact_dir,
        model_version="v_test",
        trained=trained,
        datasets=datasets,
        config=config,
        project_root=tmp_path,
    )
    ensemble = json.loads((artifact_dir / "ensemble_config.json").read_text(encoding="utf-8"))
    assert ensemble["selected_model"] == "blend_lastknown_0.70_ensemble"
    assert ensemble["weight_extra_trees"] == 0.0
    assert "xgboost_residual" in ensemble["required_predictors"]
    assert "extra_trees_residual" in ensemble["optional_predictors"]
    assert not (artifact_dir / "extra_trees_residual.joblib").exists()

    cfg = EnsembleConfig(
        selected_model=ensemble["selected_model"],
        alpha_last_known=ensemble["alpha_last_known"],
        weight_extra_trees=ensemble["weight_extra_trees"],
        weight_xgboost=ensemble["weight_xgboost"],
    )
    required = models_required_by_config(cfg)
    assert required["xgboost"] is True
    assert required["extra_trees"] is False


def test_checksum_verification_and_corruption(tmp_path: Path):
    trained, datasets, config = _tiny_trained(tmp_path)
    artifact_dir = tmp_path / "v_test"
    artifact_dir.mkdir()
    manifest = export_artifact_bundle(
        artifact_dir,
        model_version="v_test",
        trained=trained,
        datasets=datasets,
        config=config,
        project_root=tmp_path,
    )
    verify_checksums(artifact_dir, manifest)

    target = artifact_dir / "feature_columns.json"
    target.write_text(target.read_text(encoding="utf-8") + " ", encoding="utf-8")
    with pytest.raises(ValueError, match="Checksum mismatch"):
        verify_checksums(artifact_dir, manifest)


def test_missing_required_artifact_rejected(tmp_path: Path):
    trained, datasets, config = _tiny_trained(tmp_path)
    artifact_dir = tmp_path / "v_test"
    artifact_dir.mkdir()
    export_artifact_bundle(
        artifact_dir,
        model_version="v_test",
        trained=trained,
        datasets=datasets,
        config=config,
        project_root=tmp_path,
    )
    (artifact_dir / "xgboost_residual.json").unlink()
    with pytest.raises(FileNotFoundError):
        load_artifact_bundle(artifact_dir, verify=False)


def test_current_pointer_written_only_via_helper(tmp_path: Path):
    pointer = write_current_pointer(tmp_path / "artifacts", "v_test")
    payload = json.loads(pointer.read_text(encoding="utf-8"))
    assert payload["model_version"] == "v_test"
    assert sha256_file(pointer)
