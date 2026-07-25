"""Health endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Request

from app.api.errors import ApiError, ErrorCode
from app.api.schemas import HealthResponse

router = APIRouter(tags=["health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Liveness/readiness for the loaded prediction service",
)
def health(request: Request) -> HealthResponse:
    service = getattr(request.app.state, "inference_service", None)
    info = getattr(request.app.state, "model_info", None)
    if service is None or info is None:
        raise ApiError(
            ErrorCode.MODEL_UNAVAILABLE,
            "Prediction service is not ready.",
        )
    return HealthResponse(
        status="healthy",
        model_loaded=True,
        model_version=str(info.model_version),
        selected_model=str(info.selected_model),
    )
