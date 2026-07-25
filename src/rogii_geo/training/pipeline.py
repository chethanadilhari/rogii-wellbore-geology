"""Orchestrate training, export, reload parity, and current pointer update."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

from rogii_geo.models.artifact_loader import load_artifact_bundle
from rogii_geo.training.artifacts import (
    default_model_version,
    ensure_artifact_dir,
    export_artifact_bundle,
    verify_checksums,
    write_current_pointer,
)
from rogii_geo.training.config import TrainingConfig
from rogii_geo.training.dataset import MaskedDatasets, build_masked_datasets
from rogii_geo.training.discovery import (
    estimate_test_missing_fractions,
    resolve_train_dir,
)
from rogii_geo.training.trainer import TrainedModels, predict_absolute_tvt, train_and_evaluate


PARITY_ATOL = 1e-6


@dataclass
class TrainExportResult:
    artifact_dir: Path
    model_version: str
    selected_model: str
    validation_rmse: float
    training_wells: int
    final_fit_rows: int
    feature_count: int
    required_models: list[str]
    optional_models: list[str]
    parity_max_abs_diff: float
    checksums_ok: bool
    current_pointer: Path
    summary: dict[str, Any]


def run_parity_check(
    trained: TrainedModels,
    datasets: MaskedDatasets,
    config: TrainingConfig,
    artifact_dir: Path,
    *,
    max_rows: int = 5000,
) -> float:
    """Compare in-memory vs reloaded predictions on a fixed validation subsample."""

    sample = datasets.val_df
    if len(sample) > max_rows:
        sample = sample.sample(n=max_rows, random_state=config.random_state)

    in_memory = predict_absolute_tvt(
        sample,
        trained.feature_columns,
        trained.medians,
        xgb_model=trained.xgb_model,
        et_model=trained.et_model,
        alpha_last_known=config.alpha_last_known,
        weight_extra_trees=config.weight_extra_trees,
        weight_xgboost=config.weight_xgboost,
        selected_model=config.selected_model,
    )

    bundle = load_artifact_bundle(artifact_dir, verify=True)
    if bundle.feature_columns != trained.feature_columns:
        raise RuntimeError("Reloaded feature_columns order/content mismatch")
    reloaded = bundle.predict_masked_frame(sample)

    if len(in_memory) != len(reloaded):
        raise RuntimeError("Parity row-count mismatch")
    if not np.isfinite(in_memory).all() or not np.isfinite(reloaded).all():
        raise RuntimeError("Non-finite predictions during parity check")

    max_diff = float(np.max(np.abs(in_memory - reloaded)))
    if max_diff > PARITY_ATOL:
        raise RuntimeError(
            f"Reload parity failed: max abs diff={max_diff} exceeds {PARITY_ATOL}"
        )
    return max_diff


def run_train_export(
    *,
    project_root: Path,
    train_dir: Path | None = None,
    artifact_root: Path | None = None,
    model_version: str | None = None,
    config: TrainingConfig | None = None,
    overwrite: bool = False,
) -> TrainExportResult:
    project_root = Path(project_root).resolve()
    config = config or TrainingConfig()
    config = config.with_random_state(config.random_state)

    resolved_train = resolve_train_dir(project_root, train_dir)
    # Prefer sibling test dir for missing-fraction estimates when present.
    test_candidate = resolved_train.parent / "test"
    config.test_missing_fractions = estimate_test_missing_fractions(
        test_candidate if test_candidate.is_dir() else None,
        config.test_missing_fractions,
    )

    artifact_root = Path(artifact_root or (project_root / "artifacts")).resolve()
    version = model_version or default_model_version()
    artifact_dir = ensure_artifact_dir(artifact_root, version, overwrite=overwrite)

    datasets = build_masked_datasets(resolved_train, config)
    trained = train_and_evaluate(datasets, config)

    created_at = datetime.now(timezone.utc)
    manifest = export_artifact_bundle(
        artifact_dir,
        model_version=version,
        trained=trained,
        datasets=datasets,
        config=config,
        project_root=project_root,
        created_at=created_at,
    )
    verify_checksums(artifact_dir, manifest)
    parity_diff = run_parity_check(trained, datasets, config, artifact_dir)
    current_pointer = write_current_pointer(artifact_root, version)

    required_models = ["xgboost_residual"]
    optional_models = ["extra_trees_residual"] if trained.include_extra_trees else []

    summary = {
        "artifact_dir": str(artifact_dir),
        "model_version": version,
        "selected_recipe": config.selected_model,
        "validation_rmse": float(trained.selected_model_metrics.get("rmse", np.nan)),
        "training_wells": trained.train_wells,
        "final_fit_rows": trained.fit_rows,
        "feature_count": len(trained.feature_columns),
        "required_models_exported": required_models,
        "optional_models_exported": optional_models,
        "parity_max_abs_diff": parity_diff,
        "checksums_ok": True,
        "current_pointer": str(current_pointer),
    }

    return TrainExportResult(
        artifact_dir=artifact_dir,
        model_version=version,
        selected_model=config.selected_model,
        validation_rmse=float(trained.selected_model_metrics.get("rmse", np.nan)),
        training_wells=trained.train_wells,
        final_fit_rows=trained.fit_rows,
        feature_count=len(trained.feature_columns),
        required_models=required_models,
        optional_models=optional_models,
        parity_max_abs_diff=parity_diff,
        checksums_ok=True,
        current_pointer=current_pointer,
        summary=summary,
    )
