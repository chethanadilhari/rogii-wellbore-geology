"""Safe multipart CSV upload parsing for one-well requests."""

from __future__ import annotations

import csv
import io
import logging
from pathlib import Path

import pandas as pd
from fastapi import UploadFile

from app.api.errors import ApiError, ErrorCode
from rogii_geo.inference.well_id import resolve_well_id, sanitize_well_id

logger = logging.getLogger(__name__)

_ALLOWED_CONTENT_TYPES = {
    "",
    "application/octet-stream",
    "text/csv",
    "application/csv",
    "text/plain",
}


async def read_upload_bytes(
    upload: UploadFile,
    *,
    max_bytes: int,
) -> tuple[bytes, str]:
    """Read an upload into memory while enforcing size and extension checks."""

    if upload is None:
        raise ApiError(ErrorCode.INVALID_UPLOAD, "A CSV file upload is required.")

    filename = (upload.filename or "").strip()
    if not filename:
        raise ApiError(ErrorCode.INVALID_UPLOAD, "Uploaded file must include a filename.")

    suffix = Path(filename).suffix.lower()
    if suffix != ".csv":
        raise ApiError(
            ErrorCode.INVALID_UPLOAD,
            "Uploaded file must use a .csv extension.",
            details={"filename_extension": suffix or None},
        )

    content_type = (upload.content_type or "").split(";")[0].strip().lower()
    if content_type not in _ALLOWED_CONTENT_TYPES:
        raise ApiError(
            ErrorCode.INVALID_UPLOAD,
            "Unsupported content type for CSV upload.",
            details={"content_type": content_type or None},
        )

    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = await upload.read(1024 * 1024)
        if not chunk:
            break
        total += len(chunk)
        if total > max_bytes:
            raise ApiError(
                ErrorCode.FILE_TOO_LARGE,
                f"Upload exceeds the configured size limit of {max_bytes} bytes.",
                details={"max_bytes": max_bytes},
            )
        chunks.append(chunk)

    data = b"".join(chunks)
    if not data:
        raise ApiError(ErrorCode.EMPTY_FILE, "Uploaded CSV is empty.")
    return data, filename


def parse_horizontal_csv_bytes(data: bytes) -> pd.DataFrame:
    """Parse one horizontal-well CSV from in-memory bytes (UTF-8 / UTF-8-BOM)."""

    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ApiError(
            ErrorCode.INVALID_CSV,
            "Uploaded CSV must be valid UTF-8 text.",
        ) from exc

    if not text.strip():
        raise ApiError(ErrorCode.EMPTY_FILE, "Uploaded CSV is empty.")

    try:
        reader = csv.reader(io.StringIO(text))
        header = next(reader)
    except StopIteration as exc:
        raise ApiError(ErrorCode.EMPTY_FILE, "Uploaded CSV is empty.") from exc
    except csv.Error as exc:
        raise ApiError(ErrorCode.INVALID_CSV, "Uploaded CSV could not be parsed.") from exc

    if not header or all(not str(c).strip() for c in header):
        raise ApiError(ErrorCode.INVALID_CSV, "Uploaded CSV has no header columns.")
    if len(header) != len(set(header)):
        duplicates = sorted({c for c in header if header.count(c) > 1})
        raise ApiError(
            ErrorCode.DUPLICATE_COLUMNS,
            "Duplicate column names are not allowed.",
            details={"duplicates": duplicates},
        )

    try:
        frame = pd.read_csv(io.StringIO(text))
    except Exception as exc:  # noqa: BLE001 - map parse failures
        raise ApiError(
            ErrorCode.INVALID_CSV,
            "Uploaded CSV is malformed and could not be loaded.",
        ) from exc

    if frame.empty:
        raise ApiError(ErrorCode.EMPTY_FILE, "Uploaded CSV has no data rows.")
    if frame.columns.duplicated().any():
        duplicates = frame.columns[frame.columns.duplicated()].tolist()
        raise ApiError(
            ErrorCode.DUPLICATE_COLUMNS,
            "Duplicate column names are not allowed.",
            details={"duplicates": [str(c) for c in duplicates]},
        )
    return frame


def resolve_upload_well_id(filename: str, explicit_well_id: str | None) -> str:
    """Resolve well ID from optional form field or upload filename."""

    try:
        if explicit_well_id is not None and str(explicit_well_id).strip():
            return sanitize_well_id(explicit_well_id)
        return resolve_well_id(Path(filename), None)
    except ValueError as exc:
        raise ApiError(
            ErrorCode.UNSAFE_WELL_ID,
            str(exc),
            details={"filename": Path(filename).name},
        ) from exc


def enforce_row_limit(frame: pd.DataFrame, *, max_rows: int) -> None:
    if len(frame) > max_rows:
        raise ApiError(
            ErrorCode.ROW_LIMIT_EXCEEDED,
            f"Well exceeds the configured row limit of {max_rows}.",
            details={"row_count": int(len(frame)), "max_rows": max_rows},
        )
