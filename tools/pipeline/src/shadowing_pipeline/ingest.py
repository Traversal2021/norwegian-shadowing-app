"""
Raw lesson ingestion and validation.

Expected lesson layout:

    content/raw/<lesson-id>/
      original.no.txt
      annotated.no.txt
      audio.wav
      meta.json          optional
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .errors import ValidationError
from .language_config import DEFAULT_LANGUAGE
from .models import LessonLevel, RawLesson, RawLessonMeta

AUDIO_FILENAME = "audio.wav"


def load_raw_lesson(raw_dir: str | Path) -> RawLesson:
    """Load, validate, and normalize one raw lesson directory."""
    root = Path(raw_dir).resolve()
    if not root.is_dir():
        raise ValidationError(f"Raw lesson directory does not exist: {root}")

    original_path, annotated_path = resolve_lesson_text_paths(root)
    _require_audio_file(root)

    original_text = _load_text_file(original_path)
    annotated_text = _load_text_file(annotated_path)
    meta = _load_meta(root / "meta.json", expected_lesson_id=root.name)

    return RawLesson(
        lesson_id=meta.id,
        root_dir=root,
        original_text=original_text,
        annotated_text=annotated_text,
        original_path=original_path.resolve(),
        annotated_path=annotated_path.resolve(),
        audio_path=(root / AUDIO_FILENAME).resolve(),
        meta=meta,
        vocab_path=_optional_summary_path(root, "vocab"),
        grammar_path=_optional_summary_path(root, "grammar"),
    )


def validate_raw_lesson(raw_dir: str | Path) -> RawLessonMeta:
    """Validate one raw lesson directory and return parsed metadata."""
    return load_raw_lesson(raw_dir).meta


def list_raw_lesson_dirs(raw_root: str | Path) -> list[Path]:
    """Return complete raw lesson directories sorted by name."""
    root = Path(raw_root).resolve()
    if not root.exists():
        return []
    return sorted(
        entry
        for entry in root.iterdir()
        if entry.is_dir() and not entry.name.startswith(".") and (entry / AUDIO_FILENAME).is_file()
    )


def resolve_lesson_text_paths(root: Path) -> tuple[Path, Path]:
    for suffix in DEFAULT_LANGUAGE.accepted_raw_suffixes:
        original = root / f"original.{suffix}.txt"
        annotated = root / f"annotated.{suffix}.txt"
        if original.is_file() and annotated.is_file():
            return original, annotated

    accepted_pairs = ", ".join(
        f"original.{suffix}.txt + annotated.{suffix}.txt"
        for suffix in DEFAULT_LANGUAGE.accepted_raw_suffixes
    )
    raise ValidationError(
        f"Lesson '{root.name}' is missing required Norwegian text files: "
        f"{DEFAULT_LANGUAGE.original_filename} and {DEFAULT_LANGUAGE.annotated_filename}. "
        f"Accepted pairs: {accepted_pairs}."
    )


def _require_audio_file(root: Path) -> None:
    if not (root / AUDIO_FILENAME).is_file():
        raise ValidationError(f"Lesson '{root.name}' is missing required file(s): {AUDIO_FILENAME}")


def _load_text_file(path: Path) -> str:
    try:
        content = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise ValidationError(f"File must be valid UTF-8: {path}") from exc

    normalized = _normalize_text(content)
    if not normalized:
        raise ValidationError(f"Required text file is empty after normalization: {path}")
    return normalized


def _normalize_text(text: str) -> str:
    lines = [" ".join(line.strip().split()) for line in text.replace("\r\n", "\n").split("\n")]
    return "\n".join(line for line in lines if line)


def _load_meta(meta_path: Path, expected_lesson_id: str) -> RawLessonMeta:
    warnings: list[str] = []
    if not meta_path.is_file():
        warnings.append("meta.json missing; generated default metadata from lesson folder name.")
        return RawLessonMeta(
            id=expected_lesson_id,
            title=_title_from_lesson_id(expected_lesson_id),
            source=DEFAULT_LANGUAGE.default_source,
            language=DEFAULT_LANGUAGE.metadata_language,
            tags=list(DEFAULT_LANGUAGE.default_tags),
            level=LessonLevel.from_meta(DEFAULT_LANGUAGE.default_level),
            warnings=warnings,
        )

    try:
        payload = json.loads(meta_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValidationError(f"Invalid JSON in {meta_path}: {exc}") from exc

    if not isinstance(payload, dict):
        raise ValidationError(f"meta.json must contain an object: {meta_path}")

    lesson_id = _optional_non_empty_string(payload, "id", meta_path)
    if not lesson_id:
        lesson_id = expected_lesson_id
        warnings.append("meta.json missing id; inferred id from lesson folder name.")
    if lesson_id != expected_lesson_id:
        raise ValidationError(
            f"meta.json id {lesson_id!r} does not match lesson folder name {expected_lesson_id!r}"
        )

    language = (
        _optional_non_empty_string(payload, "language", meta_path)
        or DEFAULT_LANGUAGE.metadata_language
    ).lower()
    if "language" not in payload:
        warnings.append(
            f"meta.json missing language; defaulted to '{DEFAULT_LANGUAGE.metadata_language}'."
        )
    if language == DEFAULT_LANGUAGE.asr_language:
        language = DEFAULT_LANGUAGE.metadata_language
        warnings.append(
            f"meta.json language '{DEFAULT_LANGUAGE.asr_language}' normalized to "
            f"'{DEFAULT_LANGUAGE.metadata_language}' for {DEFAULT_LANGUAGE.written_standard} metadata."
        )
    if language != DEFAULT_LANGUAGE.metadata_language:
        raise ValidationError(
            f"Lesson '{lesson_id}' has unsupported language {language!r}; "
            f"expected '{DEFAULT_LANGUAGE.metadata_language}'."
        )

    tags = _parse_tags(payload.get("tags"), lesson_id)
    if "tags" not in payload:
        tags = list(DEFAULT_LANGUAGE.default_tags)
        warnings.append("meta.json missing tags; defaulted to Norwegian shadowing tags.")

    return RawLessonMeta(
        id=lesson_id,
        title=_optional_non_empty_string(payload, "title", meta_path)
        or _title_from_lesson_id(expected_lesson_id),
        source=_optional_non_empty_string(payload, "source", meta_path)
        or DEFAULT_LANGUAGE.default_source,
        language=language,
        tags=tags,
        description=_optional_string(payload.get("description")),
        level=LessonLevel.from_meta(payload.get("level", DEFAULT_LANGUAGE.default_level)),
        warnings=warnings
        + _missing_optional_meta_warnings(payload, ("title", "source"), meta_path.name),
    )


def _require_non_empty_string(payload: dict[str, Any], key: str, meta_path: Path) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"meta.json key {key!r} must be a non-empty string in {meta_path}")
    return value.strip()


def _optional_non_empty_string(payload: dict[str, Any], key: str, meta_path: Path) -> str | None:
    value = payload.get(key)
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"meta.json key {key!r} must be a non-empty string in {meta_path}")
    return value.strip()


def _optional_string(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    raise ValidationError("Optional meta.json string fields must be strings when provided.")


def _parse_tags(value: object, lesson_id: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValidationError(f"Lesson '{lesson_id}' tags must be an array of strings.")
    return [item.strip() for item in value if item.strip()]


def _optional_summary_path(root: Path, stem: str) -> Path | None:
    json_path = root / f"{stem}.json"
    md_path = root / f"{stem}.md"
    if json_path.is_file():
        return json_path.resolve()
    if md_path.is_file():
        return md_path.resolve()
    return None


def _title_from_lesson_id(lesson_id: str) -> str:
    return " ".join(part for part in lesson_id.replace("_", "-").split("-") if part).title()


def _missing_optional_meta_warnings(payload: dict[str, Any], keys: tuple[str, ...], name: str) -> list[str]:
    return [f"{name} missing {key}; inferred default value." for key in keys if key not in payload]
