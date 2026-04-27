"""Exporter for ``lesson.json`` matching the web app schema."""

from __future__ import annotations

import json
from pathlib import Path

from ..models import Lesson, Token
from ..text_utils import tokens_to_text


def export_lesson_json(lesson: Lesson, output_path: str | Path) -> Path:
    """Write the lesson payload to disk as formatted JSON."""
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(_lesson_to_dict(lesson), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return output.resolve()


def _lesson_to_dict(lesson: Lesson) -> dict[str, object]:
    return {
        "schemaVersion": lesson.schema_version,
        "id": lesson.id,
        "title": lesson.title,
        "source": lesson.source,
        "language": lesson.language,
        "description": lesson.description,
        "level": lesson.level.value,
        "tags": lesson.tags,
        "durationSeconds": lesson.duration_seconds,
        "audioFile": lesson.audio_file,
        "createdAt": lesson.created_at,
        "segments": [
            {
                "id": segment.id,
                "textPlain": segment.text_plain or tokens_to_text(segment.tokens),
                "textAnnotated": segment.text_annotated or _tokens_to_annotated_text(segment),
                "start": segment.start_time,
                "end": segment.end_time,
                "startTime": segment.start_time,
                "endTime": segment.end_time,
                "tokens": [
                    {
                        "text": token.text,
                        **({"gloss": token.gloss} if token.gloss else {}),
                        **({"start": token.start} if token.start is not None else {}),
                        **({"end": token.end} if token.end is not None else {}),
                        **(
                            {"confidence": token.confidence}
                            if token.confidence is not None
                            else {}
                        ),
                    }
                    for token in segment.tokens
                ],
                **({"translation": segment.translation} if segment.translation else {}),
            }
            for segment in lesson.segments
        ],
        "vocab": [
            {
                "word": item.word,
                "definition": item.definition,
                **({"example": item.example} if item.example else {}),
            }
            for item in lesson.vocab
        ],
        "vocabSummary": [
            {
                "word": item.word,
                "definition": item.definition,
                **({"example": item.example} if item.example else {}),
            }
            for item in lesson.vocab
        ],
        "grammar": [
            {
                "title": item.title,
                "explanation": item.explanation,
                **({"example": item.example} if item.example else {}),
            }
            for item in lesson.grammar
        ],
        "grammarSummary": [
            {
                "title": item.title,
                "explanation": item.explanation,
                **({"example": item.example} if item.example else {}),
            }
            for item in lesson.grammar
        ],
        **(
            {
                "alignmentMeta": {
                    "alignerRequested": lesson.alignment_meta.aligner_requested,
                    "alignerUsed": lesson.alignment_meta.aligner_used,
                    "fallbackOccurred": lesson.alignment_meta.fallback_occurred,
                    "hasTokenTimings": lesson.alignment_meta.has_token_timings,
                    "strictAlignment": lesson.alignment_meta.strict_alignment,
                    "externalAlignmentPath": lesson.alignment_meta.external_alignment_path,
                    "warnings": lesson.alignment_meta.warnings,
                    "notes": lesson.alignment_meta.notes,
                }
            }
            if lesson.alignment_meta
            else {}
        ),
    }


def _tokens_to_annotated_text(segment) -> str:
    return tokens_to_text(
        [
            Token(text=token.text + (f"({token.gloss})" if token.gloss else ""))
            for token in segment.tokens
        ]
    )
