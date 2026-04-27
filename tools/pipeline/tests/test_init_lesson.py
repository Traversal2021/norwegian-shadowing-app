"""Tests for raw lesson template generation."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from shadowing_pipeline.errors import ValidationError
from shadowing_pipeline.init_lesson import init_lesson


def test_init_lesson_creates_expected_files(tmp_path: Path) -> None:
    lesson_dir = init_lesson("lesson-001", "Lesson 001", raw_root=tmp_path)

    assert (lesson_dir / "original.no.txt").is_file()
    assert (lesson_dir / "annotated.no.txt").is_file()
    assert (lesson_dir / "audio.wav").is_file()
    assert (lesson_dir / "vocab.md").is_file()
    assert (lesson_dir / "grammar.md").is_file()
    meta = json.loads((lesson_dir / "meta.json").read_text(encoding="utf-8"))
    assert meta["id"] == "lesson-001"
    assert meta["title"] == "Lesson 001"
    assert meta["language"] == "nb"
    assert meta["level"] == "unknown"


def test_init_lesson_refuses_non_empty_existing_folder(tmp_path: Path) -> None:
    lesson_dir = tmp_path / "lesson-001"
    lesson_dir.mkdir()
    (lesson_dir / "meta.json").write_text("{}", encoding="utf-8")

    with pytest.raises(ValidationError, match="already exists"):
        init_lesson("lesson-001", "Lesson 001", raw_root=tmp_path)
