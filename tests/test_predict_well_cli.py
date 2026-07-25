"""CLI tests for scripts/predict_well.py."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from scripts.predict_well import main
from tests.fixtures import export_tiny_artifact_bundle, make_trailing_mask_well

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _write_input(tmp_path: Path, name: str = "abc123__horizontal_well.csv") -> Path:
    well = make_trailing_mask_well(n_known=10, n_hidden=5)
    path = tmp_path / name
    well.to_csv(path, index=False)
    return path


def test_cli_successful_run_default_active_model(tmp_path: Path):
    artifact_root = export_tiny_artifact_bundle(tmp_path)
    input_path = _write_input(tmp_path)
    out_dir = tmp_path / "out"
    code = main(
        [
            "--input",
            str(input_path),
            "--output-dir",
            str(out_dir),
            "--artifact-root",
            str(artifact_root),
        ]
    )
    assert code == 0
    assert (out_dir / "submission.csv").exists()
    assert (out_dir / "full_well_predictions.csv").exists()
    summary = json.loads((out_dir / "prediction_summary.json").read_text(encoding="utf-8"))
    assert summary["well_id"] == "abc123"
    assert summary["checksum_verification"] is True
    assert summary["prediction_rows"] == 5
    comp = pd.read_csv(out_dir / "submission.csv")
    assert list(comp.columns) == ["id", "tvt"]
    assert comp["id"].iloc[0] == "abc123_10"


def test_cli_explicit_model_version_and_custom_names(tmp_path: Path):
    artifact_root = export_tiny_artifact_bundle(tmp_path, version="v_custom")
    input_path = _write_input(tmp_path, "plain.csv")
    out_dir = tmp_path / "out2"
    code = main(
        [
            "--input",
            str(input_path),
            "--output-dir",
            str(out_dir),
            "--artifact-root",
            str(artifact_root),
            "--model-version",
            "v_custom",
            "--well-id",
            "customwell",
            "--competition-filename",
            "comp.csv",
            "--full-well-filename",
            "full.csv",
            "--summary-filename",
            "sum.json",
        ]
    )
    assert code == 0
    assert (out_dir / "comp.csv").exists()
    summary = json.loads((out_dir / "sum.json").read_text(encoding="utf-8"))
    assert summary["well_id"] == "customwell"
    assert summary["model_version"] == "v_custom"


def test_cli_overwrite_protection_and_success(tmp_path: Path):
    artifact_root = export_tiny_artifact_bundle(tmp_path)
    input_path = _write_input(tmp_path)
    out_dir = tmp_path / "out3"
    args = [
        "--input",
        str(input_path),
        "--output-dir",
        str(out_dir),
        "--artifact-root",
        str(artifact_root),
    ]
    assert main(args) == 0
    assert main(args) == 1  # exists without overwrite
    assert main([*args, "--overwrite"]) == 0


def test_cli_creates_output_directory(tmp_path: Path):
    artifact_root = export_tiny_artifact_bundle(tmp_path)
    input_path = _write_input(tmp_path)
    out_dir = tmp_path / "nested" / "predictions"
    assert not out_dir.exists()
    assert main(
        [
            "--input",
            str(input_path),
            "--output-dir",
            str(out_dir),
            "--artifact-root",
            str(artifact_root),
        ]
    ) == 0
    assert out_dir.is_dir()


def test_cli_invalid_model_version(tmp_path: Path):
    artifact_root = export_tiny_artifact_bundle(tmp_path)
    input_path = _write_input(tmp_path)
    code = main(
        [
            "--input",
            str(input_path),
            "--output-dir",
            str(tmp_path / "out"),
            "--artifact-root",
            str(artifact_root),
            "--model-version",
            "does_not_exist",
        ]
    )
    assert code == 1


def test_cli_missing_active_pointer(tmp_path: Path):
    artifact_root = export_tiny_artifact_bundle(tmp_path)
    (artifact_root / "current.json").unlink()
    input_path = _write_input(tmp_path)
    code = main(
        [
            "--input",
            str(input_path),
            "--output-dir",
            str(tmp_path / "out"),
            "--artifact-root",
            str(artifact_root),
        ]
    )
    assert code == 1


def test_cli_checksum_bypass_warns(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    artifact_root = export_tiny_artifact_bundle(tmp_path)
    input_path = _write_input(tmp_path)
    with pytest.warns(UserWarning, match="checksum verification is DISABLED"):
        code = main(
            [
                "--input",
                str(input_path),
                "--output-dir",
                str(tmp_path / "out"),
                "--artifact-root",
                str(artifact_root),
                "--skip-checksum-verification",
            ]
        )
    assert code == 0
    err = capsys.readouterr().err
    assert "WARNING" in err
    assert "checksum" in err.lower()
    summary = json.loads((tmp_path / "out" / "prediction_summary.json").read_text(encoding="utf-8"))
    assert summary["checksum_verification"] is False


def test_cli_does_not_mutate_project_current_pointer(tmp_path: Path):
    """Regression: tests must not rewrite artifacts/current.json in the repo."""

    real_pointer = PROJECT_ROOT / "artifacts" / "current.json"
    before = real_pointer.read_text(encoding="utf-8") if real_pointer.exists() else None
    artifact_root = export_tiny_artifact_bundle(tmp_path)
    input_path = _write_input(tmp_path)
    assert main(
        [
            "--input",
            str(input_path),
            "--output-dir",
            str(tmp_path / "out"),
            "--artifact-root",
            str(artifact_root),
        ]
    ) == 0
    after = real_pointer.read_text(encoding="utf-8") if real_pointer.exists() else None
    assert before == after
