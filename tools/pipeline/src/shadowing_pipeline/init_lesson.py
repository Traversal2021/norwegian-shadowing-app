"""Raw lesson template generation."""

from __future__ import annotations

import json
from pathlib import Path

from .builder import RAW_ROOT
from .errors import ValidationError
from .language_config import DEFAULT_LANGUAGE


def init_lesson(lesson_id: str, title: str, raw_root: str | Path = RAW_ROOT) -> Path:
    """Create a raw lesson folder with Phase 4 template files."""
    if not lesson_id or "/" in lesson_id or lesson_id.startswith("."):
        raise ValidationError(f"Invalid lesson id: {lesson_id!r}")
    root = Path(raw_root).resolve() / lesson_id
    if root.exists() and any(root.iterdir()):
        raise ValidationError(f"Raw lesson folder already exists and is not empty: {root}")
    root.mkdir(parents=True, exist_ok=True)

    _write_if_missing(root / DEFAULT_LANGUAGE.original_filename, "Skriv den rene norske teksten her.\n")
    _write_if_missing(
        root / DEFAULT_LANGUAGE.annotated_filename,
        "Skriv (write) den rene norske teksten (text) her.\n",
    )
    _write_if_missing(root / "vocab.md", "## eksempel\nDefinition: example\nExample: Et eksempel.\n")
    _write_if_missing(
        root / "grammar.md",
        "## Grammar note title\nExplanation: Short explanation.\nExample: Norsk eksempel.\n",
    )
    _write_if_missing(root / "audio.wav", b"")
    _write_if_missing(
        root / "meta.json",
        json.dumps(
            {
                "id": lesson_id,
                "title": title,
                "source": DEFAULT_LANGUAGE.default_source,
                "language": DEFAULT_LANGUAGE.metadata_language,
                "description": "",
                "level": DEFAULT_LANGUAGE.default_level,
                "tags": list(DEFAULT_LANGUAGE.default_tags),
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
    )
    return root


def _write_if_missing(path: Path, content: str | bytes) -> None:
    if path.exists():
        return
    if isinstance(content, bytes):
        path.write_bytes(content)
    else:
        path.write_text(content, encoding="utf-8")
