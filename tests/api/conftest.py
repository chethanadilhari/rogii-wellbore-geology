"""Shared helpers for FastAPI TestClient suites."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.api.config import Settings
from app.api.main import create_app
from tests.fixtures import export_tiny_artifact_bundle, make_trailing_mask_well

PROJECT_ROOT = Path(__file__).resolve().parents[2]
REAL_ARTIFACTS = PROJECT_ROOT / "artifacts"
REAL_V1 = REAL_ARTIFACTS / "v1"


@pytest.fixture
def tiny_artifact_root(tmp_path: Path) -> Path:
    return export_tiny_artifact_bundle(tmp_path, version="v_api")


@pytest.fixture
def api_settings(tiny_artifact_root: Path) -> Settings:
    return Settings(
        model_artifact_root=tiny_artifact_root,
        model_version="v_api",
        verify_artifact_checksums=True,
        max_upload_mb=1,
        max_rows_per_well=10_000,
        cors_allowed_origins="http://localhost:5173",
    )


@pytest.fixture
def client(api_settings: Settings):
    application = create_app(api_settings)
    with TestClient(application) as test_client:
        yield test_client


@pytest.fixture
def sample_csv_bytes() -> bytes:
    well = make_trailing_mask_well(n_known=12, n_hidden=6)
    return well.to_csv(index=False).encode("utf-8")


@pytest.fixture
def sample_csv_file(tmp_path: Path, sample_csv_bytes: bytes) -> Path:
    path = tmp_path / "abc123__horizontal_well.csv"
    path.write_bytes(sample_csv_bytes)
    return path
