"""Service tests for WellInferenceService."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from rogii_geo.inference.service import WellInferenceService
from tests.fixtures import export_tiny_artifact_bundle, make_trailing_mask_well

PROJECT_ROOT = Path(__file__).resolve().parents[1]
REAL_ARTIFACTS = PROJECT_ROOT / "artifacts"
REAL_V1 = REAL_ARTIFACTS / "v1"


def test_service_loads_bundle_and_predicts(tmp_path: Path):
    artifact_root = export_tiny_artifact_bundle(tmp_path)
    service = WellInferenceService.from_artifact_root(artifact_root, verify_checksums=True)
    desc = service.describe()
    assert desc["checksum_verification"] is True
    assert desc["xgboost_loaded"] is True
    assert desc["extra_trees_loaded"] is False
    assert desc["required_predictors"] == ["last_known", "xgboost_residual"]
    assert desc["feature_count"] == 4

    well = make_trailing_mask_well(n_known=12, n_hidden=6)
    well = well.sample(frac=1.0, random_state=2)  # scramble presentation; keep index labels

    result = service.predict_dataframe(well, "svcwell")
    n_missing = int(well["TVT_input"].isna().sum())
    assert len(result.competition_output) == n_missing
    assert len(result.full_well_output) == len(well)
    assert list(result.competition_output.columns) == ["id", "tvt"]
    assert np.isfinite(result.competition_output["tvt"]).all()

    expected_ids = [f"svcwell_{int(i)}" for i in well.index[well["TVT_input"].isna()]]
    assert result.competition_output["id"].tolist() == expected_ids

    known = well["TVT_input"].notna()
    assert (result.full_well_output.loc[known, "prediction_source"] == "known").all()
    assert (result.full_well_output.loc[~known, "prediction_source"] == "model").all()
    np.testing.assert_allclose(
        result.full_well_output.loc[known, "predicted_tvt"],
        well.loc[known, "TVT_input"],
    )
    assert result.full_well_output.index.tolist() == well.index.tolist()
    assert result.summary["prediction_rows"] == n_missing
    assert result.summary["feature_count"] == 4
    assert result.summary["rows_reordered_internally"] is True


def test_exact_feature_order_used(tmp_path: Path):
    artifact_root = export_tiny_artifact_bundle(tmp_path)
    service = WellInferenceService.from_artifact_root(artifact_root)
    assert service.bundle.feature_columns == [
        "MD",
        "GR",
        "last_known_tvt",
        "linear_tvt_projection",
    ]


@pytest.mark.skipif(not REAL_V1.is_dir(), reason="artifacts/v1 not available")
def test_real_v1_bundle_feature_contract():
    service = WellInferenceService.from_artifact_root(
        REAL_ARTIFACTS,
        model_version="v1",
        verify_checksums=True,
    )
    assert service.feature_count == 51
    assert service.selected_model == "blend_lastknown_0.70_ensemble"
    assert service.required_predictors == ["last_known", "xgboost_residual"]
    assert service.bundle.et_model is None
    assert service.bundle.xgb_model is not None
    assert "TVT" not in service.bundle.feature_columns
    assert "TVT_input" not in service.bundle.feature_columns

    well = make_trailing_mask_well(n_known=30, n_hidden=15, start_tvt=11700.0)
    result = service.predict_dataframe(well, "golden01")
    assert result.summary["feature_count"] == 51
    assert len(result.competition_output) == 15
    assert np.isfinite(result.competition_output["tvt"]).all()
