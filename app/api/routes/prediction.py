"""Prediction endpoints returning downloadable CSV responses."""

from __future__ import annotations

import logging
import time

from fastapi import APIRouter, File, Form, Request, UploadFile
from fastapi.responses import Response

from app.api.config import Settings, get_settings
from app.api.dependencies import get_inference_service
from app.api.errors import ApiError, ErrorCode, map_validation_message
from app.api.responses import csv_download_response, prediction_headers
from app.api.uploads import (
    enforce_row_limit,
    parse_horizontal_csv_bytes,
    read_upload_bytes,
    resolve_upload_well_id,
)

router = APIRouter(tags=["prediction"])
logger = logging.getLogger(__name__)


async def _run_prediction(
    request: Request,
    file: UploadFile,
    well_id: str | None,
):
    settings: Settings = getattr(request.app.state, "settings", None) or get_settings()
    service = get_inference_service(request)
    started = time.perf_counter()

    data, filename = await read_upload_bytes(file, max_bytes=settings.max_upload_bytes)
    resolved_id = resolve_upload_well_id(filename, well_id)
    frame = parse_horizontal_csv_bytes(data)
    enforce_row_limit(frame, max_rows=settings.max_rows_per_well)

    try:
        result = service.predict_dataframe(frame, resolved_id)
    except ValueError as exc:
        message = str(exc)
        # Strip "Well X failed validation: " prefix when present.
        if "failed validation:" in message:
            detail = message.split("failed validation:", 1)[1].strip()
            first = detail.split(";")[0].strip()
            code = map_validation_message(first)
            raise ApiError(
                code,
                first,
                details={"well_id": resolved_id},
            ) from exc
        raise ApiError(
            ErrorCode.PREDICTION_FAILED,
            "Prediction failed due to invalid well data.",
            details={"well_id": resolved_id},
        ) from exc
    except Exception as exc:  # noqa: BLE001
        logger.exception(
            "prediction failed request_id=%s well_id=%s",
            getattr(request.state, "request_id", None),
            resolved_id,
        )
        raise ApiError(
            ErrorCode.PREDICTION_FAILED,
            "Prediction failed due to an internal error.",
            details={"well_id": resolved_id},
        ) from exc

    duration_ms = (time.perf_counter() - started) * 1000.0
    summary = result.summary
    logger.info(
        "predict ok request_id=%s well_id=%s rows=%s pred_rows=%s model=%s duration_ms=%.1f",
        getattr(request.state, "request_id", None),
        summary.get("well_id"),
        summary.get("total_rows"),
        summary.get("prediction_rows"),
        summary.get("model_version"),
        duration_ms,
    )
    return result


def _summary_headers(result) -> dict[str, str]:
    summary = result.summary
    return prediction_headers(
        model_version=str(summary["model_version"]),
        selected_model=str(summary["selected_model"]),
        well_id=str(summary["well_id"]),
        total_rows=int(summary["total_rows"]),
        known_rows=int(summary["known_rows"]),
        prediction_rows=int(summary["prediction_rows"]),
    )


@router.post(
    "/predict",
    summary="Predict missing TVT rows and return competition-format CSV",
    response_class=Response,
    responses={
        200: {
            "content": {"text/csv": {}},
            "description": "Competition CSV with columns id,tvt",
        }
    },
)
async def predict_competition(
    request: Request,
    file: UploadFile = File(..., description="Horizontal-well CSV"),
    well_id: str | None = Form(default=None),
) -> Response:
    result = await _run_prediction(request, file, well_id)
    well = str(result.summary["well_id"])
    return csv_download_response(
        result.competition_output,
        filename=f"{well}_submission.csv",
        headers=_summary_headers(result),
    )


@router.post(
    "/predict/full-well",
    summary="Predict missing TVT rows and return full-well CSV",
    response_class=Response,
    responses={
        200: {
            "content": {"text/csv": {}},
            "description": "Full-well CSV with predicted_tvt and prediction_source",
        }
    },
)
async def predict_full_well(
    request: Request,
    file: UploadFile = File(..., description="Horizontal-well CSV"),
    well_id: str | None = Form(default=None),
) -> Response:
    result = await _run_prediction(request, file, well_id)
    well = str(result.summary["well_id"])
    return csv_download_response(
        result.full_well_output,
        filename=f"{well}_full_well_predictions.csv",
        headers=_summary_headers(result),
    )
