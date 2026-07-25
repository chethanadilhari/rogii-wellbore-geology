"""Known-prefix last-known / slope / linear-projection features."""

from __future__ import annotations

import numpy as np
import pandas as pd

from rogii_geo.constants import PRIMARY_SLOPE_WINDOW, SLOPE_WINDOWS


def _safe_polyfit_slope(md_values: np.ndarray, tvt_values: np.ndarray) -> float:
    if len(md_values) < 2 or np.unique(md_values).size < 2:
        return 0.0
    try:
        slope, _ = np.polyfit(md_values, tvt_values, 1)
        return float(slope) if np.isfinite(slope) else 0.0
    except Exception:
        return 0.0


def compute_slope_from_known(known_md, known_tvt, window: int) -> float:
    if len(known_md) == 0:
        return 0.0
    take = min(window, len(known_md))
    return _safe_polyfit_slope(known_md[-take:], known_tvt[-take:])


def add_last_known_and_slope_features(
    sorted_df: pd.DataFrame,
    known_mask,
    slope_windows=None,
    primary_window: int = PRIMARY_SLOPE_WINDOW,
    tvt_source_column: str = "TVT_input",
) -> pd.DataFrame:
    """
    Attach last-known TVT/MD and multi-window linear projections from the known prefix.

    Features for hidden rows must never use future / hidden-row TVT values.
    """

    if slope_windows is None:
        slope_windows = SLOPE_WINDOWS

    df = sorted_df.copy()
    known_mask = np.asarray(known_mask, dtype=bool)
    known_md = df.loc[known_mask, "MD"].to_numpy(dtype=float)
    known_tvt = df.loc[known_mask, tvt_source_column].to_numpy(dtype=float)
    valid = np.isfinite(known_md) & np.isfinite(known_tvt)
    known_md = known_md[valid]
    known_tvt = known_tvt[valid]

    if len(known_tvt) == 0:
        last_known_tvt = np.nan
        last_known_md = np.nan
        first_known_md = np.nan
    else:
        last_known_tvt = float(known_tvt[-1])
        last_known_md = float(known_md[-1])
        first_known_md = float(known_md[0])

    slopes = {w: compute_slope_from_known(known_md, known_tvt, w) for w in slope_windows}
    primary_slope = slopes.get(primary_window, 0.0)
    slope_values = np.array(list(slopes.values()), dtype=float)

    df["last_known_tvt"] = last_known_tvt
    df["last_known_md"] = last_known_md
    df["distance_from_last_known_md"] = df["MD"] - last_known_md
    df["known_tvt_count"] = float(len(known_tvt))
    df["known_fraction"] = float(len(known_tvt) / len(df)) if len(df) else 0.0
    df["md_relative_to_first_known"] = df["MD"] - first_known_md
    df["distance_beyond_known_interval"] = np.maximum(df["MD"] - last_known_md, 0.0)

    for window, slope in slopes.items():
        df[f"tvt_slope_w{window}"] = slope
        df[f"linear_proj_w{window}"] = last_known_tvt + slope * (df["MD"] - last_known_md)

    df["recent_tvt_slope"] = primary_slope
    df["linear_tvt_projection"] = last_known_tvt + primary_slope * (df["MD"] - last_known_md)
    df["slope_mean"] = float(np.mean(slope_values)) if len(slope_values) else 0.0
    df["slope_std"] = float(np.std(slope_values)) if len(slope_values) else 0.0
    df["slope_median"] = float(np.median(slope_values)) if len(slope_values) else 0.0
    if len(slope_windows) >= 2:
        df["slope_long_minus_short"] = slopes[max(slope_windows)] - slopes[min(slope_windows)]
    else:
        df["slope_long_minus_short"] = 0.0
    return df
