"""CLI: predict TVT for one horizontal-well CSV using frozen production artifacts."""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import warnings
from pathlib import Path

import pandas as pd


def _project_root_from_cwd() -> Path:
    cwd = Path.cwd().resolve()
    for candidate in [cwd, *cwd.parents]:
        if (candidate / "artifacts").is_dir() and (candidate / "src" / "rogii_geo").is_dir():
            return candidate
        if (candidate / "pyproject.toml").exists() and (candidate / "src" / "rogii_geo").is_dir():
            return candidate
    return cwd


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run production inference on one horizontal-well CSV. "
            "Loads the active artifact bundle (default: artifacts/current.json -> v1), "
            "predicts only missing TVT_input rows, and writes competition + full-well outputs."
        )
    )
    parser.add_argument("--input", type=Path, required=True, help="Path to one horizontal-well CSV.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("predictions"),
        help="Directory for submission.csv, full_well_predictions.csv, and summary JSON.",
    )
    parser.add_argument(
        "--artifact-root",
        type=Path,
        default=None,
        help="Artifact root containing version dirs and current.json (default: <project>/artifacts).",
    )
    parser.add_argument(
        "--model-version",
        type=str,
        default=None,
        help="Explicit artifact version (e.g. v1). Overrides artifacts/current.json.",
    )
    parser.add_argument(
        "--well-id",
        type=str,
        default=None,
        help="Override well ID used in competition row IDs.",
    )
    parser.add_argument(
        "--competition-filename",
        type=str,
        default="submission.csv",
    )
    parser.add_argument(
        "--full-well-filename",
        type=str,
        default="full_well_predictions.csv",
    )
    parser.add_argument(
        "--summary-filename",
        type=str,
        default="prediction_summary.json",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Allow replacing existing output files.",
    )
    parser.add_argument(
        "--skip-checksum-verification",
        action="store_true",
        help="DEBUG ONLY: skip artifact checksum verification (prints a warning).",
    )
    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
    )
    return parser


def _write_outputs_atomically(
    *,
    competition: pd.DataFrame,
    full_well: pd.DataFrame,
    summary: dict,
    competition_path: Path,
    full_well_path: Path,
    summary_path: Path,
) -> None:
    """Write all three outputs via temps, verify, then promote with os.replace."""

    competition_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_comp = competition_path.with_name(f".{competition_path.name}.tmp")
    tmp_full = full_well_path.with_name(f".{full_well_path.name}.tmp")
    tmp_sum = summary_path.with_name(f".{summary_path.name}.tmp")
    try:
        competition.to_csv(tmp_comp, index=False)
        full_well.to_csv(tmp_full, index=False)
        tmp_sum.write_text(
            json.dumps(summary, indent=2, allow_nan=False) + "\n",
            encoding="utf-8",
        )

        check = pd.read_csv(tmp_comp)
        if list(check.columns) != ["id", "tvt"] or check.empty:
            raise ValueError("Competition temp output failed verification.")
        if int(pd.read_csv(tmp_full).shape[0]) != len(full_well):
            raise ValueError("Full-well temp output failed verification.")
        json.loads(tmp_sum.read_text(encoding="utf-8"))

        os.replace(tmp_comp, competition_path)
        os.replace(tmp_full, full_well_path)
        os.replace(tmp_sum, summary_path)
    finally:
        for tmp in (tmp_comp, tmp_full, tmp_sum):
            if tmp.exists():
                tmp.unlink(missing_ok=True)


def main(argv: list[str] | None = None) -> int:
    script_root = Path(__file__).resolve().parents[1]
    src = script_root / "src"
    if src.is_dir() and str(src) not in sys.path:
        sys.path.insert(0, str(src))

    from rogii_geo.inference.io import read_horizontal_csv
    from rogii_geo.inference.service import WellInferenceService
    from rogii_geo.inference.well_id import resolve_well_id

    args = build_parser().parse_args(argv)
    logging.basicConfig(
        level=getattr(logging, args.log_level.upper(), logging.INFO),
        format="%(levelname)s: %(message)s",
    )
    log = logging.getLogger("predict_well")

    project_root = _project_root_from_cwd()
    artifact_root = (args.artifact_root or (project_root / "artifacts")).resolve()
    output_dir = Path(args.output_dir).resolve()
    input_path = Path(args.input).resolve()

    verify = not bool(args.skip_checksum_verification)
    if not verify:
        message = (
            "WARNING: artifact checksum verification is DISABLED "
            "(--skip-checksum-verification). Use only for debugging."
        )
        print(message, file=sys.stderr)
        warnings.warn(message, UserWarning, stacklevel=1)

    try:
        if args.model_version is None and not (artifact_root / "current.json").exists():
            raise FileNotFoundError(
                f"No --model-version supplied and active pointer missing: "
                f"{artifact_root / 'current.json'}"
            )

        service = WellInferenceService.from_artifact_root(
            artifact_root,
            model_version=args.model_version,
            verify_checksums=verify,
        )
        desc = service.describe()
        log.info(
            "Loaded model_version=%s selected_model=%s feature_count=%s "
            "required_predictors=%s checksum_verification=%s",
            desc["model_version"],
            desc["selected_model"],
            desc["feature_count"],
            desc["required_predictors"],
            desc["checksum_verification"],
        )

        well_id = resolve_well_id(input_path, args.well_id)
        frame = read_horizontal_csv(input_path)
        result = service.predict_dataframe(
            frame,
            well_id,
            input_file=input_path,
        )

        competition_path = output_dir / args.competition_filename
        full_well_path = output_dir / args.full_well_filename
        summary_path = output_dir / args.summary_filename

        for path in (competition_path, full_well_path, summary_path):
            if path.exists() and not args.overwrite:
                raise FileExistsError(
                    f"Output already exists (pass --overwrite to replace): {path}"
                )

        summary = dict(result.summary)
        summary["competition_output"] = str(competition_path)
        summary["full_well_output"] = str(full_well_path)
        summary["summary_output"] = str(summary_path)

        _write_outputs_atomically(
            competition=result.competition_output,
            full_well=result.full_well_output,
            summary=summary,
            competition_path=competition_path,
            full_well_path=full_well_path,
            summary_path=summary_path,
        )

    except (FileNotFoundError, FileExistsError, IsADirectoryError, ValueError, KeyError) as exc:
        if args.log_level.upper() == "DEBUG":
            log.exception("Prediction failed")
        else:
            print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # noqa: BLE001 - CLI boundary
        if args.log_level.upper() == "DEBUG":
            log.exception("Prediction failed")
        else:
            print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    checksum_status = "verified" if verify else "skipped"
    print("Prediction complete")
    print(f"Model version: {result.summary['model_version']}")
    print(f"Well ID: {result.summary['well_id']}")
    print(f"Total rows: {result.summary['total_rows']}")
    print(f"Known rows: {result.summary['known_rows']}")
    print(f"Predicted rows: {result.summary['prediction_rows']}")
    print(f"Competition output: {competition_path}")
    print(f"Full-well output: {full_well_path}")
    print(f"Summary: {summary_path}")
    print(f"Checksums: {checksum_status}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
