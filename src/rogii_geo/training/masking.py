"""Trailing-mask simulation for residual training (training-only)."""

from __future__ import annotations

import numpy as np
import pandas as pd

from rogii_geo.constants import PRIMARY_SLOPE_WINDOW, SLOPE_WINDOWS
from rogii_geo.features.prefix import add_last_known_and_slope_features
from rogii_geo.features.prepare import prepare_well_frame
from rogii_geo.training.config import (
    MAX_HIDDEN_ROWS_PER_MASK,
    MAX_MASKS_PER_WELL,
    MIN_HIDDEN_ROWS,
    MIN_KNOWN_ROWS,
)


def find_natural_cut(sorted_df: pd.DataFrame) -> int | None:
    """Return first trailing-missing index when the boundary is clean."""

    if "TVT_input" not in sorted_df.columns:
        return None
    missing = sorted_df["TVT_input"].isna().to_numpy()
    if not missing.any():
        return None
    first = int(np.argmax(missing))
    if missing[first:].all() and (~missing[:first]).all():
        return first
    return None


def choose_cut(
    n_rows: int,
    natural_cut: int | None,
    test_fractions: list[float],
    rng: np.random.Generator,
    *,
    min_known_rows: int = MIN_KNOWN_ROWS,
    min_hidden_rows: int = MIN_HIDDEN_ROWS,
    max_masks_per_well: int = MAX_MASKS_PER_WELL,
) -> tuple[str, int, float] | None:
    """Select one deterministic-ish cut candidate (max_masks_per_well = 1 by default)."""

    candidates: list[tuple[str, int, float]] = []

    def try_add(name: str, cut: int) -> None:
        if cut < min_known_rows or (n_rows - cut) < min_hidden_rows:
            return
        candidates.append((name, cut, (n_rows - cut) / n_rows))

    if natural_cut is not None:
        try_add("natural", natural_cut)

    frac_pool = sorted(
        set(
            round(float(f), 4)
            for f in list(test_fractions) + [0.70, 0.75]
            if np.isfinite(f)
        )
    )
    # Preserve notebook behavior: shuffle then take unique cuts.
    frac_pool = list(frac_pool)
    rng.shuffle(frac_pool)
    for frac in frac_pool:
        cut = int(round(n_rows * (1.0 - frac)))
        cut = max(min_known_rows, min(cut, n_rows - min_hidden_rows))
        try_add(f"frac_{frac:.2f}", cut)
        if len(candidates) >= 4:
            break

    seen: set[int] = set()
    selected: list[tuple[str, int, float]] = []
    for item in candidates:
        if item[1] in seen:
            continue
        seen.add(item[1])
        selected.append(item)
        if len(selected) >= max_masks_per_well:
            break
    return selected[0] if selected else None


def subsample_hidden(hidden: pd.DataFrame, max_rows: int) -> pd.DataFrame:
    """Evenly spaced deterministic subsample of hidden rows."""

    if len(hidden) <= max_rows:
        return hidden
    idx = np.linspace(0, len(hidden) - 1, max_rows).astype(int)
    return hidden.iloc[idx].copy()


def build_masked_rows_for_well(
    horizontal_df: pd.DataFrame,
    well_id: str,
    test_fractions: list[float],
    rng: np.random.Generator,
    *,
    min_known_rows: int = MIN_KNOWN_ROWS,
    min_hidden_rows: int = MIN_HIDDEN_ROWS,
    max_masks_per_well: int = MAX_MASKS_PER_WELL,
    max_hidden_rows_per_mask: int = MAX_HIDDEN_ROWS_PER_MASK,
    slope_windows: list[int] | None = None,
    primary_slope_window: int = PRIMARY_SLOPE_WINDOW,
) -> tuple[pd.DataFrame, dict | None]:
    """
    Build masked hidden-row training examples for one well.

    Uses ``sim_TVT_input`` so slope / last-known features come only from the
    known prefix. Target residual uses actual ``TVT``.
    """

    if slope_windows is None:
        slope_windows = list(SLOPE_WINDOWS)

    feat = prepare_well_frame(horizontal_df, well_id)
    usable = feat["TVT"].notna() if "TVT" in feat.columns else pd.Series(False, index=feat.index)
    if int(usable.sum()) < (min_known_rows + min_hidden_rows):
        return pd.DataFrame(), None

    feat = feat.loc[usable].reset_index(drop=True)
    n_rows = len(feat)
    cut_info = choose_cut(
        n_rows,
        find_natural_cut(feat),
        test_fractions,
        rng,
        min_known_rows=min_known_rows,
        min_hidden_rows=min_hidden_rows,
        max_masks_per_well=max_masks_per_well,
    )
    if cut_info is None:
        return pd.DataFrame(), None

    mask_name, cut, hidden_frac = cut_info
    known_mask = np.zeros(n_rows, dtype=bool)
    known_mask[:cut] = True

    sim = feat.copy()
    sim["sim_TVT_input"] = np.nan
    sim.loc[known_mask, "sim_TVT_input"] = sim.loc[known_mask, "TVT"].to_numpy()
    slope_frame = add_last_known_and_slope_features(
        sim,
        known_mask,
        slope_windows=slope_windows,
        primary_window=primary_slope_window,
        tvt_source_column="sim_TVT_input",
    )

    hidden = slope_frame.loc[~known_mask].copy()
    ok = np.isfinite(hidden["TVT"].to_numpy(dtype=float)) & np.isfinite(
        hidden["linear_tvt_projection"].to_numpy(dtype=float)
    )
    hidden = subsample_hidden(hidden.loc[ok], max_hidden_rows_per_mask)
    if hidden.empty:
        return pd.DataFrame(), None

    hidden = hidden.copy()
    hidden["well_id"] = well_id
    hidden["mask_id"] = f"{well_id}__{mask_name}"
    hidden["actual_tvt"] = hidden["TVT"].astype(float)
    hidden["residual_target"] = (
        hidden["actual_tvt"] - hidden["linear_tvt_projection"].astype(float)
    )
    hidden["group_id"] = well_id

    summary = {
        "well_id": well_id,
        "mask_name": mask_name,
        "known_rows": int(cut),
        "hidden_rows": int(len(hidden)),
        "hidden_fraction": float(hidden_frac),
        "n_rows_usable": int(n_rows),
    }
    return hidden, summary
