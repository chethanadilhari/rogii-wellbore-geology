"""Training well discovery."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


def resolve_train_dir(project_root: Path, train_dir: Path | None = None) -> Path:
    """Resolve ``data/raw/train`` or ``data/train`` (or an explicit path)."""

    if train_dir is not None:
        path = Path(train_dir)
        if not path.is_dir():
            raise FileNotFoundError(f"Training directory not found: {path}")
        return path.resolve()

    root = Path(project_root).resolve()
    candidates = [
        root / "data" / "raw" / "train",
        root / "data" / "train",
    ]
    for candidate in candidates:
        if candidate.is_dir() and any(candidate.glob("*__horizontal_well.csv")):
            return candidate.resolve()

    raise FileNotFoundError(
        "Could not locate a training directory with *__horizontal_well.csv files. "
        f"Tried: {', '.join(str(c) for c in candidates)}"
    )


def discover_horizontal_wells(train_dir: Path) -> list[str]:
    """Return sorted well IDs that have a horizontal CSV (typewell optional)."""

    train_dir = Path(train_dir)
    if not train_dir.is_dir():
        raise FileNotFoundError(f"Training directory not found: {train_dir}")

    well_ids = sorted(
        {
            path.name.replace("__horizontal_well.csv", "")
            for path in train_dir.glob("*__horizontal_well.csv")
        }
    )
    if not well_ids:
        raise FileNotFoundError(
            f"No *__horizontal_well.csv files found in {train_dir}"
        )
    return well_ids


def build_horizontal_registry(train_dir: Path) -> pd.DataFrame:
    """Registry with well_id and horizontal_path columns."""

    train_dir = Path(train_dir)
    rows = []
    for well_id in discover_horizontal_wells(train_dir):
        rows.append(
            {
                "well_id": well_id,
                "horizontal_path": str(train_dir / f"{well_id}__horizontal_well.csv"),
            }
        )
    return pd.DataFrame(rows)


def load_horizontal_csv(path: Path | str) -> pd.DataFrame:
    return pd.read_csv(path)


def estimate_test_missing_fractions(
    test_dir: Path | None,
    fallback: list[float],
) -> list[float]:
    """Estimate trailing missing fractions from test wells when available."""

    if test_dir is None or not Path(test_dir).is_dir():
        return list(fallback)

    fractions: list[float] = []
    for path in sorted(Path(test_dir).glob("*__horizontal_well.csv")):
        df = pd.read_csv(path, usecols=lambda c: c == "TVT_input")
        if "TVT_input" not in df.columns or df.empty:
            continue
        frac = float(df["TVT_input"].isna().mean())
        if 0.0 < frac < 1.0:
            fractions.append(round(frac, 4))

    if not fractions:
        return list(fallback)
    return sorted(set(fractions + list(fallback)))
