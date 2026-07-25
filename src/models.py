from collections.abc import Mapping, Sequence
from typing import Any

from sklearn.compose import ColumnTransformer
from sklearn.ensemble import (
    ExtraTreesRegressor,
    HistGradientBoostingRegressor,
    RandomForestRegressor,
)
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LinearRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from xgboost import XGBRegressor
from lightgbm import LGBMRegressor


def create_preprocessor(
    feature_columns: Sequence[str],
    scale_features: bool = True,
) -> ColumnTransformer:
    """
    Create the numeric preprocessing pipeline.
    """

    numeric_steps = [
        ("imputer", SimpleImputer(strategy="median")),
    ]

    if scale_features:
        numeric_steps.append(
            ("scaler", StandardScaler())
        )

    numeric_pipeline = Pipeline(
        steps=numeric_steps
    )

    return ColumnTransformer(
        transformers=[
            (
                "numeric",
                numeric_pipeline,
                list(feature_columns),
            )
        ]
    )


def create_linear_regression_pipeline(
    feature_columns: Sequence[str],
) -> Pipeline:
    """
    Create the Linear Regression pipeline.
    """

    preprocessor = create_preprocessor(
        feature_columns=feature_columns,
        scale_features=True,
    )

    return Pipeline(
        steps=[
            ("preprocessor", preprocessor),
            ("model", LinearRegression()),
        ]
    )


def create_random_forest_pipeline(
    feature_columns: Sequence[str],
) -> Pipeline:
    """
    Create a Random Forest pipeline suitable for the large dataset.
    """

    preprocessor = create_preprocessor(
        feature_columns=feature_columns,
        scale_features=False,
    )

    return Pipeline(
        steps=[
            ("preprocessor", preprocessor),
            (
                "model",
                RandomForestRegressor(
                    n_estimators=100,
                    max_depth=18,
                    min_samples_leaf=50,
                    max_samples=0.10,
                    random_state=42,
                    n_jobs=4,
                ),
            ),
        ]
    )

def create_hist_gradient_boosting_pipeline(
    feature_columns: Sequence[str],
) -> Pipeline:
    """
    Create a HistGradientBoosting pipeline suitable for large tabular data.
    """

    preprocessor = create_preprocessor(
        feature_columns=feature_columns,
        scale_features=False,
    )

    return Pipeline(
        steps=[
            ("preprocessor", preprocessor),
            (
                "model",
                HistGradientBoostingRegressor(
                    learning_rate=0.08,
                    max_iter=200,
                    max_leaf_nodes=31,
                    min_samples_leaf=50,
                    l2_regularization=1.0,
                    random_state=42,
                ),
            ),
        ]
    )

def create_extra_trees_pipeline(
    feature_columns: Sequence[str],
    model_params: Mapping[str, Any] | None = None,
) -> Pipeline:
    """
    Create a memory-conscious Extra Trees pipeline.

    Custom model parameters can be supplied for optimization trials.
    """

    preprocessor = create_preprocessor(
        feature_columns=feature_columns,
        scale_features=False,
    )

    default_params = {
        "n_estimators": 100,
        "max_depth": 18,
        "min_samples_leaf": 50,
        "bootstrap": True,
        "max_samples": 0.10,
        "random_state": 42,
        "n_jobs": 4,
    }

    if model_params is not None:
        default_params.update(model_params)

    return Pipeline(
        steps=[
            ("preprocessor", preprocessor),
            (
                "model",
                ExtraTreesRegressor(
                    **default_params
                ),
            ),
        ]
    )

def create_xgboost_pipeline(
    feature_columns: Sequence[str],
    model_params: Mapping[str, Any] | None = None,
) -> Pipeline:
    """
    Create a memory-conscious XGBoost regression pipeline.

    Custom model parameters can be supplied for optimization trials.
    """

    preprocessor = create_preprocessor(
        feature_columns=feature_columns,
        scale_features=False,
    )

    default_params = {
        "objective": "reg:squarederror",
        "n_estimators": 300,
        "learning_rate": 0.05,
        "max_depth": 8,
        "min_child_weight": 20,
        "subsample": 0.50,
        "colsample_bytree": 0.80,
        "reg_alpha": 0.10,
        "reg_lambda": 1.00,
        "tree_method": "hist",
        "max_bin": 256,
        "random_state": 42,
        "n_jobs": 4,
        "verbosity": 1,
    }

    if model_params is not None:
        default_params.update(model_params)

    return Pipeline(
        steps=[
            ("preprocessor", preprocessor),
            (
                "model",
                XGBRegressor(
                    **default_params
                ),
            ),
        ]
    )
    
    
def create_lightgbm_pipeline(
    feature_columns: Sequence[str],
) -> Pipeline:
    """
    Create a memory-conscious LightGBM regression pipeline.
    """

    preprocessor = create_preprocessor(
        feature_columns=feature_columns,
        scale_features=False,
    )

    return Pipeline(
        steps=[
            ("preprocessor", preprocessor),
            (
                "model",
                LGBMRegressor(
                    objective="regression",
                    n_estimators=300,
                    learning_rate=0.05,
                    num_leaves=31,
                    max_depth=10,
                    min_child_samples=100,
                    subsample=0.50,
                    subsample_freq=1,
                    colsample_bytree=0.80,
                    reg_alpha=0.10,
                    reg_lambda=1.00,
                    max_bin=255,
                    random_state=42,
                    n_jobs=4,
                    verbosity=-1,
                ),
            ),
        ]
    )
    