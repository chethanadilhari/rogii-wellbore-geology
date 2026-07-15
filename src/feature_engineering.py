import numpy as np
import pandas as pd


DIRECT_FEATURES = [
    "MD",
    "GR",
    "TVT_input",
]

COORDINATE_FEATURES = [
    "X",
    "Y",
    "Z",
]

FORMATION_MARKER_FEATURES = [
    "ANCC",
    "ASTNU",
    "ASTNL",
    "EGFDU",
    "EGFDL",
    "BUDA",
]

RAW_FEATURES = (
    DIRECT_FEATURES
    + COORDINATE_FEATURES
    + FORMATION_MARKER_FEATURES
)

TARGET_COLUMN = "TVT"
GROUP_COLUMN = "well_id"


def create_horizontal_features(
    horizontal_df: pd.DataFrame,
    well_id: str,
) -> pd.DataFrame:
    """
    Create row-level machine-learning features for one horizontal well.
    """

    if horizontal_df.empty:
        raise ValueError(f"Horizontal well {well_id} is empty.")

    required_columns = [
        "MD",
        "X",
        "Y",
        "Z",
        "GR",
        "TVT_input",
    ]

    missing_columns = [
        column
        for column in required_columns
        if column not in horizontal_df.columns
    ]

    if missing_columns:
        raise ValueError(
            f"Well {well_id} is missing required columns: "
            f"{missing_columns}"
        )

    df = horizontal_df.copy()
    df = df.sort_values("MD").reset_index(drop=True)

    df[GROUP_COLUMN] = well_id

    df["MD_relative"] = df["MD"] - df["MD"].iloc[0]
    df["X_relative"] = df["X"] - df["X"].iloc[0]
    df["Y_relative"] = df["Y"] - df["Y"].iloc[0]
    df["Z_relative"] = df["Z"] - df["Z"].iloc[0]

    df["MD_diff"] = df["MD"].diff()
    df["X_diff"] = df["X"].diff()
    df["Y_diff"] = df["Y"].diff()
    df["Z_diff"] = df["Z"].diff()
    df["GR_diff"] = df["GR"].diff()
    df["TVT_input_diff"] = df["TVT_input"].diff()

    df["horizontal_distance"] = np.sqrt(
        df["X_relative"] ** 2
        + df["Y_relative"] ** 2
    )

    df["spatial_distance"] = np.sqrt(
        df["X_relative"] ** 2
        + df["Y_relative"] ** 2
        + df["Z_relative"] ** 2
    )

    return df