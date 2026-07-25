"""One-well inference feature preparation (no model fitting)."""

from __future__ import annotations

import pandas as pd

from rogii_geo.constants import PRIMARY_SLOPE_WINDOW, SLOPE_WINDOWS
from rogii_geo.features.prefix import add_last_known_and_slope_features
from rogii_geo.features.prepare import prepare_well_frame
from rogii_geo.validation.well import validate_horizontal_well


def build_inference_features(
    horizontal_df: pd.DataFrame,
    well_id: str,
    *,
    validate: bool = True,
) -> tuple[pd.DataFrame, pd.Series]:
    """
    Prepare a fully featured well frame and known-mask for inference.

    Returns
    -------
    feat : DataFrame
        MD-sorted engineered features including last-known / projections.
    known_mask : Series[bool]
        True where ``TVT_input`` is present.
    """

    if validate:
        result = validate_horizontal_well(horizontal_df, well_id)
        if not result.ok:
            raise ValueError(
                f"Well {well_id} failed validation: " + "; ".join(result.errors)
            )

    feat = prepare_well_frame(horizontal_df, well_id)
    known_mask = feat["TVT_input"].notna()
    feat = add_last_known_and_slope_features(
        feat,
        known_mask.to_numpy(),
        slope_windows=SLOPE_WINDOWS,
        primary_window=PRIMARY_SLOPE_WINDOW,
        tvt_source_column="TVT_input",
    )
    return feat, known_mask
