from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.api.config import Settings
from app.api.main import create_app


def test_health_ok(client: TestClient):
    response = client.get("/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "healthy"
    assert payload["model_loaded"] is True
    assert payload["model_version"] == "v_api"
    assert payload["selected_model"] == "blend_lastknown_0.70_ensemble"
    assert "X-Request-ID" in response.headers


def test_health_503_when_service_cleared(api_settings: Settings):
    application = create_app(api_settings)
    with TestClient(application) as client:
        client.app.state.inference_service = None
        response = client.get("/health")
        assert response.status_code == 503
        body = response.json()
        assert body["error"]["code"] == "MODEL_UNAVAILABLE"


def test_startup_fails_when_artifacts_missing(tmp_path: Path):
    settings = Settings(
        model_artifact_root=tmp_path / "missing_artifacts",
        model_version="v_missing",
        verify_artifact_checksums=True,
    )
    application = create_app(settings)
    with pytest.raises(Exception):
        with TestClient(application):
            pass
