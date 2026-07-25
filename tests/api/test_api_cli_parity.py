from __future__ import annotations

from io import BytesIO
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.api.config import Settings
from app.api.main import create_app
from rogii_geo.inference.service import WellInferenceService

PROJECT_ROOT = Path(__file__).resolve().parents[2]
FIXTURES = PROJECT_ROOT / "tests" / "fixtures"
REAL_ARTIFACTS = PROJECT_ROOT / "artifacts"
REAL_V1 = REAL_ARTIFACTS / "v1"

ATOL = 1e-6


@pytest.mark.skipif(not REAL_V1.is_dir(), reason="artifacts/v1 not available")
def test_api_matches_service_on_golden_fixture():
    settings = Settings(
        model_artifact_root=REAL_ARTIFACTS,
        model_version="v1",
        verify_artifact_checksums=True,
    )
    application = create_app(settings)
    well_path = FIXTURES / "golden_well.csv"
    content = well_path.read_bytes()

    service = WellInferenceService.from_artifact_root(
        REAL_ARTIFACTS,
        model_version="v1",
        verify_checksums=True,
    )
    well = pd.read_csv(well_path)
    expected = service.predict_dataframe(well, "golden01")

    with TestClient(application) as client:
        response = client.post(
            "/predict",
            files={"file": ("golden01__horizontal_well.csv", BytesIO(content), "text/csv")},
        )
        assert response.status_code == 200
        api = pd.read_csv(BytesIO(response.content))

    assert len(api) == len(expected.competition_output)
    assert api["id"].tolist() == expected.competition_output["id"].tolist()
    np.testing.assert_allclose(
        api["tvt"].to_numpy(dtype=float),
        expected.competition_output["tvt"].to_numpy(dtype=float),
        atol=ATOL,
        rtol=0.0,
    )

    # Frozen golden competition fixture
    golden = pd.read_csv(FIXTURES / "golden_competition_output.csv")
    assert api["id"].tolist() == golden["id"].tolist()
    np.testing.assert_allclose(api["tvt"], golden["tvt"], atol=ATOL, rtol=0.0)


@pytest.mark.skipif(not REAL_V1.is_dir(), reason="artifacts/v1 not available")
def test_api_full_well_matches_service():
    settings = Settings(
        model_artifact_root=REAL_ARTIFACTS,
        model_version="v1",
        verify_artifact_checksums=True,
    )
    application = create_app(settings)
    well_path = FIXTURES / "golden_well.csv"
    content = well_path.read_bytes()
    well = pd.read_csv(well_path)
    service = WellInferenceService.from_artifact_root(
        REAL_ARTIFACTS, model_version="v1", verify_checksums=True
    )
    expected = service.predict_dataframe(well, "golden01")

    with TestClient(application) as client:
        response = client.post(
            "/predict/full-well",
            files={"file": ("golden01__horizontal_well.csv", BytesIO(content), "text/csv")},
        )
        assert response.status_code == 200
        api = pd.read_csv(BytesIO(response.content))

    assert len(api) == len(expected.full_well_output)
    np.testing.assert_allclose(
        api["predicted_tvt"],
        expected.full_well_output["predicted_tvt"],
        atol=ATOL,
        rtol=0.0,
    )
    assert api["prediction_source"].tolist() == expected.full_well_output["prediction_source"].tolist()
