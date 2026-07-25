"""Assemble a model-ready well frame from a raw horizontal CSV dataframe."""

from __future__ import annotations

import numpy as np
import pandas as pd

from rogii_geo.constants import FORMATION_COLUMNS
from rogii_geo.features.horizontal import engineer_horizontal_features


def prepare_well_frame(horizontal_df: pd.DataFrame, well_id: str) -> pd.DataFrame:
    """
    Engineer horizontal features and re-attach TVT / formation columns in MD order.

    Mirrors ``prepare_well_frame`` in final_ensemble_residual_kaggle_submission.ipynb.
    """

    raw = horizontal_df.copy()
    raw["original_row_index"] = raw.index.astype(int)
    feat = engineer_horizontal_features(raw, well_id)
    raw_sorted = raw.sort_values("MD", kind="mergesort").reset_index(drop=True)
    for col in ["TVT_input", "TVT"] + FORMATION_COLUMNS:
        if col in raw_sorted.columns:
            feat[col] = raw_sorted[col].to_numpy()
        elif col not in feat.columns:
            feat[col] = np.nan
    return feat
