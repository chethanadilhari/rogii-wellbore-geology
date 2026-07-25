"""Stable API error codes and HTTP exception helpers."""

from __future__ import annotations

from typing import Any

from fastapi import Request
from fastapi.responses import JSONResponse


class ErrorCode:
    INVALID_UPLOAD = "INVALID_UPLOAD"
    FILE_TOO_LARGE = "FILE_TOO_LARGE"
    EMPTY_FILE = "EMPTY_FILE"
    INVALID_CSV = "INVALID_CSV"
    DUPLICATE_COLUMNS = "DUPLICATE_COLUMNS"
    MISSING_REQUIRED_COLUMNS = "MISSING_REQUIRED_COLUMNS"
    INVALID_MD = "INVALID_MD"
    NO_KNOWN_TVT = "NO_KNOWN_TVT"
    NO_PREDICTION_ROWS = "NO_PREDICTION_ROWS"
    NON_TRAILING_TVT_GAP = "NON_TRAILING_TVT_GAP"
    UNSAFE_WELL_ID = "UNSAFE_WELL_ID"
    ROW_LIMIT_EXCEEDED = "ROW_LIMIT_EXCEEDED"
    MODEL_UNAVAILABLE = "MODEL_UNAVAILABLE"
    ARTIFACT_VERIFICATION_FAILED = "ARTIFACT_VERIFICATION_FAILED"
    PREDICTION_FAILED = "PREDICTION_FAILED"
    INTERNAL_ERROR = "INTERNAL_ERROR"


_STATUS_BY_CODE: dict[str, int] = {
    ErrorCode.INVALID_UPLOAD: 400,
    ErrorCode.FILE_TOO_LARGE: 413,
    ErrorCode.EMPTY_FILE: 400,
    ErrorCode.INVALID_CSV: 400,
    ErrorCode.DUPLICATE_COLUMNS: 400,
    ErrorCode.MISSING_REQUIRED_COLUMNS: 422,
    ErrorCode.INVALID_MD: 422,
    ErrorCode.NO_KNOWN_TVT: 422,
    ErrorCode.NO_PREDICTION_ROWS: 422,
    ErrorCode.NON_TRAILING_TVT_GAP: 422,
    ErrorCode.UNSAFE_WELL_ID: 400,
    ErrorCode.ROW_LIMIT_EXCEEDED: 422,
    ErrorCode.MODEL_UNAVAILABLE: 503,
    ErrorCode.ARTIFACT_VERIFICATION_FAILED: 503,
    ErrorCode.PREDICTION_FAILED: 500,
    ErrorCode.INTERNAL_ERROR: 500,
}


class ApiError(Exception):
    """Application error with a stable machine-readable code."""

    def __init__(
        self,
        code: str,
        message: str,
        *,
        details: dict[str, Any] | None = None,
        status_code: int | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or {}
        self.status_code = status_code or _STATUS_BY_CODE.get(code, 500)


def map_validation_message(message: str) -> str:
    """Map a package validation error string to a stable API error code."""

    lower = message.lower()
    if "duplicate column" in lower:
        return ErrorCode.DUPLICATE_COLUMNS
    if "missing required columns" in lower:
        return ErrorCode.MISSING_REQUIRED_COLUMNS
    if "column md" in lower or lower.startswith("md "):
        return ErrorCode.INVALID_MD
    if "entirely missing" in lower and "tvt_input" in lower:
        return ErrorCode.NO_KNOWN_TVT
    if "no known-prefix" in lower:
        return ErrorCode.NO_KNOWN_TVT
    if "no prediction rows" in lower:
        return ErrorCode.NO_PREDICTION_ROWS
    if "clean trailing mask" in lower or "trailing" in lower:
        return ErrorCode.NON_TRAILING_TVT_GAP
    if "empty" in lower:
        return ErrorCode.EMPTY_FILE
    return ErrorCode.INVALID_CSV


def error_payload(
    *,
    code: str,
    message: str,
    details: dict[str, Any] | None,
    request_id: str,
) -> dict[str, Any]:
    return {
        "error": {
            "code": code,
            "message": message,
            "details": details or {},
            "request_id": request_id,
        }
    }


async def api_error_handler(request: Request, exc: ApiError) -> JSONResponse:
    request_id = getattr(request.state, "request_id", None) or request.headers.get(
        "X-Request-ID", "unknown"
    )
    payload = error_payload(
        code=exc.code,
        message=exc.message,
        details=exc.details,
        request_id=str(request_id),
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=payload,
        headers={"X-Request-ID": str(request_id)},
    )


async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    request_id = getattr(request.state, "request_id", None) or request.headers.get(
        "X-Request-ID", "unknown"
    )
    payload = error_payload(
        code=ErrorCode.INTERNAL_ERROR,
        message="An unexpected internal error occurred.",
        details={},
        request_id=str(request_id),
    )
    return JSONResponse(
        status_code=500,
        content=payload,
        headers={"X-Request-ID": str(request_id)},
    )
