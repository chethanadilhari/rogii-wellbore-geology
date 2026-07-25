"""High-level one-well inference service (no training, no API concerns)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from rogii_geo import __version__ as PACKAGE_VERSION
from rogii_geo.checksums import sha256_file
from rogii_geo.inference.outputs import (
    MODEL_SOURCE,
    build_competition_output,
    build_original_order_full_well,
    build_prediction_frame,
)
from rogii_geo.inference.pipeline import build_inference_features
from rogii_geo.inference.well_id import sanitize_well_id
from rogii_geo.models.artifact_loader import (
    ArtifactBundle,
    load_artifact_bundle,
    resolve_artifact_dir,
)
from rogii_geo.models.config import models_required_by_config
from rogii_geo.validation.well import validate_horizontal_well


def _json_native(value: Any) -> Any:
    """Convert NumPy / pandas scalars to JSON-native Python types."""

    if isinstance(value, dict):
        return {str(k): _json_native(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_native(v) for v in value]
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, (str, bytes)):
        return value
    if value is None:
        return None
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return float(value)
    if isinstance(value, (np.bool_,)):
        return bool(value)
    if isinstance(value, np.ndarray):
        return [_json_native(v) for v in value.tolist()]
    if isinstance(value, (bool, int, float)):
        return value
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    return value


def required_predictors_for_bundle(bundle: ArtifactBundle) -> list[str]:
    """Deterministic list of predictors required by the loaded recipe."""

    required = ["last_known"]
    flags = models_required_by_config(bundle.ensemble_config)
    if flags["xgboost"]:
        required.append("xgboost_residual")
    if flags["extra_trees"]:
        required.append("extra_trees_residual")
    return required


def _rows_reordered(original_df: pd.DataFrame, feat: pd.DataFrame) -> bool:
    original_order = original_df.index.astype(int).to_numpy()
    sorted_order = feat["original_row_index"].to_numpy(dtype=int)
    return not np.array_equal(original_order, sorted_order)


@dataclass(frozen=True)
class InferenceResult:
    """Competition CSV frame, full-well frame, and machine-readable summary."""

    competition_output: pd.DataFrame
    full_well_output: pd.DataFrame
    summary: dict[str, object]


class WellInferenceService:
    """Orchestrate artifact-backed prediction for one horizontal well."""

    def __init__(
        self,
        bundle: ArtifactBundle,
        *,
        checksum_verification: bool = True,
    ) -> None:
        self.bundle = bundle
        self.checksum_verification = bool(checksum_verification)

    @classmethod
    def from_artifact_root(
        cls,
        artifact_root: Path,
        *,
        model_version: str | None = None,
        verify_checksums: bool = True,
    ) -> "WellInferenceService":
        artifact_dir = resolve_artifact_dir(Path(artifact_root), model_version)
        bundle = load_artifact_bundle(artifact_dir, verify=verify_checksums)
        return cls(bundle, checksum_verification=verify_checksums)

    @property
    def model_version(self) -> str:
        return self.bundle.model_version

    @property
    def selected_model(self) -> str:
        return self.bundle.ensemble_config.selected_model

    @property
    def feature_count(self) -> int:
        return len(self.bundle.feature_columns)

    @property
    def required_predictors(self) -> list[str]:
        return required_predictors_for_bundle(self.bundle)

    def describe(self) -> dict[str, object]:
        return {
            "model_version": self.model_version,
            "selected_model": self.selected_model,
            "feature_count": self.feature_count,
            "required_predictors": self.required_predictors,
            "checksum_verification": self.checksum_verification,
            "extra_trees_loaded": self.bundle.et_model is not None,
            "xgboost_loaded": self.bundle.xgb_model is not None,
        }

    def predict_dataframe(
        self,
        horizontal_df: pd.DataFrame,
        well_id: str,
        *,
        input_file: str | Path | None = None,
        duration_seconds: float | None = None,
    ) -> InferenceResult:
        """
        Run the frozen production recipe on one validated horizontal well.

        No training occurs. Predictions are emitted only for missing ``TVT_input``.
        """

        well_id = sanitize_well_id(well_id)
        started = datetime.now(timezone.utc)
        warnings: list[str] = []

        validation = validate_horizontal_well(horizontal_df, well_id)
        warnings.extend(validation.warnings)
        if not validation.ok:
            raise ValueError(
                f"Well {well_id} failed validation: " + "; ".join(validation.errors)
            )

        original = horizontal_df.copy()
        feat, known_mask = build_inference_features(
            original,
            well_id,
            validate=False,
        )
        rows_reordered = _rows_reordered(original, feat)

        if list(self.bundle.feature_columns) != sorted(self.bundle.feature_columns):
            # Feature order is an explicit contract; keep the saved order.
            pass
        missing_feats = [c for c in self.bundle.feature_columns if c not in feat.columns]
        if missing_feats:
            raise ValueError(f"Engineered frame missing required features: {missing_feats}")

        hidden_feat = feat.loc[~known_mask.to_numpy()]
        if hidden_feat.empty:
            raise ValueError("No prediction rows after feature engineering.")

        # Guard: never leak TVT / TVT_input into the model matrix.
        leak_cols = {"TVT", "TVT_input"} & set(self.bundle.feature_columns)
        if leak_cols:
            raise RuntimeError(
                f"Feature columns must not include TVT leakage columns: {sorted(leak_cols)}"
            )

        predicted = self.bundle.predict_masked_frame(hidden_feat)
        if len(predicted) != len(hidden_feat):
            raise RuntimeError(
                f"Model returned {len(predicted)} predictions for {len(hidden_feat)} rows"
            )
        if not np.isfinite(predicted).all():
            raise RuntimeError("Model produced non-finite predictions.")

        pred_frame = build_prediction_frame(
            feat,
            known_mask,
            predicted,
            model_name=self.selected_model,
        )
        competition = build_competition_output(pred_frame)
        full_well = build_original_order_full_well(
            original,
            feat,
            known_mask,
            predicted,
        )

        pred_values = competition["tvt"].to_numpy(dtype=float)
        original_indices = pred_frame["original_row_index"].to_numpy(dtype=int)
        finished = datetime.now(timezone.utc)
        elapsed = (
            float(duration_seconds)
            if duration_seconds is not None
            else (finished - started).total_seconds()
        )

        input_path = Path(input_file) if input_file is not None else None
        input_sha = sha256_file(input_path) if input_path and input_path.exists() else None
        manifest_path = self.bundle.artifact_dir / "manifest.json"
        manifest_sha = sha256_file(manifest_path) if manifest_path.exists() else None

        summary: dict[str, object] = {
            "well_id": well_id,
            "input_file": str(input_path) if input_path is not None else None,
            "model_version": self.model_version,
            "selected_model": self.selected_model,
            "total_rows": int(len(original)),
            "known_rows": int(known_mask.sum()),
            "prediction_rows": int((~known_mask).sum()),
            "feature_count": int(self.feature_count),
            "required_predictors": list(self.required_predictors),
            "prediction_min": float(np.min(pred_values)),
            "prediction_max": float(np.max(pred_values)),
            "prediction_mean": float(np.mean(pred_values)),
            "prediction_std": float(np.std(pred_values)),
            "first_prediction_original_index": int(original_indices.min()),
            "last_prediction_original_index": int(original_indices.max()),
            "checksum_verification": bool(self.checksum_verification),
            "competition_output": "submission.csv",
            "full_well_output": "full_well_predictions.csv",
            "created_at_utc": finished.isoformat(),
            "input_file_sha256": input_sha,
            "artifact_manifest_sha256": manifest_sha,
            "rows_reordered_internally": bool(rows_reordered),
            "warnings": warnings,
            "prediction_duration_seconds": float(elapsed),
            "package_version": PACKAGE_VERSION,
            "prediction_source_model_rows": MODEL_SOURCE,
            "xgboost_loaded": self.bundle.xgb_model is not None,
            "extra_trees_loaded": self.bundle.et_model is not None,
            "artifact_dir": str(self.bundle.artifact_dir),
        }
        summary = _json_native(summary)
        assert isinstance(summary, dict)

        return InferenceResult(
            competition_output=competition,
            full_well_output=full_well,
            summary=summary,
        )
