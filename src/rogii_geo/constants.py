"""Constants matching final_ensemble_residual_kaggle_submission.ipynb."""

from __future__ import annotations

RAW_HORIZONTAL_FEATURES = ["MD", "GR", "X", "Y", "Z"]

FORMATION_COLUMNS = ["ANCC", "ASTNU", "ASTNL", "EGFDU", "EGFDL", "BUDA"]

ROLLING_WINDOWS = [5, 11]

SLOPE_WINDOWS = [10, 25, 50]

PRIMARY_SLOPE_WINDOW = 50

REQUIRED_HORIZONTAL_COLUMNS = [
    "MD",
    "X",
    "Y",
    "Z",
    "GR",
    "TVT_input",
]

META_COLUMNS = {
    "well_id",
    "mask_id",
    "group_id",
    "original_row_index",
    "input_row_order",
    "actual_tvt",
    "residual_target",
    "TVT",
    "TVT_input",
    "sim_TVT_input",
}

# Production recipe frozen from results/ensemble_residual_submission metadata.
PRODUCTION_SELECTED_MODEL = "blend_lastknown_0.70_ensemble"
PRODUCTION_ALPHA_LAST_KNOWN = 0.70
PRODUCTION_WEIGHT_EXTRA_TREES = 0.0
PRODUCTION_WEIGHT_XGBOOST = 1.0
PRODUCTION_VALIDATION_RMSE = 16.97201957425067
