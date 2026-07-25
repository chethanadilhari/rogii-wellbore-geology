"""FastAPI dependencies and safe model metadata builders."""

from __future__ import annotations

from typing import Any

from fastapi import Request

from app.api.errors import ApiError, ErrorCode
from app.api.schemas import ModelInfoResponse
from rogii_geo.inference.service import WellInferenceService, required_predictors_for_bundle


def get_request_id(request: Request) -> str:
    return str(getattr(request.state, "request_id", "unknown"))


def get_inference_service(request: Request) -> WellInferenceService:
    service = getattr(request.app.state, "inference_service", None)
    if service is None:
        raise ApiError(
            ErrorCode.MODEL_UNAVAILABLE,
            "Prediction service is not available.",
        )
    return service


def get_model_info(request: Request) -> ModelInfoResponse:
    info = getattr(request.app.state, "model_info", None)
    if info is None:
        raise ApiError(
            ErrorCode.MODEL_UNAVAILABLE,
            "Model metadata is not available.",
        )
    if isinstance(info, ModelInfoResponse):
        return info
    return ModelInfoResponse.model_validate(info)


def build_safe_model_info(service: WellInferenceService) -> ModelInfoResponse:
    """Extract client-safe metadata from the loaded artifact bundle."""

    card = service.bundle.model_card or {}
    cfg = service.bundle.ensemble_config
    optional: list[str] = []
    if not cfg.requires_extra_trees():
        optional.append("extra_trees_residual")

    created = card.get("training_timestamp_utc")
    return ModelInfoResponse(
        model_version=service.model_version,
        selected_model=service.selected_model,
        validation_rmse=_as_float(card.get("validation_rmse")),
        validation_mae=_as_float(card.get("validation_mae")),
        feature_count=service.feature_count,
        required_predictors=required_predictors_for_bundle(service.bundle),
        optional_predictors=optional,
        alpha_last_known=float(cfg.alpha_last_known),
        weight_extra_trees=float(cfg.weight_extra_trees),
        weight_xgboost=float(cfg.weight_xgboost),
        training_wells=_as_int(card.get("training_well_count")),
        final_fit_rows=_as_int(card.get("final_fit_row_count")),
        created_at_utc=str(created) if created else None,
    )


def _as_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _as_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
