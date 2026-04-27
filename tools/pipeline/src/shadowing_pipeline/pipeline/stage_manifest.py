"""Stage G: manifest generation wrapper."""

from __future__ import annotations

from pathlib import Path

from ..manifest import generate_manifest


def stage_manifest(processed_root: Path, web_manifest_path: Path) -> Path:
    return generate_manifest(processed_root, web_manifest_path)
