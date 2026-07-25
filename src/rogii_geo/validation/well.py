"""Well schema and prediction-boundary validation."""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from rogii_geo.constants import REQUIRED_HORIZONTAL_COLUMNS


@dataclass
class ValidationResult:
    """Outcome of validating one uploaded horizontal well CSV."""

    ok: bool
    well_id: str
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    n_rows: int = 0
    n_known: int = 0
    n_prediction: int = 0


def identify_prediction_sections(horizontal_df: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    """Return (known_mask, prediction_mask) from ``TVT_input`` nullability."""

    if "TVT_input" not in horizontal_df.columns:
        raise ValueError("Column TVT_input is required.")
    known_mask = horizontal_df["TVT_input"].notna().to_numpy(dtype=bool)
    prediction_mask = ~known_mask
    return known_mask, prediction_mask


def has_clean_prediction_boundary(horizontal_df: pd.DataFrame) -> bool:
    """
    True when, after MD sort, all known rows precede all missing ``TVT_input`` rows.

    This is the competition trailing-mask invariant validated on all training wells.
    """

    if "TVT_input" not in horizontal_df.columns or "MD" not in horizontal_df.columns:
        return False
    if horizontal_df.empty:
        return False

    sorted_df = horizontal_df.sort_values("MD", kind="mergesort")
    missing = sorted_df["TVT_input"].isna().to_numpy(dtype=bool)
    if not missing.any():
        return True
    if missing.all():
        return False
    first = int(np.argmax(missing))
    return bool(missing[first:].all() and (~missing[:first]).all())


def validate_horizontal_well(
    horizontal_df: pd.DataFrame,
    well_id: str,
    *,
    require_prediction_rows: bool = True,
) -> ValidationResult:
    """Validate schema and trailing-boundary rules before prediction."""

    errors: list[str] = []
    warnings: list[str] = []

    if horizontal_df is None or horizontal_df.empty:
        return ValidationResult(
            ok=False,
            well_id=well_id,
            errors=["Well CSV is empty."],
        )

    if horizontal_df.columns.duplicated().any():
        duplicates = horizontal_df.columns[horizontal_df.columns.duplicated()].tolist()
        errors.append(f"Duplicate column names: {duplicates}")

    missing_cols = [c for c in REQUIRED_HORIZONTAL_COLUMNS if c not in horizontal_df.columns]
    if missing_cols:
        errors.append(f"Missing required columns: {missing_cols}")

    if "MD" in horizontal_df.columns:
        md = pd.to_numeric(horizontal_df["MD"], errors="coerce")
        if md.isna().all():
            errors.append("Column MD is entirely missing or non-numeric.")
        elif md.isna().any():
            errors.append("Column MD contains invalid (missing or non-numeric) values.")

    n_rows = int(len(horizontal_df))
    n_known = 0
    n_prediction = 0

    if "TVT_input" in horizontal_df.columns:
        known_mask, prediction_mask = identify_prediction_sections(horizontal_df)
        n_known = int(known_mask.sum())
        n_prediction = int(prediction_mask.sum())

        if n_known == 0:
            errors.append("No known-prefix rows (TVT_input is entirely missing).")
        if n_prediction == 0 and require_prediction_rows:
            errors.append("No prediction rows (TVT_input has no missing values).")
        if not has_clean_prediction_boundary(horizontal_df):
            errors.append(
                "Prediction boundary is not a clean trailing mask "
                "(known prefix then all-missing suffix)."
            )

    formation_missing = [
        c for c in ["ANCC", "ASTNU", "ASTNL", "EGFDU", "EGFDL", "BUDA"] if c not in horizontal_df.columns
    ]
    if formation_missing:
        warnings.append(
            f"Formation marker columns absent and will be median-filled: {formation_missing}"
        )

    if horizontal_df.index.duplicated().any():
        warnings.append("Duplicate index values present; original_row_index uses the frame index.")

    return ValidationResult(
        ok=len(errors) == 0,
        well_id=well_id,
        errors=errors,
        warnings=warnings,
        n_rows=n_rows,
        n_known=n_known,
        n_prediction=n_prediction,
    )
