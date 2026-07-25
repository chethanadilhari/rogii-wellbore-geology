"""Verify FinalProductionCandidate notebook metadata consistency."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from rogii_geo.constants import (
    PRODUCTION_ALPHA_LAST_KNOWN,
    PRODUCTION_SELECTED_MODEL,
    PRODUCTION_VALIDATION_RMSE,
    PRODUCTION_WEIGHT_EXTRA_TREES,
    PRODUCTION_WEIGHT_XGBOOST,
)
from rogii_geo.models.blend import parse_blend_alpha


@dataclass
class MetadataVerificationResult:
    ok: bool
    discrepancies: list[str]
    feature_column_count: int | None = None


def default_results_dir(project_root: Path | None = None) -> Path:
    root = project_root or Path(__file__).resolve().parents[2]
    return root / "results" / "ensemble_residual_submission"


def verify_production_metadata(results_dir: Path | None = None) -> MetadataVerificationResult:
    """
    Cross-check selected model, blend alpha, ensemble weights, and feature list.

    Raises nothing; returns discrepancies for the caller to stop on failure.
    """

    base = results_dir or default_results_dir()
    discrepancies: list[str] = []

    selected_path = base / "metadata" / "selected_model_summary.json"
    submission_path = base / "metadata" / "submission_summary.json"
    features_path = base / "metadata" / "feature_columns.json"
    weights_path = base / "tables" / "ensemble_weight_search.csv"
    comparison_path = base / "tables" / "validation_comparison.csv"

    for path in (selected_path, submission_path, features_path, weights_path, comparison_path):
        if not path.exists():
            discrepancies.append(f"Missing required artifact: {path}")

    if discrepancies:
        return MetadataVerificationResult(ok=False, discrepancies=discrepancies)

    selected = json.loads(selected_path.read_text(encoding="utf-8"))
    submission = json.loads(submission_path.read_text(encoding="utf-8"))
    feature_columns = json.loads(features_path.read_text(encoding="utf-8"))
    weights = pd.read_csv(weights_path)
    comparison = pd.read_csv(comparison_path)

    if selected.get("selected_model") != submission.get("selected_model"):
        discrepancies.append(
            "selected_model mismatch between selected_model_summary.json and "
            f"submission_summary.json: {selected.get('selected_model')} vs "
            f"{submission.get('selected_model')}"
        )

    if selected.get("selected_model") != PRODUCTION_SELECTED_MODEL:
        discrepancies.append(
            f"Package constant PRODUCTION_SELECTED_MODEL={PRODUCTION_SELECTED_MODEL} "
            f"does not match metadata selected_model={selected.get('selected_model')}"
        )

    top_model = str(comparison.iloc[0]["model"])
    if selected.get("selected_model") != top_model:
        discrepancies.append(
            f"selected_model_summary.json selected_model={selected.get('selected_model')} "
            f"does not match validation_comparison.csv top row={top_model}"
        )

    selected_rmse = float(selected["validation_rmse"])
    top_rmse = float(comparison.iloc[0]["rmse"])
    if abs(selected_rmse - top_rmse) > 1e-9:
        discrepancies.append(
            f"validation_rmse mismatch: selected={selected_rmse} vs comparison top={top_rmse}"
        )
    if abs(selected_rmse - float(submission["validation_rmse"])) > 1e-9:
        discrepancies.append(
            "validation_rmse mismatch between selected_model_summary.json and "
            "submission_summary.json"
        )
    if abs(selected_rmse - PRODUCTION_VALIDATION_RMSE) > 1e-9:
        discrepancies.append(
            f"Package PRODUCTION_VALIDATION_RMSE={PRODUCTION_VALIDATION_RMSE} "
            f"does not match metadata {selected_rmse}"
        )

    w_et = float(selected["best_ensemble_weight_extra_trees"])
    w_xgb = float(selected["best_ensemble_weight_xgboost"])
    best_weight_row = weights.iloc[0]
    if abs(w_et - float(best_weight_row["weight_extra_trees"])) > 1e-9:
        discrepancies.append(
            "best_ensemble_weight_extra_trees does not match ensemble_weight_search.csv top row"
        )
    if abs(w_xgb - float(best_weight_row["weight_xgboost"])) > 1e-9:
        discrepancies.append(
            "best_ensemble_weight_xgboost does not match ensemble_weight_search.csv top row"
        )
    if abs(w_et - PRODUCTION_WEIGHT_EXTRA_TREES) > 1e-9:
        discrepancies.append(
            f"Package PRODUCTION_WEIGHT_EXTRA_TREES={PRODUCTION_WEIGHT_EXTRA_TREES} "
            f"does not match metadata {w_et}"
        )
    if abs(w_xgb - PRODUCTION_WEIGHT_XGBOOST) > 1e-9:
        discrepancies.append(
            f"Package PRODUCTION_WEIGHT_XGBOOST={PRODUCTION_WEIGHT_XGBOOST} "
            f"does not match metadata {w_xgb}"
        )

    alpha = parse_blend_alpha(str(selected["selected_model"]))
    if abs(alpha - PRODUCTION_ALPHA_LAST_KNOWN) > 1e-9:
        discrepancies.append(
            f"Parsed blend alpha {alpha} does not match "
            f"PRODUCTION_ALPHA_LAST_KNOWN={PRODUCTION_ALPHA_LAST_KNOWN}"
        )

    n_features = len(feature_columns)
    if selected.get("n_features") is not None and int(selected["n_features"]) != n_features:
        discrepancies.append(
            f"n_features in selected_model_summary.json ({selected['n_features']}) "
            f"does not match feature_columns.json length ({n_features})"
        )
    if n_features != 51:
        discrepancies.append(f"Expected 51 feature columns, found {n_features}")

    required = {"MD", "GR", "linear_tvt_projection", "last_known_tvt"}
    missing_required = sorted(required - set(feature_columns))
    if missing_required:
        discrepancies.append(f"feature_columns.json missing required columns: {missing_required}")

    forbidden = {"TVT", "TVT_input", "sim_TVT_input", "actual_tvt", "residual_target"}
    leaked = sorted(forbidden & set(feature_columns))
    if leaked:
        discrepancies.append(f"feature_columns.json contains forbidden leakage columns: {leaked}")

    return MetadataVerificationResult(
        ok=len(discrepancies) == 0,
        discrepancies=discrepancies,
        feature_column_count=n_features,
    )
