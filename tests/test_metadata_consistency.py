from __future__ import annotations

from pathlib import Path

from rogii_geo.metadata_verify import verify_production_metadata


def test_production_metadata_is_internally_consistent():
    project_root = Path(__file__).resolve().parents[1]
    result = verify_production_metadata(
        project_root / "results" / "ensemble_residual_submission"
    )
    assert result.ok, "\n".join(result.discrepancies)
    assert result.feature_column_count == 51
