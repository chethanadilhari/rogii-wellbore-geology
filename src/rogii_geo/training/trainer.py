"""Fit residual models and evaluate the frozen production recipe."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd
from sklearn.ensemble import ExtraTreesRegressor
from xgboost import XGBRegressor

from rogii_geo.models.impute import fit_median_imputer, transform_with_medians
from rogii_geo.models.predictors import (
    apply_residual_model,
    blend_last_known_with_ensemble,
    weighted_ensemble,
)
from rogii_geo.training.config import TrainingConfig
from rogii_geo.training.dataset import MaskedDatasets, subsample_fit_rows
from rogii_geo.training.evaluation import calculate_validation_metrics


@dataclass
class TrainedModels:
    feature_columns: list[str]
    medians: pd.Series
    missing_median_features: list[str]
    xgb_model: XGBRegressor | None
    et_model: ExtraTreesRegressor | None
    validation_comparison: pd.DataFrame
    per_well_metrics: pd.DataFrame
    fit_rows: int
    train_rows: int
    val_rows: int
    train_wells: int
    val_wells: int
    selected_model_metrics: dict[str, Any] = field(default_factory=dict)
    include_extra_trees: bool = False


def _serialize_medians(
    medians: pd.Series,
    feature_columns: list[str],
    fallback: float,
) -> tuple[pd.Series, list[str]]:
    values = {}
    missing = []
    for col in feature_columns:
        value = medians.get(col, np.nan)
        if value is None or not np.isfinite(float(value)):
            values[col] = float(fallback)
            missing.append(col)
        else:
            values[col] = float(value)
    return pd.Series(values), missing


def predict_absolute_tvt(
    frame: pd.DataFrame,
    feature_columns: list[str],
    medians: pd.Series,
    *,
    xgb_model: XGBRegressor | None,
    et_model: ExtraTreesRegressor | None,
    alpha_last_known: float,
    weight_extra_trees: float,
    weight_xgboost: float,
    selected_model: str,
) -> np.ndarray:
    """Apply the production blend (or requested residual candidate) to a masked frame."""

    last_known = frame["last_known_tvt"].to_numpy(dtype=float)
    linear = frame["linear_tvt_projection"].to_numpy(dtype=float)
    X = transform_with_medians(frame, feature_columns, medians)

    pred_xgb = None
    pred_et = None
    if xgb_model is not None:
        pred_xgb = apply_residual_model(linear, xgb_model.predict(X))
    if et_model is not None:
        pred_et = apply_residual_model(linear, et_model.predict(X))

    if selected_model == "last_known_tvt":
        return last_known
    if selected_model == "linear_projection":
        return linear
    if selected_model == "xgboost_residual":
        if pred_xgb is None:
            raise RuntimeError("XGBoost model required")
        return pred_xgb
    if selected_model == "extra_trees_residual":
        if pred_et is None:
            raise RuntimeError("Extra Trees model required")
        return pred_et

    ensemble = weighted_ensemble(
        pred_et,
        pred_xgb,
        weight_extra_trees,
        weight_xgboost,
    )
    if selected_model == "weighted_et_xgb_ensemble":
        return ensemble
    if selected_model.startswith("blend_lastknown_"):
        return blend_last_known_with_ensemble(last_known, ensemble, alpha_last_known)
    raise KeyError(f"Unknown selected model: {selected_model}")


def train_and_evaluate(
    datasets: MaskedDatasets,
    config: TrainingConfig,
) -> TrainedModels:
    """
    Fit medians + required residual models on train masks, evaluate on val masks,
    then refit on train+val for export.
    """

    feature_columns = list(datasets.feature_columns)
    train_df = datasets.train_df
    val_df = datasets.val_df

    train_medians_raw = fit_median_imputer(train_df, feature_columns)
    train_medians, _ = _serialize_medians(
        train_medians_raw,
        feature_columns,
        config.missing_median_fallback,
    )

    fit_df = subsample_fit_rows(
        train_df,
        config.model_fit_max_rows,
        config.random_state,
    )
    X_fit = transform_with_medians(fit_df, feature_columns, train_medians)
    y_fit = fit_df["residual_target"].to_numpy(dtype=np.float32)
    X_val = transform_with_medians(val_df, feature_columns, train_medians)

    y_val = val_df["actual_tvt"].to_numpy(dtype=float)
    wells_val = val_df["well_id"].to_numpy()
    linear_val = val_df["linear_tvt_projection"].to_numpy(dtype=float)
    last_known_val = val_df["last_known_tvt"].to_numpy(dtype=float)

    include_et = bool(config.include_optional_extra_trees) or config.weight_extra_trees > 0.0

    et_model = None
    pred_et_val = None
    if include_et:
        et_model = ExtraTreesRegressor(**config.et_params)
        et_model.fit(X_fit, y_fit)
        pred_et_val = apply_residual_model(linear_val, et_model.predict(X_val))

    xgb_model = XGBRegressor(**config.xgb_params)
    xgb_model.fit(X_fit, y_fit)
    pred_xgb_val = apply_residual_model(linear_val, xgb_model.predict(X_val))

    comparison_rows = []
    per_well_frames = []

    candidates: dict[str, np.ndarray] = {
        "last_known_tvt": last_known_val,
        "linear_projection": linear_val,
        "xgboost_residual": pred_xgb_val,
    }
    if pred_et_val is not None:
        candidates["extra_trees_residual"] = pred_et_val
        ensemble_val = weighted_ensemble(
            pred_et_val,
            pred_xgb_val,
            config.weight_extra_trees,
            config.weight_xgboost,
        )
        candidates["weighted_et_xgb_ensemble"] = ensemble_val
    else:
        # Production default: w_ET=0 → ensemble is pure XGBoost residual TVT.
        ensemble_val = weighted_ensemble(
            None,
            pred_xgb_val,
            config.weight_extra_trees,
            config.weight_xgboost,
        )

    blend_val = blend_last_known_with_ensemble(
        last_known_val,
        ensemble_val,
        config.alpha_last_known,
    )
    candidates[config.selected_model] = blend_val

    for name, preds in candidates.items():
        overall, per_well = calculate_validation_metrics(y_val, preds, wells_val, name)
        comparison_rows.append(overall)
        per_well_frames.append(per_well)

    comparison_df = pd.DataFrame(comparison_rows).sort_values(
        ["rmse", "mean_well_rmse"]
    ).reset_index(drop=True)
    per_well_df = pd.concat(per_well_frames, ignore_index=True)

    selected_metrics = comparison_df.loc[
        comparison_df["model"] == config.selected_model
    ].iloc[0].to_dict()

    # Final refit on train+val for export artifacts.
    full_df = pd.concat([train_df, val_df], ignore_index=True)
    final_medians_raw = fit_median_imputer(full_df, feature_columns)
    final_medians, missing_median_features = _serialize_medians(
        final_medians_raw,
        feature_columns,
        config.missing_median_fallback,
    )
    final_fit_df = subsample_fit_rows(
        full_df,
        config.model_fit_max_rows,
        config.random_state,
    )
    X_full = transform_with_medians(final_fit_df, feature_columns, final_medians)
    y_full = final_fit_df["residual_target"].to_numpy(dtype=np.float32)

    final_xgb = XGBRegressor(**config.xgb_params)
    final_xgb.fit(X_full, y_full)

    final_et = None
    if include_et:
        final_et = ExtraTreesRegressor(**config.et_params)
        final_et.fit(X_full, y_full)

    return TrainedModels(
        feature_columns=feature_columns,
        medians=final_medians,
        missing_median_features=missing_median_features,
        xgb_model=final_xgb,
        et_model=final_et,
        validation_comparison=comparison_df,
        per_well_metrics=per_well_df,
        fit_rows=int(len(final_fit_df)),
        train_rows=int(len(train_df)),
        val_rows=int(len(val_df)),
        train_wells=int(train_df["well_id"].nunique()),
        val_wells=int(val_df["well_id"].nunique()),
        selected_model_metrics=selected_metrics,
        include_extra_trees=include_et,
    )
