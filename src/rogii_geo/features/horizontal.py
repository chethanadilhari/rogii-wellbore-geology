"""Horizontal-well feature engineering from the FinalProductionCandidate notebook."""

from __future__ import annotations

import numpy as np
import pandas as pd

from rogii_geo.constants import RAW_HORIZONTAL_FEATURES, ROLLING_WINDOWS


def engineer_horizontal_features(
    horizontal_df: pd.DataFrame,
    well_id: str,
) -> pd.DataFrame:
    """
    Create row-level geometric / GR rolling features for one horizontal well.

    Preserves ``original_row_index`` through MD sort so competition IDs remain
    ``{well_id}_{original_row_index}``.
    """

    missing = [c for c in RAW_HORIZONTAL_FEATURES if c not in horizontal_df.columns]
    if missing:
        raise ValueError(f"Well {well_id} missing required columns: {missing}")

    df = horizontal_df.copy()
    df["original_row_index"] = df.index.astype(int)
    df["input_row_order"] = np.arange(len(df), dtype=int)
    df["well_id"] = well_id
    df = df.sort_values("MD", kind="mergesort").reset_index(drop=True)

    md0 = df["MD"].iloc[0]
    df["MD_relative"] = df["MD"] - md0
    md_range = float(df["MD"].iloc[-1] - md0)
    df["MD_normalized"] = df["MD_relative"] / md_range if md_range > 0 else 0.0

    df["X_relative"] = df["X"] - df["X"].iloc[0]
    df["Y_relative"] = df["Y"] - df["Y"].iloc[0]
    df["Z_relative"] = df["Z"] - df["Z"].iloc[0]

    for col in ["MD", "X", "Y", "Z", "GR"]:
        df[f"{col}_diff"] = df[col].diff()

    df["step_distance_3d"] = np.sqrt(
        df["X_diff"].fillna(0.0) ** 2
        + df["Y_diff"].fillna(0.0) ** 2
        + df["Z_diff"].fillna(0.0) ** 2
    )
    df["cumulative_trajectory_distance"] = df["step_distance_3d"].cumsum()
    df["horizontal_distance"] = np.sqrt(df["X_relative"] ** 2 + df["Y_relative"] ** 2)
    df["spatial_distance"] = np.sqrt(
        df["X_relative"] ** 2 + df["Y_relative"] ** 2 + df["Z_relative"] ** 2
    )

    for window in ROLLING_WINDOWS:
        roll = df["GR"].rolling(window=window, min_periods=1)
        df[f"GR_roll_mean_{window}"] = roll.mean()
        df[f"GR_roll_std_{window}"] = roll.std()
        df[f"GR_dev_from_roll_mean_{window}"] = df["GR"] - df[f"GR_roll_mean_{window}"]

    with np.errstate(divide="ignore", invalid="ignore"):
        df["dz_dmd"] = df["Z_diff"] / df["MD_diff"].replace(0, np.nan)

    return df
