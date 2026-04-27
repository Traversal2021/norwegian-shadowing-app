"""Tests for shell script portability expectations."""

from __future__ import annotations

from pathlib import Path


def test_run_ingestion_script_does_not_use_mapfile() -> None:
    script = Path(__file__).resolve().parents[3] / "scripts" / "run_ingestion.sh"
    content = script.read_text(encoding="utf-8")
    assert "mapfile" not in content
