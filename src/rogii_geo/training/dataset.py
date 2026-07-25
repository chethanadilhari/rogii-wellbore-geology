"""Build masked training / validation datasets with well-grouped splits."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.model_selection import GroupShuffleSplit

from rogii_geo.constants import META_COLUMNS
from rogii_geo.features.columns import infer_feature_columns
from rogii_geo.training.config import TrainingConfig
from rogii_geo.training.discovery import build_horizontal_registry, load_horizontal_csv
from rogii_geo.training.masking import build_masked_rows_for_well


@dataclass
class MaskedDatasets:
    train_df: pd.DataFrame
    val_df: pd.DataFrame
    feature_columns: list[str]
    train_well_ids: list[str]
    val_well_ids: list[str]
    mask_summary: pd.DataFrame
    dataset_summary: pd.DataFrame


def split_wells(
    well_ids: list[str],
    *,
    test_size: float,
    random_state: int,
) -> tuple[list[str], list[str]]:
    """GroupShuffleSplit on well IDs (one row per well)."""

    frame = pd.DataFrame({"well_id": well_ids})
    splitter = GroupShuffleSplit(
        n_splits=1,
        test_size=test_size,
        random_state=random_state,
    )
    train_idx, val_idx = next(
        splitter.split(frame, groups=frame["well_id"])
    )
    train_wells = frame.iloc[train_idx]["well_id"].tolist()
    val_wells = frame.iloc[val_idx]["well_id"].tolist()
    overlap = set(train_wells) & set(val_wells)
    if overlap:
        raise RuntimeError(f"Well leakage in split: {sorted(overlap)[:5]}")
    return train_wells, val_wells


def build_dataset_for_wells(
    well_ids: list[str],
    registry: pd.DataFrame,
    config: TrainingConfig,
    *,
    rng_seed: int,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return (masked_rows, mask_summary) for the given wells."""

    rng = np.random.default_rng(rng_seed)
    frames: list[pd.DataFrame] = []
    summaries: list[dict] = []

    path_map = {
        row.well_id: row.horizontal_path
        for row in registry.itertuples(index=False)
    }

    for well_id in well_ids:
        path = path_map.get(well_id)
        if path is None:
            continue
        horizontal_df = load_horizontal_csv(path)
        hidden, summary = build_masked_rows_for_well(
            horizontal_df,
            well_id,
            config.test_missing_fractions,
            rng,
            min_known_rows=config.min_known_rows,
            min_hidden_rows=config.min_hidden_rows,
            max_masks_per_well=config.max_masks_per_well,
            max_hidden_rows_per_mask=config.max_hidden_rows_per_mask,
            slope_windows=config.slope_windows,
            primary_slope_window=config.primary_slope_window,
        )
        if summary is not None and not hidden.empty:
            frames.append(hidden)
            summaries.append(summary)

    if not frames:
        return pd.DataFrame(), pd.DataFrame()

    return pd.concat(frames, ignore_index=True), pd.DataFrame(summaries)


def resolve_feature_columns(train_df: pd.DataFrame) -> list[str]:
    """Infer numeric feature columns and enforce required projection features."""

    columns = infer_feature_columns(train_df)
    for required in ["MD", "GR", "linear_tvt_projection", "last_known_tvt"]:
        if required in train_df.columns and required not in columns:
            columns.append(required)
    columns = sorted(set(columns))

    leaked = sorted(set(columns) & META_COLUMNS)
    # META already excludes TVT etc from infer; double-check forbidden names.
    forbidden = {
        "TVT",
        "TVT_input",
        "sim_TVT_input",
        "actual_tvt",
        "residual_target",
        "well_id",
        "mask_id",
        "group_id",
        "original_row_index",
    }
    leaked = sorted(set(columns) & forbidden)
    if leaked:
        raise ValueError(f"Feature leakage detected: {leaked}")
    return columns


def build_masked_datasets(
    train_dir,
    config: TrainingConfig,
) -> MaskedDatasets:
    """Full masked train/val construction with well-grouped split."""

    registry = build_horizontal_registry(train_dir)
    well_ids = registry["well_id"].tolist()
    train_wells, val_wells = split_wells(
        well_ids,
        test_size=config.val_test_size,
        random_state=config.random_state,
    )

    train_df, train_masks = build_dataset_for_wells(
        train_wells,
        registry,
        config,
        rng_seed=config.random_state,
    )
    val_df, val_masks = build_dataset_for_wells(
        val_wells,
        registry,
        config,
        rng_seed=config.random_state + 1,
    )

    if train_df.empty:
        raise RuntimeError(
            "No valid masked training rows could be produced from the training wells."
        )
    if val_df.empty:
        raise RuntimeError(
            "No valid masked validation rows could be produced from the validation wells."
        )

    feature_columns = resolve_feature_columns(train_df)
    mask_summary = pd.concat([train_masks, val_masks], ignore_index=True)
    if not mask_summary.empty:
        mask_summary["split"] = np.where(
            mask_summary["well_id"].isin(train_wells),
            "train",
            "val",
        )

    dataset_summary = pd.DataFrame(
        [
            {
                "split": "train",
                "n_wells": len(train_wells),
                "n_wells_with_masks": int(train_df["well_id"].nunique()),
                "n_rows": int(len(train_df)),
            },
            {
                "split": "val",
                "n_wells": len(val_wells),
                "n_wells_with_masks": int(val_df["well_id"].nunique()),
                "n_rows": int(len(val_df)),
            },
            {
                "split": "all_discovered",
                "n_wells": len(well_ids),
                "n_wells_with_masks": int(
                    pd.concat([train_df, val_df])["well_id"].nunique()
                ),
                "n_rows": int(len(train_df) + len(val_df)),
            },
        ]
    )

    return MaskedDatasets(
        train_df=train_df,
        val_df=val_df,
        feature_columns=feature_columns,
        train_well_ids=train_wells,
        val_well_ids=val_wells,
        mask_summary=mask_summary,
        dataset_summary=dataset_summary,
    )


def subsample_fit_rows(
    df: pd.DataFrame,
    max_rows: int,
    random_state: int,
) -> pd.DataFrame:
    """Deterministic row cap for model fitting."""

    if len(df) <= max_rows:
        return df
    return df.sample(n=int(max_rows), random_state=random_state)
