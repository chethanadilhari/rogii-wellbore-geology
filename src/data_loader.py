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


def discover_test_well_pairs(
    test_dir: Path = TEST_DIR,
) -> list[str]:
    """
    Discover complete Kaggle test well pairs.

    A clear error is raised when a typewell or horizontal-well file is
    missing, because inference must not silently skip an incomplete well.
    """

    typewell_ids = {
        file.name.replace("__typewell.csv", "")
        for file in test_dir.glob("*__typewell.csv")
    }

    horizontal_ids = {
        file.name.replace("__horizontal_well.csv", "")
        for file in test_dir.glob("*__horizontal_well.csv")
    }

    if not typewell_ids and not horizontal_ids:
        raise FileNotFoundError(
            f"No Kaggle test well files were found in {test_dir}."
        )

    missing_typewells = sorted(horizontal_ids - typewell_ids)
    missing_horizontal_wells = sorted(typewell_ids - horizontal_ids)

    if missing_typewells or missing_horizontal_wells:
        raise ValueError(
            "Incomplete Kaggle test well pairs. "
            f"Missing typewells: {missing_typewells}; "
            "missing horizontal wells: "
            f"{missing_horizontal_wells}."
        )

    return sorted(typewell_ids)


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


def load_test_typewell(
    well_id: str,
    test_dir: Path = TEST_DIR,
) -> pd.DataFrame:

    return pd.read_csv(
        test_dir / f"{well_id}__typewell.csv"
    )


def load_test_pair(
    well_id: str,
    test_dir: Path = TEST_DIR,
) -> tuple[pd.DataFrame, pd.DataFrame]:

    return (
        load_test_typewell(
            well_id,
            test_dir,
        ),
        load_test_horizontal_well(
            well_id,
            test_dir,
        ),
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