"""Well validation helpers for the /validate endpoint (no model prediction)."""

from __future__ import annotations

import numpy as np
import pandas as pd

from app.api.errors import ApiError, map_validation_message
from app.api.schemas import ValidateResponse
from rogii_geo.validation.well import validate_horizontal_well


def build_validate_response(frame: pd.DataFrame, well_id: str) -> ValidateResponse:
    """Validate a parsed well frame without invoking residual models."""

    result = validate_horizontal_well(frame, well_id)
    first_idx = None
    last_idx = None
    if "TVT_input" in frame.columns:
        missing = frame["TVT_input"].isna()
        if missing.any():
            indices = frame.index[missing].astype(int)
            first_idx = int(indices.min())
            last_idx = int(indices.max())

    rows_reordered = False
    if "MD" in frame.columns and not frame.empty:
        sorted_index = frame.sort_values("MD", kind="mergesort").index.to_numpy()
        rows_reordered = not np.array_equal(frame.index.to_numpy(), sorted_index)

    response = ValidateResponse(
        valid=bool(result.ok),
        well_id=well_id,
        total_rows=int(result.n_rows),
        known_rows=int(result.n_known),
        prediction_rows=int(result.n_prediction),
        first_prediction_original_index=first_idx,
        last_prediction_original_index=last_idx,
        rows_reordered_for_processing=bool(rows_reordered),
        warnings=list(result.warnings),
        errors=list(result.errors),
    )
    return response


def raise_for_invalid_well(response: ValidateResponse) -> None:
    """Raise a structured ApiError when validation failed."""

    if response.valid:
        return
    message = response.errors[0] if response.errors else "Well validation failed."
    code = map_validation_message(message)
    raise ApiError(
        code,
        message,
        details={
            "well_id": response.well_id,
            "errors": response.errors,
        },
    )
