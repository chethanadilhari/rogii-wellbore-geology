"""Production training defaults from FinalProductionCandidate notebook/metadata."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from rogii_geo.constants import (
    PRIMARY_SLOPE_WINDOW,
    PRODUCTION_ALPHA_LAST_KNOWN,
    PRODUCTION_SELECTED_MODEL,
    PRODUCTION_WEIGHT_EXTRA_TREES,
    PRODUCTION_WEIGHT_XGBOOST,
    SLOPE_WINDOWS,
)

SOURCE_NOTEBOOK = "final_ensemble_residual_kaggle_submission.ipynb"
SCHEMA_VERSION = "v1_residual_trailing_mask"

RANDOM_STATE = 42
MAX_HIDDEN_ROWS_PER_MASK = 400
MODEL_FIT_MAX_ROWS = 150_000
MAX_MASKS_PER_WELL = 1
MIN_KNOWN_ROWS = 50
MIN_HIDDEN_ROWS = 20
VAL_TEST_SIZE = 0.20
DEFAULT_TEST_MISSING_FRACTIONS = [0.70, 0.75]
MISSING_MEDIAN_FALLBACK = 0.0

ET_PARAMS: dict[str, Any] = {
    "n_estimators": 150,
    "max_depth": 20,
    "min_samples_leaf": 25,
    "bootstrap": True,
    "max_samples": 0.20,
    "random_state": RANDOM_STATE,
    "n_jobs": -1,
}

XGB_PARAMS: dict[str, Any] = {
    "objective": "reg:squarederror",
    "n_estimators": 500,
    "learning_rate": 0.05,
    "max_depth": 8,
    "min_child_weight": 20,
    "subsample": 0.50,
    "colsample_bytree": 0.80,
    "reg_alpha": 0.10,
    "reg_lambda": 1.00,
    "tree_method": "hist",
    "max_bin": 256,
    "random_state": RANDOM_STATE,
    "n_jobs": -1,
    "verbosity": 0,
}


@dataclass
class TrainingConfig:
    """Runtime training configuration (CLI overrides applied here)."""

    random_state: int = RANDOM_STATE
    max_hidden_rows_per_mask: int = MAX_HIDDEN_ROWS_PER_MASK
    model_fit_max_rows: int = MODEL_FIT_MAX_ROWS
    max_masks_per_well: int = MAX_MASKS_PER_WELL
    min_known_rows: int = MIN_KNOWN_ROWS
    min_hidden_rows: int = MIN_HIDDEN_ROWS
    val_test_size: float = VAL_TEST_SIZE
    primary_slope_window: int = PRIMARY_SLOPE_WINDOW
    slope_windows: list[int] = field(default_factory=lambda: list(SLOPE_WINDOWS))
    test_missing_fractions: list[float] = field(
        default_factory=lambda: list(DEFAULT_TEST_MISSING_FRACTIONS)
    )
    include_optional_extra_trees: bool = False
    selected_model: str = PRODUCTION_SELECTED_MODEL
    alpha_last_known: float = PRODUCTION_ALPHA_LAST_KNOWN
    weight_extra_trees: float = PRODUCTION_WEIGHT_EXTRA_TREES
    weight_xgboost: float = PRODUCTION_WEIGHT_XGBOOST
    xgb_params: dict[str, Any] = field(default_factory=lambda: dict(XGB_PARAMS))
    et_params: dict[str, Any] = field(default_factory=lambda: dict(ET_PARAMS))
    missing_median_fallback: float = MISSING_MEDIAN_FALLBACK

    def with_random_state(self, random_state: int) -> "TrainingConfig":
        self.random_state = int(random_state)
        self.xgb_params = dict(self.xgb_params)
        self.et_params = dict(self.et_params)
        self.xgb_params["random_state"] = self.random_state
        self.et_params["random_state"] = self.random_state
        return self
