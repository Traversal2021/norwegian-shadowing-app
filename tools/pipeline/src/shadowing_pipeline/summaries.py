"""Manual vocab/grammar summary sidecar parsing for Phase 4."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .errors import ValidationError
from .models import GrammarItem, VocabItem


def load_vocab_summary(path: Path | None) -> list[VocabItem]:
    """Load optional vocab sidecar data."""
    if path is None:
        return []
    if path.suffix == ".json":
        payload = _load_json_array(path)
        return [_parse_vocab_dict(item, path) for item in payload]
    if path.suffix == ".md":
        return [_parse_vocab_block(block, path) for block in _parse_markdown_blocks(path)]
    raise ValidationError(f"Unsupported vocab summary file type: {path}")


def load_grammar_summary(path: Path | None) -> list[GrammarItem]:
    """Load optional grammar sidecar data."""
    if path is None:
        return []
    if path.suffix == ".json":
        payload = _load_json_array(path)
        return [_parse_grammar_dict(item, path) for item in payload]
    if path.suffix == ".md":
        return [_parse_grammar_block(block, path) for block in _parse_markdown_blocks(path)]
    raise ValidationError(f"Unsupported grammar summary file type: {path}")


def _load_json_array(path: Path) -> list[dict[str, Any]]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValidationError(f"Invalid JSON summary file {path}: {exc}") from exc
    if not isinstance(payload, list):
        raise ValidationError(f"Summary JSON must be an array: {path}")
    if not all(isinstance(item, dict) for item in payload):
        raise ValidationError(f"Summary JSON items must be objects: {path}")
    return payload


def _parse_vocab_dict(item: dict[str, Any], path: Path) -> VocabItem:
    return VocabItem(
        word=_required_string(item, "word", path),
        definition=_required_string(item, "definition", path),
        example=_optional_string(item.get("example"), path),
    )


def _parse_grammar_dict(item: dict[str, Any], path: Path) -> GrammarItem:
    return GrammarItem(
        title=_required_string(item, "title", path),
        explanation=_required_string(item, "explanation", path),
        example=_optional_string(item.get("example"), path),
    )


def _parse_markdown_blocks(path: Path) -> list[dict[str, str]]:
    blocks: list[dict[str, str]] = []
    current: dict[str, str] | None = None

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("## "):
            if current:
                blocks.append(current)
            current = {"title": line[3:].strip()}
            continue
        if current is None:
            raise ValidationError(f"Markdown summary must start items with '## Heading': {path}")
        if ":" not in line:
            raise ValidationError(f"Markdown summary field must use 'key: value': {path}: {line}")
        key, value = line.split(":", 1)
        current[key.strip().lower()] = value.strip()

    if current:
        blocks.append(current)
    return blocks


def _parse_vocab_block(block: dict[str, str], path: Path) -> VocabItem:
    return VocabItem(
        word=block.get("word") or _required_block_string(block, "title", path),
        definition=_required_block_string(block, "definition", path),
        example=block.get("example") or None,
    )


def _parse_grammar_block(block: dict[str, str], path: Path) -> GrammarItem:
    return GrammarItem(
        title=block.get("title") or _required_block_string(block, "title", path),
        explanation=_required_block_string(block, "explanation", path),
        example=block.get("example") or None,
    )


def _required_string(item: dict[str, Any], key: str, path: Path) -> str:
    value = item.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"Summary item in {path} missing non-empty string field {key!r}.")
    return value.strip()


def _optional_string(value: object, path: Path) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValidationError(f"Optional summary field in {path} must be a string.")
    return value.strip() or None


def _required_block_string(block: dict[str, str], key: str, path: Path) -> str:
    value = block.get(key, "").strip()
    if not value:
        raise ValidationError(f"Markdown summary item in {path} missing field {key!r}.")
    return value
