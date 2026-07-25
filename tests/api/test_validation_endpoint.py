from __future__ import annotations

from io import BytesIO
from pathlib import Path

from fastapi.testclient import TestClient

from app.api.config import Settings
from app.api.main import create_app
from tests.fixtures import make_dirty_boundary_well, make_trailing_mask_well


def _post_validate(client: TestClient, content: bytes, filename: str = "well.csv", well_id: str | None = None):
    files = {"file": (filename, BytesIO(content), "text/csv")}
    data = {}
    if well_id is not None:
        data["well_id"] = well_id
    return client.post("/validate", files=files, data=data)


def test_validate_valid_well(client: TestClient, sample_csv_bytes: bytes):
    response = _post_validate(client, sample_csv_bytes, "abc123__horizontal_well.csv")
    assert response.status_code == 200
    payload = response.json()
    assert payload["valid"] is True
    assert payload["well_id"] == "abc123"
    assert payload["total_rows"] == 18
    assert payload["known_rows"] == 12
    assert payload["prediction_rows"] == 6


def test_validate_invalid_extension(client: TestClient, sample_csv_bytes: bytes):
    response = _post_validate(client, sample_csv_bytes, "well.txt")
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_UPLOAD"


def test_validate_empty_file(client: TestClient):
    response = _post_validate(client, b"", "empty.csv")
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "EMPTY_FILE"


def test_validate_malformed_csv(client: TestClient):
    response = _post_validate(client, b"\xff\xfe\x00not-utf8", "bad.csv")
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_CSV"


def test_validate_duplicate_columns(client: TestClient):
    content = b"MD,GR,X,Y,Z,TVT_input,MD\n1,2,3,4,5,6,7\n"
    response = _post_validate(client, content, "dup.csv")
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "DUPLICATE_COLUMNS"


def test_validate_missing_required_columns(client: TestClient):
    well = make_trailing_mask_well().drop(columns=["GR"])
    response = _post_validate(client, well.to_csv(index=False).encode("utf-8"))
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "MISSING_REQUIRED_COLUMNS"


def test_validate_all_known(client: TestClient):
    well = make_trailing_mask_well(n_known=10, n_hidden=0)
    response = _post_validate(client, well.to_csv(index=False).encode("utf-8"))
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "NO_PREDICTION_ROWS"


def test_validate_all_missing(client: TestClient):
    well = make_trailing_mask_well()
    well["TVT_input"] = float("nan")
    response = _post_validate(client, well.to_csv(index=False).encode("utf-8"))
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "NO_KNOWN_TVT"


def test_validate_non_trailing(client: TestClient):
    well = make_dirty_boundary_well()
    response = _post_validate(client, well.to_csv(index=False).encode("utf-8"))
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "NON_TRAILING_TVT_GAP"


def test_validate_invalid_md(client: TestClient):
    well = make_trailing_mask_well()
    well.loc[0, "MD"] = float("nan")
    response = _post_validate(client, well.to_csv(index=False).encode("utf-8"))
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_MD"


def test_validate_unsafe_well_id(client: TestClient, sample_csv_bytes: bytes):
    response = _post_validate(client, sample_csv_bytes, "well.csv", well_id="../evil")
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "UNSAFE_WELL_ID"


def test_validate_row_limit_exceeded(tiny_artifact_root: Path):
    settings = Settings(
        model_artifact_root=tiny_artifact_root,
        model_version="v_api",
        max_rows_per_well=5,
        max_upload_mb=1,
    )
    application = create_app(settings)
    well = make_trailing_mask_well(n_known=10, n_hidden=5)
    with TestClient(application) as client:
        response = _post_validate(client, well.to_csv(index=False).encode("utf-8"))
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "ROW_LIMIT_EXCEEDED"


def test_validate_upload_size_exceeded(tiny_artifact_root: Path):
    settings = Settings(
        model_artifact_root=tiny_artifact_root,
        model_version="v_api",
        max_upload_mb=1,
        max_rows_per_well=100000,
    )
    application = create_app(settings)
    # ~1.2 MiB payload exceeds MAX_UPLOAD_MB=1
    row = b"10000,50,1,2,3,11000\n"
    header = b"MD,GR,X,Y,Z,TVT_input\n"
    payload = header + (row * 80000)
    assert len(payload) > 1024 * 1024
    with TestClient(application) as client:
        response = _post_validate(client, payload, "big.csv")
    assert response.status_code == 413
    assert response.json()["error"]["code"] == "FILE_TOO_LARGE"
