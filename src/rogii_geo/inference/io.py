"""CSV input loading and atomic output writers for one-well inference."""

from __future__ import annotations

import csv
import json
import os
from pathlib import Path
from typing import Any

import pandas as pd


def read_horizontal_csv(path: Path) -> pd.DataFrame:
    """
    Load one horizontal-well CSV with strict path and header checks.

    Rejects missing paths, directories, non-CSV extensions, empty files,
    and duplicate column names.
    """

    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Input file not found: {path}")
    if path.is_dir():
        raise IsADirectoryError(f"Input path is a directory, not a CSV file: {path}")
    if path.suffix.lower() != ".csv":
        raise ValueError(f"Input must be a .csv file; got: {path}")

    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.reader(handle)
        try:
            header = next(reader)
        except StopIteration as exc:
            raise ValueError(f"Input CSV is empty: {path}") from exc

    if not header or all(not str(c).strip() for c in header):
        raise ValueError(f"Input CSV has no header columns: {path}")
    if len(header) != len(set(header)):
        duplicates = sorted({c for c in header if header.count(c) > 1})
        raise ValueError(f"Duplicate column names in CSV header: {duplicates}")

    frame = pd.read_csv(path)
    if frame.empty:
        raise ValueError(f"Input CSV has no data rows: {path}")
    if frame.columns.duplicated().any():
        duplicates = frame.columns[frame.columns.duplicated()].tolist()
        raise ValueError(f"Duplicate column names after CSV load: {duplicates}")
    return frame


def _ensure_writable(path: Path, *, overwrite: bool) -> None:
    if path.exists() and not overwrite:
        raise FileExistsError(
            f"Output already exists (pass --overwrite to replace): {path}"
        )


def atomic_write_csv(
    frame: pd.DataFrame,
    path: Path,
    *,
    overwrite: bool = False,
) -> Path:
    """Write a CSV via a temporary file then atomically rename."""

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    _ensure_writable(path, overwrite=overwrite)
    temp = path.with_name(f".{path.name}.tmp")
    try:
        frame.to_csv(temp, index=False)
        os.replace(temp, path)
    finally:
        if temp.exists():
            temp.unlink(missing_ok=True)
    return path


def atomic_write_json(
    payload: dict[str, Any],
    path: Path,
    *,
    overwrite: bool = False,
) -> Path:
    """Write JSON via a temporary file then atomically rename."""

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    _ensure_writable(path, overwrite=overwrite)
    temp = path.with_name(f".{path.name}.tmp")
    try:
        temp.write_text(
            json.dumps(payload, indent=2, allow_nan=False) + "\n",
            encoding="utf-8",
        )
        os.replace(temp, path)
    finally:
        if temp.exists():
            temp.unlink(missing_ok=True)
    return path
