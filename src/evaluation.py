import time

import numpy as np
import pandas as pd

from sklearn.base import clone
from sklearn.metrics import mean_absolute_error, mean_squared_error


def evaluate_model(
    pipeline,
    X: pd.DataFrame,
    y: pd.Series,
    groups: pd.Series,
    cv,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Evaluate a regression pipeline using grouped cross-validation.
    """

    fold_metrics = []
    prediction_frames = []

    for fold, (train_idx, valid_idx) in enumerate(
        cv.split(X, y, groups),
        start=1,
    ):
        X_train = X.iloc[train_idx]
        X_valid = X.iloc[valid_idx]

        y_train = y.iloc[train_idx]
        y_valid = y.iloc[valid_idx]

        model = clone(pipeline)
        model.fit(X_train, y_train)

        y_pred = model.predict(X_valid)

        rmse = np.sqrt(
            mean_squared_error(
                y_valid,
                y_pred,
            )
        )

        mae = mean_absolute_error(
            y_valid,
            y_pred,
        )

        fold_metrics.append({
            "fold": fold,
            "rmse": rmse,
            "mae": mae,
        })

        prediction_frames.append(
            pd.DataFrame({
                "fold": fold,
                "well_id": groups.iloc[valid_idx].values,
                "actual_tvt": y_valid.values,
                "predicted_tvt": y_pred,
            })
        )

        print(
            f"Fold {fold} | "
            f"RMSE = {rmse:.2f} | "
            f"MAE = {mae:.2f}"
        )

    fold_results = pd.DataFrame(fold_metrics)

    predictions = pd.concat(
        prediction_frames,
        ignore_index=True,
    )

    return fold_results, predictions


def evaluate_development_split(
    pipeline,
    X_train: pd.DataFrame,
    y_train: pd.Series,
    X_validation: pd.DataFrame,
    y_validation: pd.Series,
    validation_groups: pd.Series,
    model_name: str,
) -> tuple[dict, pd.DataFrame, object]:
    """
    Train and evaluate a regression pipeline using one development split.
    """

    model = clone(pipeline)

    training_start = time.perf_counter()

    model.fit(
        X_train,
        y_train,
    )

    training_seconds = (
        time.perf_counter() - training_start
    )

    prediction_start = time.perf_counter()

    y_pred = model.predict(X_validation)

    prediction_seconds = (
        time.perf_counter() - prediction_start
    )

    rmse = np.sqrt(
        mean_squared_error(
            y_validation,
            y_pred,
        )
    )

    mae = mean_absolute_error(
        y_validation,
        y_pred,
    )

    metrics = {
        "model": model_name,
        "rmse": rmse,
        "mae": mae,
        "training_seconds": training_seconds,
        "prediction_seconds": prediction_seconds,
        "validation_rows": len(X_validation),
        "validation_wells": validation_groups.nunique(),
    }

    predictions = pd.DataFrame({
        "well_id": validation_groups.to_numpy(),
        "actual_tvt": y_validation.to_numpy(),
        "predicted_tvt": y_pred,
        "model": model_name,
    })

    print(
        f"{model_name} | "
        f"RMSE = {rmse:.2f} | "
        f"MAE = {mae:.2f} | "
        f"Training = {training_seconds:.2f}s"
    )

    return metrics, predictions, model


def calculate_well_level_metrics(
    predictions: pd.DataFrame,
    model_name: str,
) -> pd.DataFrame:
    """
    Calculate RMSE and MAE separately for every validation well.
    """

    well_results = []

    for well_id, well_df in predictions.groupby("well_id"):
        rmse = np.sqrt(
            mean_squared_error(
                well_df["actual_tvt"],
                well_df["predicted_tvt"],
            )
        )

        mae = mean_absolute_error(
            well_df["actual_tvt"],
            well_df["predicted_tvt"],
        )

        well_results.append({
            "well_id": well_id,
            "model": model_name,
            "rmse": rmse,
            "mae": mae,
            "n_rows": len(well_df),
        })

    return pd.DataFrame(well_results)

    