from __future__ import annotations

from io import BytesIO

from fastapi.testclient import TestClient


def test_error_shape_includes_request_id(client: TestClient):
    response = client.post(
        "/validate",
        files={"file": ("bad.txt", BytesIO(b"MD,GR\n1,2\n"), "text/csv")},
        headers={"X-Request-ID": "req-test-123"},
    )
    assert response.status_code == 400
    assert response.headers["X-Request-ID"] == "req-test-123"
    body = response.json()
    assert set(body.keys()) == {"error"}
    assert set(body["error"].keys()) == {"code", "message", "details", "request_id"}
    assert body["error"]["request_id"] == "req-test-123"
    assert body["error"]["code"] == "INVALID_UPLOAD"
    # No filesystem path leakage
    assert ":\\" not in body["error"]["message"]
    assert "/artifacts" not in str(body).lower()


def test_generated_request_id_when_missing(client: TestClient):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.headers["X-Request-ID"]
