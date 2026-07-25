"""Prediction output formatters for competition and full-well workflows."""

from __future__ import annotations

import numpy as np
import pandas as pd


KNOWN_SOURCE = "known"
MODEL_SOURCE = "model"


def build_prediction_frame(
    feat: pd.DataFrame,
    known_mask: pd.Series | np.ndarray,
    predicted_tvt: np.ndarray,
    *,
    model_name: str,
) -> pd.DataFrame:
    """Build per-row prediction metadata for hidden rows in original-row order."""

    known_mask = np.asarray(known_mask, dtype=bool)
    pred_df = feat.loc[~known_mask].copy()
    if len(pred_df) != len(predicted_tvt):
        raise ValueError(
            f"Prediction length mismatch: {len(pred_df)} rows vs {len(predicted_tvt)} values"
        )

    pred_df = pred_df.assign(_pred_tvt=np.asarray(predicted_tvt, dtype=float))
    if "input_row_order" in pred_df.columns:
        pred_df = pred_df.sort_values("input_row_order", kind="mergesort")
    else:
        pred_df = pred_df.sort_values("original_row_index", kind="mergesort")

    well_id = str(pred_df["well_id"].iloc[0]) if "well_id" in pred_df.columns else "unknown"
    out = pd.DataFrame(
        {
            "id": [
                f"{well_id}_{int(idx)}"
                for idx in pred_df["original_row_index"].to_numpy()
            ],
            "well_id": well_id,
            "original_row_index": pred_df["original_row_index"].to_numpy(dtype=int),
            "MD": pred_df["MD"].to_numpy(dtype=float),
            "pred_last_known": pred_df["last_known_tvt"].to_numpy(dtype=float),
            "pred_linear": pred_df["linear_tvt_projection"].to_numpy(dtype=float),
            "tvt": pred_df["_pred_tvt"].to_numpy(dtype=float),
            "prediction_source": model_name,
        }
    )
    return out.reset_index(drop=True)


def build_competition_output(prediction_frame: pd.DataFrame) -> pd.DataFrame:
    """Competition submission format: only ``id,tvt`` for prediction rows."""

    out = prediction_frame[["id", "tvt"]].copy()
    out["id"] = out["id"].astype(str)
    out["tvt"] = out["tvt"].astype(float)
    if not np.isfinite(out["tvt"].to_numpy(dtype=float)).all():
        raise ValueError("Competition output contains non-finite tvt values.")
    return out.reset_index(drop=True)


def build_full_well_output(
    feat: pd.DataFrame,
    known_mask: pd.Series | np.ndarray,
    predicted_tvt: np.ndarray,
    *,
    model_name: str = MODEL_SOURCE,
) -> pd.DataFrame:
    """
    Full-well engineered frame plus ``predicted_tvt`` and source labels.

    Known rows use ``TVT_input`` with ``prediction_source='known'``.
    Hidden rows use model predictions with ``prediction_source='model'``.
    ``model_name`` is accepted for backward compatibility but sources follow
    the Phase 3 contract (``known`` / ``model``).
    """

    del model_name  # Phase 3 uses fixed known/model labels.
    known_mask = np.asarray(known_mask, dtype=bool)
    out = feat.copy()
    predicted = np.full(len(out), np.nan, dtype=float)
    sources = np.full(len(out), "", dtype=object)

    if known_mask.any():
        predicted[known_mask] = out.loc[known_mask, "TVT_input"].to_numpy(dtype=float)
        sources[known_mask] = KNOWN_SOURCE

    hidden = ~known_mask
    n_hidden = int(hidden.sum())
    if n_hidden != len(predicted_tvt):
        raise ValueError(
            f"Hidden row count {n_hidden} does not match predictions {len(predicted_tvt)}"
        )
    predicted[hidden] = np.asarray(predicted_tvt, dtype=float)
    sources[hidden] = MODEL_SOURCE

    out["predicted_tvt"] = predicted
    out["prediction_source"] = sources
    return out


def build_original_order_full_well(
    original_df: pd.DataFrame,
    feat: pd.DataFrame,
    known_mask: pd.Series | np.ndarray,
    predicted_tvt: np.ndarray,
) -> pd.DataFrame:
    """
    Restore predictions onto the original input columns and row order.

    Adds ``predicted_tvt`` and ``prediction_source`` only.
    """

    known_mask = np.asarray(known_mask, dtype=bool)
    hidden_feat = feat.loc[~known_mask]
    if len(hidden_feat) != len(predicted_tvt):
        raise ValueError(
            f"Hidden row count {len(hidden_feat)} does not match predictions "
            f"{len(predicted_tvt)}"
        )

    pred_by_index = pd.Series(
        np.asarray(predicted_tvt, dtype=float),
        index=hidden_feat["original_row_index"].to_numpy(dtype=int),
    )
    if pred_by_index.index.duplicated().any():
        raise ValueError("Duplicate original_row_index values among prediction rows.")

    out = original_df.copy()
    known = out["TVT_input"].notna()
    predicted = np.full(len(out), np.nan, dtype=float)
    sources = np.full(len(out), "", dtype=object)

    predicted[known.to_numpy()] = out.loc[known, "TVT_input"].to_numpy(dtype=float)
    sources[known.to_numpy()] = KNOWN_SOURCE

    missing_positions = (~known).to_numpy()
    missing_indices = out.index[missing_positions].astype(int)
    try:
        mapped = pred_by_index.loc[missing_indices].to_numpy(dtype=float)
    except KeyError as exc:
        raise KeyError(
            f"Missing model prediction for original_row_index values: {exc}"
        ) from exc
    predicted[missing_positions] = mapped
    sources[missing_positions] = MODEL_SOURCE

    out["predicted_tvt"] = predicted
    out["prediction_source"] = sources
    if not np.isfinite(out["predicted_tvt"].to_numpy(dtype=float)).all():
        raise ValueError("Full-well output contains non-finite predicted_tvt values.")
    return out
