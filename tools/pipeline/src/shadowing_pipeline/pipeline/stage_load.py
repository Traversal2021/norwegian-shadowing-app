"""Stage A: load raw lesson files."""

from __future__ import annotations

from pathlib import Path

from ..ingest import load_raw_lesson
from .context import BuildContext, StageDiagnostics


def stage_load(raw_dir: Path, output_dir: Path) -> BuildContext:
    raw_lesson = load_raw_lesson(raw_dir)
    context = BuildContext(
        lesson_id=raw_lesson.lesson_id,
        raw_dir=raw_lesson.root_dir,
        output_dir=output_dir,
        external_alignment_path=raw_lesson.root_dir / "alignment.external.json",
        raw_lesson=raw_lesson,
    )
    context.add_diagnostics(
        StageDiagnostics(
            stage="load",
            warnings=list(raw_lesson.meta.warnings),
            artifacts={
                "original": str(raw_lesson.original_path),
                "annotated": str(raw_lesson.annotated_path),
                "audio": str(raw_lesson.audio_path),
            },
        )
    )
    return context
