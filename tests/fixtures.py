"""Synthetic well fixtures for unit tests."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from xgboost import XGBRegressor

from rogii_geo.training.artifacts import export_artifact_bundle, write_current_pointer
from rogii_geo.training.config import TrainingConfig
from rogii_geo.training.dataset import MaskedDatasets
from rogii_geo.training.trainer import TrainedModels

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


def make_trailing_mask_well(
    n_known: int = 20,
    n_hidden: int = 10,
    *,
    well_id: str = "testwell",
    start_md: float = 10000.0,
    start_tvt: float = 11000.0,
    slope: float = 0.5,
) -> pd.DataFrame:
    """Build a clean known-prefix / trailing-missing horizontal well."""

    n = n_known + n_hidden
    md = start_md + np.arange(n, dtype=float)
    tvt = start_tvt + slope * np.arange(n, dtype=float)
    tvt_input = tvt.copy()
    tvt_input[n_known:] = np.nan

    return pd.DataFrame(
        {
            "MD": md,
            "X": 1000.0 + np.arange(n, dtype=float),
            "Y": 2000.0 + 0.5 * np.arange(n, dtype=float),
            "Z": -9000.0 - 0.2 * np.arange(n, dtype=float),
            "GR": 50.0 + np.sin(np.arange(n) / 3.0),
            "TVT": tvt,
            "TVT_input": tvt_input,
            "ANCC": -9300.0,
            "ASTNU": -9500.0,
            "ASTNL": -9550.0,
            "EGFDU": -9600.0,
            "EGFDL": -9650.0,
            "BUDA": -9800.0,
        }
    )


def make_dirty_boundary_well() -> pd.DataFrame:
    """Known → missing → known again (invalid competition boundary)."""

    df = make_trailing_mask_well(n_known=10, n_hidden=10)
    df.loc[15, "TVT_input"] = df.loc[15, "TVT"]
    return df


def export_tiny_artifact_bundle(tmp_path: Path, *, version: str = "v_test") -> Path:
    """Create a minimal checksummed artifact bundle for isolated CLI/service tests."""

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
    artifact_root = tmp_path / "artifacts"
    artifact_dir = artifact_root / version
    artifact_dir.mkdir(parents=True)
    export_artifact_bundle(
        artifact_dir,
        model_version=version,
        trained=trained,
        datasets=datasets,
        config=config,
        project_root=tmp_path,
    )
    write_current_pointer(artifact_root, version)
    return artifact_root
