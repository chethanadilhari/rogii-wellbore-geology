"""HTTP response helpers for CSV downloads."""

from __future__ import annotations

from io import StringIO

import pandas as pd
from fastapi.responses import Response


def dataframe_to_csv_bytes(frame: pd.DataFrame) -> bytes:
    buffer = StringIO()
    frame.to_csv(buffer, index=False)
    return buffer.getvalue().encode("utf-8")


def csv_download_response(
    frame: pd.DataFrame,
    *,
    filename: str,
    headers: dict[str, str] | None = None,
) -> Response:
    safe_name = filename.replace("\\", "_").replace("/", "_").replace("..", "_")
    content = dataframe_to_csv_bytes(frame)
    response_headers = {
        "Content-Disposition": f'attachment; filename="{safe_name}"',
        **(headers or {}),
    }
    return Response(
        content=content,
        media_type="text/csv; charset=utf-8",
        headers=response_headers,
    )


def prediction_headers(
    *,
    model_version: str,
    selected_model: str,
    well_id: str,
    total_rows: int,
    known_rows: int,
    prediction_rows: int,
) -> dict[str, str]:
    return {
        "X-Model-Version": str(model_version),
        "X-Selected-Model": str(selected_model),
        "X-Well-Id": str(well_id),
        "X-Total-Rows": str(total_rows),
        "X-Known-Rows": str(known_rows),
        "X-Prediction-Rows": str(prediction_rows),
    }
