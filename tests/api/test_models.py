from __future__ import annotations

from fastapi.testclient import TestClient


def test_models_current_safe_metadata(client: TestClient):
    response = client.get("/models/current")
    assert response.status_code == 200
    payload = response.json()
    assert payload["model_version"] == "v_api"
    assert payload["selected_model"] == "blend_lastknown_0.70_ensemble"
    assert payload["feature_count"] == 4
    assert payload["required_predictors"] == ["last_known", "xgboost_residual"]
    assert "extra_trees_residual" in payload["optional_predictors"]
    assert payload["alpha_last_known"] == 0.7
    assert payload["weight_extra_trees"] == 0.0
    assert payload["weight_xgboost"] == 1.0
    blob = str(payload).lower()
    assert "artifacts" not in blob
    assert "artifact_dir" not in blob
    assert ".json" not in blob or "selected_model" in blob
