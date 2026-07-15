from pathlib import Path

import pandas as pd

from src.config import (
    PROCESSED_DIR,
    TEST_DIR,
    TRAIN_DIR,
)


# ==========================================================
# Training Well Discovery
# ==========================================================

def discover_training_wells(
    train_dir: Path = TRAIN_DIR,
) -> list[str]:
    """
    Discover complete training well pairs.
    """

    typewell_files = sorted(
        train_dir.glob("*__typewell.csv")
    )

    horizontal_files = sorted(
        train_dir.glob("*__horizontal_well.csv")
    )

    typewell_ids = {
        file.name.replace("__typewell.csv", "")
        for file in typewell_files
    }

    horizontal_ids = {
        file.name.replace("__horizontal_well.csv", "")
        for file in horizontal_files
    }

    return sorted(
        typewell_ids.intersection(horizontal_ids)
    )


# ==========================================================
# Test Well Discovery
# ==========================================================

def discover_test_wells(
    test_dir: Path = TEST_DIR,
) -> list[str]:
    """
    Discover all horizontal wells in the Kaggle test set.
    """

    horizontal_files = sorted(
        test_dir.glob("*__horizontal_well.csv")
    )

    return sorted(
        file.name.replace(
            "__horizontal_well.csv",
            ""
        )
        for file in horizontal_files
    )


# ==========================================================
# Training Data Loading
# ==========================================================

def load_typewell(
    well_id: str,
    train_dir: Path = TRAIN_DIR,
) -> pd.DataFrame:

    return pd.read_csv(
        train_dir / f"{well_id}__typewell.csv"
    )


def load_horizontal_well(
    well_id: str,
    train_dir: Path = TRAIN_DIR,
) -> pd.DataFrame:

    return pd.read_csv(
        train_dir / f"{well_id}__horizontal_well.csv"
    )


def load_training_pair(
    well_id: str,
    train_dir: Path = TRAIN_DIR,
):

    return (
        load_typewell(
            well_id,
            train_dir,
        ),
        load_horizontal_well(
            well_id,
            train_dir,
        ),
    )


# ==========================================================
# Test Data Loading
# ==========================================================

def load_test_horizontal_well(
    well_id: str,
    test_dir: Path = TEST_DIR,
) -> pd.DataFrame:

    return pd.read_csv(
        test_dir / f"{well_id}__horizontal_well.csv"
    )


# ==========================================================
# Processed Dataset Utilities
# ==========================================================

def save_processed_dataset(
    dataframe: pd.DataFrame,
    filename: str,
):

    path = PROCESSED_DIR / filename

    dataframe.to_csv(
        path,
        index=False,
    )

    print(f"Saved: {path}")


def load_processed_dataset(
    filename: str,
) -> pd.DataFrame:

    path = PROCESSED_DIR / filename

    return pd.read_csv(path)