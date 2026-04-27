"""Tests for generated lesson manifest shape."""

from __future__ import annotations

import json
from pathlib import Path

from shadowing_pipeline.manifest import generate_manifest


def test_generate_manifest_from_processed_lessons(tmp_path: Path) -> None:
    lesson_dir = tmp_path / "processed" / "lesson-a"
    lesson_dir.mkdir(parents=True)
    (lesson_dir / "lesson.json").write_text(
        json.dumps(
            {
                "id": "lesson-a",
                "title": "Hei",
                "description": "A short lesson",
                "level": "beginner",
                "durationSeconds": 4.2,
                "createdAt": "2026-04-23T00:00:00+00:00",
                "segments": [{"id": "s1"}],
            }
        ),
        encoding="utf-8",
    )
    (lesson_dir / "build-report.json").write_text(
        json.dumps(
            {
                "meta": {"source": "test", "language": "nb", "tags": ["tag"]},
                "alignment": {"alignerUsed": "fallback"},
                "processedAt": "2026-04-23T00:00:00+00:00",
            }
        ),
        encoding="utf-8",
    )

    output_path = generate_manifest(tmp_path / "processed", tmp_path / "public" / "index.json")
    payload = json.loads(output_path.read_text(encoding="utf-8"))

    assert payload == [
        {
            "id": "lesson-a",
            "title": "Hei",
            "source": "test",
            "language": "nb",
            "tags": ["tag"],
            "audioSrc": "/lessons/lesson-a/audio.mp3",
            "lessonJsonSrc": "/lessons/lesson-a/lesson.json",
            "captionsSrc": "/lessons/lesson-a/captions.vtt",
            "durationSec": 4.2,
            "segmentCount": 1,
            "description": "A short lesson",
            "level": "beginner",
            "alignerUsed": "fallback",
            "builtAt": "2026-04-23T00:00:00+00:00",
        }
    ]
