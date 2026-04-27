"""Manifest generation for the web app lesson library."""

from __future__ import annotations

import json
from pathlib import Path

from .language_config import DEFAULT_LANGUAGE
from .models import LessonLevel, ManifestEntry


def generate_manifest(processed_root: str | Path, output_path: str | Path) -> Path:
    """Generate ``apps/web/public/lessons/index.json`` from processed lessons."""
    processed_dir = Path(processed_root).resolve()
    entries: list[ManifestEntry] = []

    if processed_dir.exists():
        for lesson_dir in sorted(
            entry for entry in processed_dir.iterdir() if entry.is_dir() and not entry.name.startswith(".")
        ):
            lesson_json_path = lesson_dir / "lesson.json"
            build_report_path = lesson_dir / "build-report.json"
            if not lesson_json_path.is_file() or not build_report_path.is_file():
                continue
            entry = _load_manifest_entry(lesson_dir, lesson_json_path, build_report_path)
            if entry.language == DEFAULT_LANGUAGE.metadata_language:
                entries.append(entry)

    payload = [
        {
            "id": entry.id,
            "title": entry.title,
            "source": entry.source,
            "language": entry.language,
            "tags": entry.tags,
            "audioSrc": entry.audio_src,
            "lessonJsonSrc": entry.lesson_json_src,
            "captionsSrc": entry.captions_src,
            "durationSec": entry.duration_sec,
            "segmentCount": entry.segment_count,
            "description": entry.description,
            "level": entry.level.value,
            "alignerUsed": entry.aligner_used,
            "builtAt": entry.built_at,
        }
        for entry in entries
    ]

    destination = Path(output_path).resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return destination


def _load_manifest_entry(
    lesson_dir: Path,
    lesson_json_path: Path,
    build_report_path: Path,
) -> ManifestEntry:
    lesson_payload = json.loads(lesson_json_path.read_text(encoding="utf-8"))
    report_payload = json.loads(build_report_path.read_text(encoding="utf-8"))
    meta = report_payload["meta"]
    alignment = report_payload.get("alignment", {})

    return ManifestEntry(
        id=lesson_payload["id"],
        title=lesson_payload["title"],
        source=meta["source"],
        language=meta["language"],
        tags=meta.get("tags", []),
        audio_src=f"/lessons/{lesson_dir.name}/audio.mp3",
        lesson_json_src=f"/lessons/{lesson_dir.name}/lesson.json",
        captions_src=f"/lessons/{lesson_dir.name}/captions.vtt",
        duration_sec=lesson_payload["durationSeconds"],
        segment_count=len(lesson_payload["segments"]),
        description=lesson_payload.get("description", ""),
        level=LessonLevel.from_meta(lesson_payload.get("level", DEFAULT_LANGUAGE.default_level)),
        aligner_used=alignment.get("alignerUsed", ""),
        built_at=report_payload.get("processedAt", lesson_payload.get("createdAt", "")),
    )
