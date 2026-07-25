"""Model metadata endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Request

from app.api.dependencies import get_model_info
from app.api.schemas import ModelInfoResponse

router = APIRouter(tags=["models"])


@router.get(
    "/models/current",
    response_model=ModelInfoResponse,
    summary="Safe metadata for the active production artifact bundle",
)
def models_current(request: Request) -> ModelInfoResponse:
    return get_model_info(request)
