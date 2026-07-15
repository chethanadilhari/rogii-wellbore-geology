from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
TRAIN_DIR = RAW_DIR / "train"
TEST_DIR = RAW_DIR / "test"
PROCESSED_DIR = DATA_DIR / "processed"

MODELS_DIR = PROJECT_ROOT / "models"
RESULTS_DIR = PROJECT_ROOT / "results"

NOTEBOOK_05_RESULTS_DIR = RESULTS_DIR / "notebook_05"
NOTEBOOK_05_MODELS_DIR = MODELS_DIR / "notebook_05"

NOTEBOOK_06_RESULTS_DIR = RESULTS_DIR / "notebook_06"
NOTEBOOK_06_MODELS_DIR = MODELS_DIR / "notebook_06"


def create_project_directories():
    """
    Create project output directories if they do not already exist.
    """

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    NOTEBOOK_05_RESULTS_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    NOTEBOOK_05_MODELS_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    NOTEBOOK_06_RESULTS_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    NOTEBOOK_06_MODELS_DIR.mkdir(
        parents=True,
        exist_ok=True
    )