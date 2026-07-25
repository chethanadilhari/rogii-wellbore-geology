"""Validation metrics for masked residual training."""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error


def calculate_rmse(y_true, y_pred) -> float:
    return float(np.sqrt(mean_squared_error(y_true, y_pred)))


def calculate_validation_metrics(
    y_true,
    y_pred,
    well_ids,
    model_name: str,
) -> tuple[dict, pd.DataFrame]:
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    well_ids = np.asarray(well_ids)

    overall = {
        "model": model_name,
        "rmse": calculate_rmse(y_true, y_pred),
        "mae": float(mean_absolute_error(y_true, y_pred)),
        "n_rows": int(len(y_true)),
        "n_wells": int(pd.Series(well_ids).nunique()),
    }

    frame = pd.DataFrame({"well_id": well_ids, "y_true": y_true, "y_pred": y_pred})
    records = []
    for well_id, group in frame.groupby("well_id", sort=True):
        records.append(
            {
                "well_id": well_id,
                "model": model_name,
                "rmse": calculate_rmse(group["y_true"], group["y_pred"]),
                "mae": float(mean_absolute_error(group["y_true"], group["y_pred"])),
                "n_rows": int(len(group)),
            }
        )
    per_well = pd.DataFrame(records)
    overall["mean_well_rmse"] = float(per_well["rmse"].mean())
    overall["median_well_rmse"] = float(per_well["rmse"].median())
    overall["max_well_rmse"] = float(per_well["rmse"].max())
    return overall, per_well
