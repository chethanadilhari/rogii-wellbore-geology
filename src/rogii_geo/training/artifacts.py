"""Export immutable versioned artifact bundles."""

from __future__ import annotations

import hashlib
import json
import os
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd

from rogii_geo._version import __version__ as PACKAGE_VERSION
from rogii_geo.checksums import sha256_file, verify_checksums
from rogii_geo.constants import PRIMARY_SLOPE_WINDOW
from rogii_geo.training.config import SOURCE_NOTEBOOK, SCHEMA_VERSION, TrainingConfig
from rogii_geo.training.dataset import MaskedDatasets
from rogii_geo.training.trainer import TrainedModels


REQUIRED_ARTIFACT_FILES = [
    "xgboost_residual.json",
    "feature_columns.json",
    "feature_medians.json",
    "ensemble_config.json",
    "model_card.json",
    "validation_comparison.csv",
    "per_well_validation_metrics.csv",
    "training_dataset_summary.csv",
    "mask_summary.csv",
]

OPTIONAL_ARTIFACT_FILES = [
    "extra_trees_residual.joblib",
]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def default_model_version(now: datetime | None = None) -> str:
    stamp = (now or datetime.now(timezone.utc)).strftime("%Y%m%d_%H%M%S")
    return f"v1_{stamp}"


def get_git_sha(project_root: Path) -> str | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(project_root),
            check=True,
            capture_output=True,
            text=True,
        )
        return result.stdout.strip() or None
    except Exception:
        return None


def ensure_artifact_dir(
    artifact_root: Path,
    model_version: str,
    *,
    overwrite: bool = False,
) -> Path:
    target = Path(artifact_root) / model_version
    if target.exists():
        existing = [p for p in target.iterdir()]
        if existing and not overwrite:
            raise FileExistsError(
                f"Artifact directory already exists and is not empty: {target}. "
                "Pass --overwrite to replace it."
            )
        if overwrite:
            for path in target.rglob("*"):
                if path.is_file():
                    path.unlink()
    target.mkdir(parents=True, exist_ok=True)
    return target


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def export_artifact_bundle(
    artifact_dir: Path,
    *,
    model_version: str,
    trained: TrainedModels,
    datasets: MaskedDatasets,
    config: TrainingConfig,
    project_root: Path,
    created_at: datetime | None = None,
) -> dict[str, Any]:
    """Write all artifact files and return the manifest dict (without self-hash)."""

    artifact_dir = Path(artifact_dir)
    created = created_at or datetime.now(timezone.utc)
    created_iso = created.isoformat()

    # XGBoost native serialization
    xgb_path = artifact_dir / "xgboost_residual.json"
    if trained.xgb_model is None:
        raise RuntimeError("XGBoost model missing; cannot export production artifacts.")
    trained.xgb_model.save_model(str(xgb_path))

    et_exported = False
    if trained.et_model is not None:
        joblib.dump(trained.et_model, artifact_dir / "extra_trees_residual.joblib")
        et_exported = True

    write_json(artifact_dir / "feature_columns.json", trained.feature_columns)
    write_json(
        artifact_dir / "feature_medians.json",
        {k: float(v) for k, v in trained.medians.items()},
    )

    required_predictors = ["last_known"]
    optional_predictors = ["extra_trees_residual"]
    if config.weight_xgboost > 0 or config.selected_model.startswith("blend_lastknown_"):
        required_predictors.append("xgboost_residual")
    if config.weight_extra_trees > 0:
        required_predictors.append("extra_trees_residual")
        optional_predictors = []

    ensemble_config = {
        "selected_model": config.selected_model,
        "alpha_last_known": float(config.alpha_last_known),
        "weight_extra_trees": float(config.weight_extra_trees),
        "weight_xgboost": float(config.weight_xgboost),
        "primary_slope_window": int(config.primary_slope_window),
        "required_predictors": required_predictors,
        "optional_predictors": optional_predictors,
    }
    write_json(artifact_dir / "ensemble_config.json", ensemble_config)

    git_sha = get_git_sha(project_root)
    selected = trained.selected_model_metrics
    model_card = {
        "model_version": model_version,
        "selected_model": config.selected_model,
        "effective_formula": (
            "final_tvt = 0.70 * last_known_tvt + 0.30 * "
            "(linear_tvt_projection + xgb_predicted_residual)"
        ),
        "validation_rmse": float(selected.get("rmse", np.nan)),
        "validation_mae": float(selected.get("mae", np.nan)),
        "validation_well_count": int(selected.get("n_wells", trained.val_wells)),
        "validation_row_count": int(selected.get("n_rows", trained.val_rows)),
        "training_well_count": int(trained.train_wells),
        "training_row_count": int(trained.train_rows),
        "final_fit_row_count": int(trained.fit_rows),
        "feature_count": int(len(trained.feature_columns)),
        "xgboost_params": dict(config.xgb_params),
        "extra_trees_params": dict(config.et_params) if et_exported else None,
        "extra_trees_exported": et_exported,
        "random_state": int(config.random_state),
        "training_timestamp_utc": created_iso,
        "python_version": sys.version.split()[0],
        "platform": platform.platform(),
        "pandas_version": pd.__version__,
        "numpy_version": np.__version__,
        "sklearn_version": __import__("sklearn").__version__,
        "xgboost_version": __import__("xgboost").__version__,
        "git_commit_sha": git_sha,
        "package_version": PACKAGE_VERSION,
        "source_notebook": SOURCE_NOTEBOOK,
        "schema_version": SCHEMA_VERSION,
        "known_limitations": [
            "Production recipe is frozen; this export does not re-select models.",
            "Extra Trees is optional when weight_extra_trees == 0.",
            "Formation markers may be absent on uploaded wells and are median-filled.",
        ],
        "missing_median_fallback": float(config.missing_median_fallback),
        "missing_median_features": list(trained.missing_median_features),
        "primary_slope_window": PRIMARY_SLOPE_WINDOW,
    }
    write_json(artifact_dir / "model_card.json", model_card)

    trained.validation_comparison.to_csv(
        artifact_dir / "validation_comparison.csv",
        index=False,
    )
    trained.per_well_metrics.to_csv(
        artifact_dir / "per_well_validation_metrics.csv",
        index=False,
    )
    datasets.dataset_summary.to_csv(
        artifact_dir / "training_dataset_summary.csv",
        index=False,
    )
    datasets.mask_summary.to_csv(
        artifact_dir / "mask_summary.csv",
        index=False,
    )

    checksums: dict[str, str] = {}
    for name in REQUIRED_ARTIFACT_FILES:
        path = artifact_dir / name
        if not path.exists():
            raise FileNotFoundError(f"Required artifact missing after export: {path}")
        checksums[name] = sha256_file(path)
    for name in OPTIONAL_ARTIFACT_FILES:
        path = artifact_dir / name
        if path.exists():
            checksums[name] = sha256_file(path)

    manifest = {
        "artifact_version": model_version,
        "created_at_utc": created_iso,
        "selected_model": config.selected_model,
        "required_files": list(REQUIRED_ARTIFACT_FILES),
        "optional_files": [f for f in OPTIONAL_ARTIFACT_FILES if (artifact_dir / f).exists()],
        "file_checksums_sha256": checksums,
        "feature_count": int(len(trained.feature_columns)),
        "schema_version": SCHEMA_VERSION,
        "package_version": PACKAGE_VERSION,
        "git_commit_sha": git_sha,
        "compatibility": {
            "inference_requires": required_predictors,
            "xgboost_format": "xgboost_residual.json via Booster/XGBRegressor.load_model",
        },
    }
    write_json(artifact_dir / "manifest.json", manifest)
    return manifest


def write_current_pointer(artifact_root: Path, model_version: str) -> Path:
    """Atomically update artifacts/current.json after a successful export."""

    artifact_root = Path(artifact_root)
    artifact_root.mkdir(parents=True, exist_ok=True)
    target = artifact_root / "current.json"
    temp = artifact_root / "current.json.tmp"
    payload = {
        "model_version": model_version,
        "updated_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    temp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    os.replace(temp, target)
    return target


def verify_checksums(artifact_dir: Path, manifest: dict[str, Any] | None = None) -> None:
    from rogii_geo.checksums import verify_checksums as _verify

    _verify(artifact_dir, manifest)
