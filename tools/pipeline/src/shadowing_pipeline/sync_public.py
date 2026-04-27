"""Copy processed lessons into the web app public directory."""

from __future__ import annotations

import shutil
import json
from pathlib import Path

from .language_config import DEFAULT_LANGUAGE
from .builder import PROCESSED_ROOT, WEB_LESSONS_ROOT, refresh_manifest

# Only these files are needed by the web app.
_WEB_FILES = {"audio.mp3", "lesson.json", "captions.vtt"}


def sync_processed_lessons_to_public(
    processed_root: str | Path = PROCESSED_ROOT,
    public_lessons_root: str | Path = WEB_LESSONS_ROOT,
) -> None:
    """Copy only web-serving assets into ``apps/web/public/lessons``."""
    processed_dir = Path(processed_root).resolve()
    public_dir = Path(public_lessons_root).resolve()
    public_dir.mkdir(parents=True, exist_ok=True)
    if not processed_dir.exists():
        refresh_manifest()
        return

    synced_lesson_ids: set[str] = set()
    for lesson_dir in sorted(
        entry for entry in processed_dir.iterdir() if entry.is_dir() and not entry.name.startswith(".")
    ):
        if not _is_current_language_lesson(lesson_dir):
            continue
        destination = public_dir / lesson_dir.name
        destination.mkdir(parents=True, exist_ok=True)
        for filename in _WEB_FILES:
            src = lesson_dir / filename
            if src.is_file():
                shutil.copy2(src, destination / filename)
        synced_lesson_ids.add(lesson_dir.name)

    for public_lesson_dir in sorted(
        entry for entry in public_dir.iterdir() if entry.is_dir() and not entry.name.startswith(".")
    ):
        if public_lesson_dir.name not in synced_lesson_ids:
            shutil.rmtree(public_lesson_dir)

    refresh_manifest()


def _is_current_language_lesson(lesson_dir: Path) -> bool:
    lesson_json_path = lesson_dir / "lesson.json"
    if not lesson_json_path.is_file():
        return False
    try:
        payload = json.loads(lesson_json_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return False
    return payload.get("language") == DEFAULT_LANGUAGE.metadata_language


def main() -> None:
    sync_processed_lessons_to_public()


if __name__ == "__main__":
    main()
