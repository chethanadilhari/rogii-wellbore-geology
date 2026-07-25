"""Feature-column inference matching the FinalProductionCandidate notebook."""

from __future__ import annotations

import pandas as pd

from rogii_geo.constants import META_COLUMNS


def infer_feature_columns(df: pd.DataFrame) -> list[str]:
    """Return sorted numeric columns excluding training meta / target columns."""

    cols: list[str] = []
    for col in df.columns:
        if col in META_COLUMNS:
            continue
        if pd.api.types.is_numeric_dtype(df[col]):
            cols.append(col)
    return sorted(set(cols))
