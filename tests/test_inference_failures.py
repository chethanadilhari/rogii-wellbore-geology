"""Validation and CLI failure-path coverage."""

from __future__ import annotations

from pathlib import Path

import pytest

from rogii_geo.inference.io import read_horizontal_csv
from rogii_geo.inference.service import WellInferenceService
from rogii_geo.inference.well_id import resolve_well_id, sanitize_well_id
from scripts.predict_well import main
from tests.fixtures import export_tiny_artifact_bundle, make_dirty_boundary_well, make_trailing_mask_well


def test_missing_required_column(tmp_path: Path):
    artifact_root = export_tiny_artifact_bundle(tmp_path)
    service = WellInferenceService.from_artifact_root(artifact_root)
    well = make_trailing_mask_well().drop(columns=["GR"])
    with pytest.raises(ValueError, match="Missing required columns"):
        service.predict_dataframe(well, "w1")


def test_empty_file(tmp_path: Path):
    path = tmp_path / "empty.csv"
    path.write_text("", encoding="utf-8")
    with pytest.raises(ValueError, match="empty"):
        read_horizontal_csv(path)


def test_all_known_tvt_input(tmp_path: Path):
    artifact_root = export_tiny_artifact_bundle(tmp_path)
    service = WellInferenceService.from_artifact_root(artifact_root)
    well = make_trailing_mask_well(n_known=10, n_hidden=0)
    with pytest.raises(ValueError, match="No prediction rows"):
        service.predict_dataframe(well, "w1")


def test_all_missing_tvt_input(tmp_path: Path):
    artifact_root = export_tiny_artifact_bundle(tmp_path)
    service = WellInferenceService.from_artifact_root(artifact_root)
    well = make_trailing_mask_well(n_known=10, n_hidden=5)
    well["TVT_input"] = float("nan")
    with pytest.raises(ValueError, match="entirely missing"):
        service.predict_dataframe(well, "w1")


def test_non_trailing_missing_interval(tmp_path: Path):
    artifact_root = export_tiny_artifact_bundle(tmp_path)
    service = WellInferenceService.from_artifact_root(artifact_root)
    with pytest.raises(ValueError, match="clean trailing mask"):
        service.predict_dataframe(make_dirty_boundary_well(), "w1")


def test_invalid_md(tmp_path: Path):
    artifact_root = export_tiny_artifact_bundle(tmp_path)
    service = WellInferenceService.from_artifact_root(artifact_root)
    well = make_trailing_mask_well()
    well.loc[0, "MD"] = float("nan")
    with pytest.raises(ValueError, match="MD"):
        service.predict_dataframe(well, "w1")


def test_malformed_csv_and_directory(tmp_path: Path):
    bad = tmp_path / "not_csv.txt"
    bad.write_text("MD,GR\n1,2\n", encoding="utf-8")
    with pytest.raises(ValueError, match=r"\.csv"):
        read_horizontal_csv(bad)

    directory = tmp_path / "dir"
    directory.mkdir()
    with pytest.raises(IsADirectoryError):
        read_horizontal_csv(directory)

    missing = tmp_path / "missing.csv"
    with pytest.raises(FileNotFoundError):
        read_horizontal_csv(missing)


def test_duplicate_column_names(tmp_path: Path):
    path = tmp_path / "dup.csv"
    path.write_text("MD,GR,X,Y,Z,TVT_input,MD\n1,2,3,4,5,6,7\n", encoding="utf-8")
    with pytest.raises(ValueError, match="Duplicate column names"):
        read_horizontal_csv(path)


def test_unsafe_well_id():
    with pytest.raises(ValueError, match="Unsafe"):
        sanitize_well_id("../evil")
    with pytest.raises(ValueError, match="Unsafe"):
        sanitize_well_id("well/id")
    with pytest.raises(ValueError, match="Unsafe"):
        sanitize_well_id("bad id!")
    assert resolve_well_id(Path("000d7d20__horizontal_well.csv")) == "000d7d20"
    assert resolve_well_id(Path("plain.csv"), explicit_well_id="ok_well") == "ok_well"


def test_cli_rejects_unsafe_well_id(tmp_path: Path):
    artifact_root = export_tiny_artifact_bundle(tmp_path)
    well = make_trailing_mask_well()
    path = tmp_path / "well.csv"
    well.to_csv(path, index=False)
    code = main(
        [
            "--input",
            str(path),
            "--output-dir",
            str(tmp_path / "out"),
            "--artifact-root",
            str(artifact_root),
            "--well-id",
            "../bad",
        ]
    )
    assert code == 1
