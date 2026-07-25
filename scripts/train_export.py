"""CLI: train residual models and export a versioned artifact bundle."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _project_root_from_cwd() -> Path:
    cwd = Path.cwd().resolve()
    for candidate in [cwd, *cwd.parents]:
        if (candidate / "data" / "raw" / "train").is_dir() or (
            candidate / "data" / "train"
        ).is_dir():
            return candidate
        if (candidate / "src" / "rogii_geo").is_dir() and (candidate / "pyproject.toml").exists():
            return candidate
    return cwd


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Train the FinalProductionCandidate residual pipeline and export "
            "an immutable artifact bundle for inference."
        )
    )
    parser.add_argument("--project-root", type=Path, default=None)
    parser.add_argument("--train-dir", type=Path, default=None)
    parser.add_argument("--artifact-root", type=Path, default=None)
    parser.add_argument("--model-version", type=str, default=None)
    parser.add_argument("--fit-max-rows", type=int, default=None)
    parser.add_argument("--max-hidden-rows", type=int, default=None)
    parser.add_argument("--random-state", type=int, default=None)
    parser.add_argument(
        "--include-optional-extra-trees",
        action="store_true",
        help="Train and export Extra Trees even when weight_extra_trees == 0.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Allow replacing an existing non-empty artifact version directory.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    # Ensure src/ is importable when running as a script without editable install.
    script_root = Path(__file__).resolve().parents[1]
    src = script_root / "src"
    if src.is_dir() and str(src) not in sys.path:
        sys.path.insert(0, str(src))

    from rogii_geo.training.config import TrainingConfig
    from rogii_geo.training.pipeline import run_train_export

    args = build_parser().parse_args(argv)
    project_root = (args.project_root or _project_root_from_cwd()).resolve()

    config = TrainingConfig()
    if args.random_state is not None:
        config.with_random_state(args.random_state)
    if args.fit_max_rows is not None:
        config.model_fit_max_rows = int(args.fit_max_rows)
    if args.max_hidden_rows is not None:
        config.max_hidden_rows_per_mask = int(args.max_hidden_rows)
    config.include_optional_extra_trees = bool(args.include_optional_extra_trees)

    try:
        result = run_train_export(
            project_root=project_root,
            train_dir=args.train_dir,
            artifact_root=args.artifact_root,
            model_version=args.model_version,
            config=config,
            overwrite=bool(args.overwrite),
        )
    except Exception as exc:  # noqa: BLE001 - CLI boundary
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print("=== Train / export complete ===")
    print(json.dumps(result.summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
