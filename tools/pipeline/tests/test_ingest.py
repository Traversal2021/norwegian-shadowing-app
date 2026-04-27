"""Tests for raw lesson ingestion and validation."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from shadowing_pipeline.errors import ValidationError
from shadowing_pipeline.ingest import load_raw_lesson


def _write_lesson(root: Path, lesson_id: str = "lesson-a") -> Path:
    lesson_dir = root / lesson_id
    lesson_dir.mkdir()
    (lesson_dir / "original.no.txt").write_text("Hei verden.\n", encoding="utf-8")
    (lesson_dir / "annotated.no.txt").write_text("Hei (hello) verden.\n", encoding="utf-8")
    (lesson_dir / "audio.wav").write_bytes(b"placeholder")
    (lesson_dir / "meta.json").write_text(
        json.dumps(
            {
                "id": lesson_id,
                "title": "Hei verden",
                "source": "test",
                "language": "nb",
                "tags": ["test"],
            }
        ),
        encoding="utf-8",
    )
    return lesson_dir


def test_load_raw_lesson_validates_required_shape(tmp_path: Path) -> None:
    lesson = load_raw_lesson(_write_lesson(tmp_path))

    assert lesson.lesson_id == "lesson-a"
    assert lesson.original_text == "Hei verden."
    assert lesson.annotated_text == "Hei (hello) verden."
    assert lesson.meta.title == "Hei verden"
    assert lesson.meta.language == "nb"
    assert lesson.original_path.name == "original.no.txt"


def test_load_raw_lesson_reports_missing_file(tmp_path: Path) -> None:
    lesson_dir = _write_lesson(tmp_path)
    (lesson_dir / "audio.wav").unlink()

    with pytest.raises(ValidationError, match="missing required file"):
        load_raw_lesson(lesson_dir)


def test_load_raw_lesson_reports_meta_id_mismatch(tmp_path: Path) -> None:
    lesson_dir = _write_lesson(tmp_path)
    (lesson_dir / "meta.json").write_text(
        json.dumps({"id": "other", "title": "Hei", "source": "test", "language": "nb"}),
        encoding="utf-8",
    )

    with pytest.raises(ValidationError, match="does not match lesson folder"):
        load_raw_lesson(lesson_dir)


def test_load_raw_lesson_generates_default_meta_when_missing(tmp_path: Path) -> None:
    lesson_dir = _write_lesson(tmp_path, lesson_id="norwegian-999-test-lesson")
    (lesson_dir / "meta.json").unlink()

    lesson = load_raw_lesson(lesson_dir)

    assert lesson.meta.id == "norwegian-999-test-lesson"
    assert lesson.meta.title == "Norwegian 999 Test Lesson"
    assert lesson.meta.source == "Norwegian learning material"
    assert lesson.meta.language == "nb"
    assert lesson.meta.tags == ["norwegian", "shadowing"]
    assert lesson.meta.level.value == "unknown"
    assert lesson.meta.warnings


def test_load_raw_lesson_accepts_nb_text_suffix(tmp_path: Path) -> None:
    lesson_dir = _write_lesson(tmp_path)
    (lesson_dir / "original.nb.txt").write_text(
        (lesson_dir / "original.no.txt").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    (lesson_dir / "annotated.nb.txt").write_text(
        (lesson_dir / "annotated.no.txt").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    (lesson_dir / "original.no.txt").unlink()
    (lesson_dir / "annotated.no.txt").unlink()

    lesson = load_raw_lesson(lesson_dir)

    assert lesson.original_path.name == "original.nb.txt"
    assert lesson.annotated_path.name == "annotated.nb.txt"


def test_load_raw_lesson_normalizes_no_metadata_language_to_nb(tmp_path: Path) -> None:
    lesson_dir = _write_lesson(tmp_path)
    (lesson_dir / "meta.json").write_text(
        json.dumps({"id": "lesson-a", "title": "Hei", "source": "test", "language": "no"}),
        encoding="utf-8",
    )

    lesson = load_raw_lesson(lesson_dir)

    assert lesson.meta.language == "nb"
    assert any("normalized" in warning for warning in lesson.meta.warnings)
