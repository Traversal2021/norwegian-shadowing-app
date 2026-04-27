"""Stage F: export processed artifacts for the web app."""

from __future__ import annotations

import json
from datetime import UTC, datetime

from ..errors import PipelineError
from ..exporters.lesson_json import export_lesson_json
from ..exporters.vtt import export_vtt
from ..language_config import DEFAULT_LANGUAGE
from ..models import AlignmentItem, Lesson
from ..text_utils import tokens_to_text
from ..summaries import load_grammar_summary, load_vocab_summary
from .context import BuildContext, StageDiagnostics


def stage_export(context: BuildContext) -> BuildContext:
    raw = context.raw_lesson
    alignment = context.alignment
    if raw is None or alignment is None:
        raise PipelineError(f"Stage export failed for {context.lesson_id}: missing raw/alignment data.")

    vocab = load_vocab_summary(raw.vocab_path)
    grammar = load_grammar_summary(raw.grammar_path)
    duration = context.duration_seconds or (
        alignment.segments[-1].end_time if alignment.segments else 0.0
    )
    built_at = datetime.now(UTC).isoformat()

    lesson = Lesson(
        id=raw.meta.id,
        title=raw.meta.title,
        source=raw.meta.source,
        language=raw.meta.language,
        tags=raw.meta.tags,
        description=raw.meta.description or raw.meta.source,
        level=raw.meta.level,
        duration_seconds=duration,
        audio_file="audio.mp3",
        segments=alignment.segments,
        vocab=vocab,
        grammar=grammar,
        created_at=built_at,
        alignment_meta=alignment.meta,
    )
    context.lesson = lesson

    clean_path = context.output_dir / DEFAULT_LANGUAGE.clean_text_filename
    clean_path.write_text(raw.original_text.rstrip() + "\n", encoding="utf-8")
    export_lesson_json(lesson, context.output_dir / "lesson.json")
    export_vtt(lesson, context.output_dir / "captions.vtt")
    _export_alignment(context, context.output_dir / "alignment.json")
    _export_build_report(context, context.output_dir / "build-report.json")

    context.add_diagnostics(
        StageDiagnostics(
            stage="export",
            artifacts={
                "lessonJson": str(context.output_dir / "lesson.json"),
                "captions": str(context.output_dir / "captions.vtt"),
                "alignment": str(context.output_dir / "alignment.json"),
                "cleanText": str(clean_path),
            },
        )
    )
    return context


def _export_alignment(context: BuildContext, output_path) -> None:
    alignment = context.alignment
    raw = context.raw_lesson
    if alignment is None or raw is None:
        raise PipelineError(f"Stage export failed for {context.lesson_id}: missing alignment.")
    items = [
        AlignmentItem(
            id=segment.id,
            text=segment.text_plain or tokens_to_text(segment.tokens),
            start_time=segment.start_time,
            end_time=segment.end_time,
            tokens=segment.tokens,
            notes=[],
        )
        for segment in alignment.segments
    ]
    payload = {
        "schemaVersion": 2,
        "lessonId": context.lesson_id,
        "alignerRequested": alignment.meta.aligner_requested,
        "alignerUsed": alignment.meta.aligner_used,
        "fallbackOccurred": alignment.meta.fallback_occurred,
        "hasTokenTimings": alignment.meta.has_token_timings,
        "externalAlignmentPath": alignment.meta.external_alignment_path,
        "warnings": alignment.meta.warnings,
        "notes": alignment.meta.notes,
        "segments": [
            {
                "id": item.id,
                "text": item.text,
                "start": item.start_time,
                "end": item.end_time,
                "startTime": item.start_time,
                "endTime": item.end_time,
                "tokens": [
                    {
                        "index": index,
                        "text": token.text,
                        **({"start": token.start} if token.start is not None else {}),
                        **({"end": token.end} if token.end is not None else {}),
                        **({"confidence": token.confidence} if token.confidence is not None else {}),
                    }
                    for index, token in enumerate(item.tokens)
                    if token.start is not None or token.end is not None or token.confidence is not None
                ],
            }
            for item in items
        ],
    }
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _export_build_report(context: BuildContext, output_path) -> None:
    raw = context.raw_lesson
    lesson = context.lesson
    alignment = context.alignment
    if raw is None or lesson is None or alignment is None:
        raise PipelineError(f"Stage export failed for {context.lesson_id}: incomplete context.")

    payload = {
        "schemaVersion": 2,
        "lessonId": lesson.id,
        "meta": {
            "id": raw.meta.id,
            "title": raw.meta.title,
            "source": raw.meta.source,
            "language": raw.meta.language,
            "tags": raw.meta.tags,
            "description": raw.meta.description,
            "level": raw.meta.level.value,
        },
        "sourcePaths": {
            "rawLessonDir": str(raw.root_dir),
            "originalText": str(raw.original_path),
            "annotatedText": str(raw.annotated_path),
            "audio": str(raw.audio_path),
            "meta": str(raw.root_dir / "meta.json") if (raw.root_dir / "meta.json").is_file() else None,
            "vocab": str(raw.vocab_path) if raw.vocab_path else None,
            "grammar": str(raw.grammar_path) if raw.grammar_path else None,
        },
        "outputPaths": {
            "processedLessonDir": str(context.output_dir),
            "audio": str(context.output_dir / "audio.mp3"),
            "normalizedAudio": str(context.normalized_audio_path) if context.normalized_audio_path else None,
            "lessonJson": str(context.output_dir / "lesson.json"),
            "captions": str(context.output_dir / "captions.vtt"),
            "alignment": str(context.output_dir / "alignment.json"),
            "canonicalAnnotated": str(context.output_dir / DEFAULT_LANGUAGE.canonical_annotated_filename),
            "sentenceSegments": str(context.output_dir / "sentence-segments.json"),
            "cleanText": str(context.output_dir / DEFAULT_LANGUAGE.clean_text_filename),
            "buildReport": str(output_path),
        },
        "audio": {
            "durationSeconds": context.duration_seconds,
            "probe": context.audio_probe,
        },
        "regeneration": context.regeneration_report,
        "segmentation": {
            "backend": context.segmentation.backend if context.segmentation else None,
            "segmentCount": len(context.segmentation.segments) if context.segmentation else 0,
        },
        "duration": lesson.duration_seconds,
        "segmentCount": len(lesson.segments),
        "vocabCount": len(lesson.vocab),
        "grammarCount": len(lesson.grammar),
        "alignment": {
            "alignerRequested": alignment.meta.aligner_requested,
            "alignerUsed": alignment.meta.aligner_used,
            "fallbackOccurred": alignment.meta.fallback_occurred,
            "hasTokenTimings": alignment.meta.has_token_timings,
            "strictAlignment": alignment.meta.strict_alignment,
            "externalAlignmentPath": alignment.meta.external_alignment_path,
            "notes": alignment.meta.notes,
        },
        "stages": [
            {
                "stage": item.stage,
                "warnings": item.warnings,
                "notes": item.notes,
                "artifacts": item.artifacts,
            }
            for item in context.diagnostics
        ],
        "processedAt": lesson.created_at,
        "warnings": context.warnings,
    }
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
