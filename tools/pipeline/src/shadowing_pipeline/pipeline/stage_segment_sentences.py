"""Stage D: sentence segmentation."""

from __future__ import annotations

import json

from ..errors import ValidationError
from ..models import Segment
from ..parse_annotations import parse_annotated_line
from ..segmentation.spacy_sentences import segment_sentences
from .context import BuildContext, StageDiagnostics


def stage_segment_sentences(context: BuildContext) -> BuildContext:
    raw = context.raw_lesson
    if raw is None:
        raise ValidationError(f"Stage segmentation failed for {context.lesson_id}: raw lesson not loaded.")

    result = segment_sentences(raw.original_text)
    if not result.segments:
        raise ValidationError(
            f"Stage segmentation failed for {context.lesson_id}: no sentence segments produced."
        )

    context.segmentation = result
    canonical_by_sentence = segment_sentences(context.canonical_annotated_text).segments
    seed_segments: list[Segment] = []
    for index, sentence in enumerate(result.segments):
        annotated = (
            canonical_by_sentence[index].text
            if index < len(canonical_by_sentence)
            else sentence.text
        )
        seed_segments.append(
            Segment(
                id=sentence.id,
                start_time=0.0,
                end_time=0.0,
                tokens=parse_annotated_line(annotated),
                text_plain=sentence.text,
                text_annotated=annotated,
            )
        )
    context.seed_segments = seed_segments

    output_path = context.output_dir / "sentence-segments.json"
    output_path.write_text(
        json.dumps(
            {
                "schemaVersion": 1,
                "lessonId": context.lesson_id,
                "backend": result.backend,
                "warnings": result.warnings,
                "segments": [
                    {
                        "id": segment.id,
                        "text": segment.text,
                        "startChar": segment.start_char,
                        "endChar": segment.end_char,
                        "tokenCount": segment.token_count,
                        "diagnostics": segment.diagnostics,
                    }
                    for segment in result.segments
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    context.add_diagnostics(
        StageDiagnostics(
            stage="segment-sentences",
            warnings=list(result.warnings),
            artifacts={"sentenceSegments": str(output_path)},
        )
    )
    return context
