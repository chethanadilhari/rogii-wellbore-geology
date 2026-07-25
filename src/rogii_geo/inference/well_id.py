"""Well ID resolution and sanitization for inference outputs."""

from __future__ import annotations

import re
from pathlib import Path

_HORIZONTAL_SUFFIX = "__horizontal_well.csv"
_SAFE_WELL_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.\-]*$")


def sanitize_well_id(well_id: str) -> str:
    """
    Return a filesystem- and ID-safe well identifier.

    Rejects empty values, path separators, and characters outside
    ``[A-Za-z0-9_.-]``.
    """

    candidate = str(well_id).strip()
    if not candidate:
        raise ValueError("Well ID is empty.")
    if any(sep in candidate for sep in ("/", "\\")) or ".." in candidate:
        raise ValueError(f"Unsafe well ID (path separators not allowed): {well_id!r}")
    if not _SAFE_WELL_ID.fullmatch(candidate):
        raise ValueError(
            f"Unsafe well ID {well_id!r}: only letters, digits, underscore, "
            "dot, and hyphen are allowed."
        )
    return candidate


def resolve_well_id(input_path: Path, explicit_well_id: str | None = None) -> str:
    """
    Resolve well ID in priority order:

    1. Explicit ``--well-id``
    2. Filename matching ``{well_id}__horizontal_well.csv``
    3. Input filename stem
    """

    if explicit_well_id is not None and str(explicit_well_id).strip():
        return sanitize_well_id(explicit_well_id)

    name = Path(input_path).name
    if name.lower().endswith(_HORIZONTAL_SUFFIX):
        stem = name[: -len(_HORIZONTAL_SUFFIX)]
        return sanitize_well_id(stem)

    return sanitize_well_id(Path(input_path).stem)
