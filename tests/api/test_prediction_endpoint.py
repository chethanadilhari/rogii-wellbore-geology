from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
from pathlib import Path

import numpy as np
import pandas as pd
from fastapi.testclient import TestClient

from tests.fixtures import make_trailing_mask_well


def _post_predict(
    client: TestClient,
    content: bytes,
    *,
    endpoint: str = "/predict",
    filename: str = "abc123__horizontal_well.csv",
    well_id: str | None = None,
):
    files = {"file": (filename, BytesIO(content), "text/csv")}
    data = {"well_id": well_id} if well_id is not None else None
    return client.post(endpoint, files=files, data=data)


def test_predict_competition_csv(client: TestClient, sample_csv_bytes: bytes):
    response = _post_predict(client, sample_csv_bytes)
    assert response.status_code == 200
    assert "text/csv" in response.headers["content-type"]
    assert "abc123_submission.csv" in response.headers.get("content-disposition", "")
    assert response.headers["X-Model-Version"] == "v_api"
    assert response.headers["X-Well-Id"] == "abc123"
    assert response.headers["X-Prediction-Rows"] == "6"

    frame = pd.read_csv(BytesIO(response.content))
    assert list(frame.columns) == ["id", "tvt"]
    assert len(frame) == 6
    assert np.isfinite(frame["tvt"]).all()
    assert frame["id"].tolist() == [f"abc123_{i}" for i in range(12, 18)]


def test_predict_custom_well_id(client: TestClient, sample_csv_bytes: bytes):
    response = _post_predict(client, sample_csv_bytes, filename="plain.csv", well_id="customwell")
    assert response.status_code == 200
    assert response.headers["X-Well-Id"] == "customwell"
    frame = pd.read_csv(BytesIO(response.content))
    assert frame["id"].iloc[0].startswith("customwell_")


def test_predict_full_well(client: TestClient, sample_csv_bytes: bytes):
    original = pd.read_csv(BytesIO(sample_csv_bytes))
    response = _post_predict(client, sample_csv_bytes, endpoint="/predict/full-well")
    assert response.status_code == 200
    assert "full_well_predictions.csv" in response.headers.get("content-disposition", "")
    full = pd.read_csv(BytesIO(response.content))
    assert len(full) == len(original)
    assert "predicted_tvt" in full.columns
    assert "prediction_source" in full.columns
    known = original["TVT_input"].notna()
    assert (full.loc[known, "prediction_source"] == "known").all()
    assert (full.loc[~known, "prediction_source"] == "model").all()
    np.testing.assert_allclose(
        full.loc[known, "predicted_tvt"],
        original.loc[known, "TVT_input"],
    )


def test_predict_deterministic_repeat(client: TestClient, sample_csv_bytes: bytes):
    r1 = _post_predict(client, sample_csv_bytes)
    r2 = _post_predict(client, sample_csv_bytes)
    assert r1.content == r2.content


def test_predict_concurrent_no_cross_contamination(client: TestClient):
    service = client.app.state.inference_service
    service_id = id(service)
    medians_before = service.bundle.medians.copy()
    columns_before = list(service.bundle.feature_columns)

    payloads = []
    for i in range(4):
        well = make_trailing_mask_well(n_known=8, n_hidden=4, start_tvt=11000.0 + i)
        payloads.append(well.to_csv(index=False).encode("utf-8"))

    def _one(content: bytes):
        return _post_predict(client, content, filename="w__horizontal_well.csv", well_id="conc")

    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(_one, payloads))

    assert all(r.status_code == 200 for r in results)
    assert id(client.app.state.inference_service) == service_id
    pd.testing.assert_series_equal(client.app.state.inference_service.bundle.medians, medians_before)
    assert list(client.app.state.inference_service.bundle.feature_columns) == columns_before

    # Each response deterministic vs solo request
    for content, concurrent in zip(payloads, results, strict=True):
        solo = _post_predict(client, content, filename="w__horizontal_well.csv", well_id="conc")
        assert concurrent.content == solo.content
