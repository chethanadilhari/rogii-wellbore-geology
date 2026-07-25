"""Well validation endpoint (no prediction)."""

from __future__ import annotations

import logging
import time

from fastapi import APIRouter, File, Form, Request, UploadFile

from app.api.config import Settings, get_settings
from app.api.schemas import ValidateResponse
from app.api.uploads import (
    enforce_row_limit,
    parse_horizontal_csv_bytes,
    read_upload_bytes,
    resolve_upload_well_id,
)
from app.api.validation_service import build_validate_response, raise_for_invalid_well

router = APIRouter(tags=["validation"])
logger = logging.getLogger(__name__)


@router.post(
    "/validate",
    response_model=ValidateResponse,
    summary="Validate one horizontal-well CSV without running prediction",
)
async def validate_well(
    request: Request,
    file: UploadFile = File(..., description="Horizontal-well CSV"),
    well_id: str | None = Form(default=None),
) -> ValidateResponse:
    settings: Settings = getattr(request.app.state, "settings", None) or get_settings()
    started = time.perf_counter()
    data, filename = await read_upload_bytes(file, max_bytes=settings.max_upload_bytes)
    resolved_id = resolve_upload_well_id(filename, well_id)
    frame = parse_horizontal_csv_bytes(data)
    enforce_row_limit(frame, max_rows=settings.max_rows_per_well)
    response = build_validate_response(frame, resolved_id)
    raise_for_invalid_well(response)

    duration_ms = (time.perf_counter() - started) * 1000.0
    logger.info(
        "validate ok request_id=%s well_id=%s rows=%s duration_ms=%.1f",
        getattr(request.state, "request_id", None),
        response.well_id,
        response.total_rows,
        duration_ms,
    )
    return response
