"""Golden regression tests against frozen fixtures and artifacts/v1."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from rogii_geo.inference.service import WellInferenceService

PROJECT_ROOT = Path(__file__).resolve().parents[1]
FIXTURES = Path(__file__).resolve().parent / "fixtures"
REAL_ARTIFACTS = PROJECT_ROOT / "artifacts"
REAL_V1 = REAL_ARTIFACTS / "v1"

ATOL = 1e-6

STABLE_SUMMARY_KEYS = [
    "well_id",
    "model_version",
    "selected_model",
    "total_rows",
    "known_rows",
    "prediction_rows",
    "feature_count",
    "required_predictors",
    "prediction_min",
    "prediction_max",
    "prediction_mean",
    "prediction_std",
    "first_prediction_original_index",
    "last_prediction_original_index",
    "checksum_verification",
    "rows_reordered_internally",
    "package_version",
    "xgboost_loaded",
    "extra_trees_loaded",
]


pytestmark = pytest.mark.skipif(
    not REAL_V1.is_dir(),
    reason="artifacts/v1 not available for golden regression",
)


def _run_golden() -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    well = pd.read_csv(FIXTURES / "golden_well.csv")
    service = WellInferenceService.from_artifact_root(
        REAL_ARTIFACTS,
        model_version="v1",
        verify_checksums=True,
    )
    result = service.predict_dataframe(well, "golden01", input_file=FIXTURES / "golden_well.csv")
    return result.competition_output, result.full_well_output, result.summary


def test_golden_competition_output_matches():
    competition, _, _ = _run_golden()
    expected = pd.read_csv(FIXTURES / "golden_competition_output.csv")
    assert list(competition.columns) == ["id", "tvt"]
    assert competition["id"].tolist() == expected["id"].tolist()
    np.testing.assert_allclose(
        competition["tvt"].to_numpy(dtype=float),
        expected["tvt"].to_numpy(dtype=float),
        atol=ATOL,
        rtol=0.0,
    )


def test_golden_full_well_matches():
    _, full, _ = _run_golden()
    expected = pd.read_csv(FIXTURES / "golden_full_well_output.csv")
    assert len(full) == len(expected)
    assert full["prediction_source"].tolist() == expected["prediction_source"].tolist()
    np.testing.assert_allclose(
        full["predicted_tvt"].to_numpy(dtype=float),
        expected["predicted_tvt"].to_numpy(dtype=float),
        atol=ATOL,
        rtol=0.0,
    )
    # Original columns preserved in order.
    for col in pd.read_csv(FIXTURES / "golden_well.csv").columns:
        if pd.api.types.is_numeric_dtype(expected[col]):
            np.testing.assert_allclose(
                full[col].to_numpy(dtype=float),
                expected[col].to_numpy(dtype=float),
                atol=ATOL,
                equal_nan=True,
            )
        else:
            assert full[col].tolist() == expected[col].tolist()


def test_golden_summary_stable_fields():
    _, _, summary = _run_golden()
    expected = json.loads((FIXTURES / "golden_prediction_summary.json").read_text(encoding="utf-8"))
    for key in STABLE_SUMMARY_KEYS:
        actual = summary[key]
        want = expected[key]
        if isinstance(want, float):
            assert actual == pytest.approx(want, abs=ATOL)
        else:
            assert actual == want


def test_golden_repeat_execution_identical():
    c1, f1, s1 = _run_golden()
    c2, f2, s2 = _run_golden()
    assert c1["id"].tolist() == c2["id"].tolist()
    np.testing.assert_allclose(c1["tvt"], c2["tvt"], atol=0.0, rtol=0.0)
    np.testing.assert_allclose(f1["predicted_tvt"], f2["predicted_tvt"], atol=0.0, rtol=0.0)
    for key in STABLE_SUMMARY_KEYS:
        if isinstance(s1[key], float):
            assert s1[key] == pytest.approx(s2[key], abs=0.0)
        else:
            assert s1[key] == s2[key]
