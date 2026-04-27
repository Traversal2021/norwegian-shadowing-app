"""Stage E: align segmented text to normalized audio."""

from __future__ import annotations

from ..align.base import AlignmentMode
from ..align.selector import align_segments
from ..errors import AlignmentError
from .context import BuildContext, StageDiagnostics


def stage_align_audio(
    context: BuildContext,
    *,
    aligner: AlignmentMode = "auto",
    strict_alignment: bool = False,
) -> BuildContext:
    if context.normalized_audio_path is None:
        raise AlignmentError(
            f"Stage align-audio failed for {context.lesson_id}: normalized audio missing."
        )
    if not context.seed_segments:
        raise AlignmentError(f"Stage align-audio failed for {context.lesson_id}: no segments to align.")
    if context.raw_lesson is None:
        raise AlignmentError(f"Stage align-audio failed for {context.lesson_id}: raw lesson missing.")

    context.alignment = align_segments(
        str(context.normalized_audio_path),
        context.seed_segments,
        lesson_id=context.lesson_id,
        language=context.raw_lesson.meta.language,
        transcript_path=str(context.raw_lesson.original_path),
        segments_json_path=str(context.output_dir / "sentence-segments.json"),
        external_alignment_path=(
            str(context.external_alignment_path) if context.external_alignment_path is not None else None
        ),
        requested=aligner,
        strict_alignment=strict_alignment,
    )
    if not context.alignment.segments or any(
        segment.end_time <= segment.start_time for segment in context.alignment.segments
    ):
        raise AlignmentError(
            f"Stage align-audio failed for {context.lesson_id}: alignment output missing valid timestamps."
        )
    context.add_diagnostics(
        StageDiagnostics(
            stage="align-audio",
            warnings=list(context.alignment.meta.warnings),
            notes=list(context.alignment.meta.notes),
        )
    )
    return context
