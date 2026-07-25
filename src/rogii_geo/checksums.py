"""Shared checksum helpers used by training export and inference loading."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_checksums(artifact_dir: Path, manifest: dict[str, Any] | None = None) -> None:
    artifact_dir = Path(artifact_dir)
    if manifest is None:
        manifest = json.loads((artifact_dir / "manifest.json").read_text(encoding="utf-8"))
    checksums = manifest.get("file_checksums_sha256", {})
    for name, expected in checksums.items():
        path = artifact_dir / name
        if not path.exists():
            raise FileNotFoundError(f"Checksum listed file missing: {path}")
        actual = sha256_file(path)
        if actual != expected:
            raise ValueError(
                f"Checksum mismatch for {name}: expected {expected}, got {actual}"
            )
