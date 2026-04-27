"""Stage B: validate normalized raw inputs."""

from __future__ import annotations

from ..errors import ValidationError
from .context import BuildContext, StageDiagnostics


def stage_validate(context: BuildContext) -> BuildContext:
    raw = context.raw_lesson
    if raw is None:
        raise ValidationError(f"Stage validate failed for {context.lesson_id}: raw lesson not loaded.")
    if not raw.original_text.strip():
        raise ValidationError(f"Stage validate failed for {context.lesson_id}: {raw.original_path.name} is empty.")
    if not raw.annotated_text.strip():
        raise ValidationError(f"Stage validate failed for {context.lesson_id}: {raw.annotated_path.name} is empty.")
    if not raw.audio_path.is_file():
        raise ValidationError(
            f"Stage validate failed for {context.lesson_id}: missing audio file {raw.audio_path}."
        )
    context.add_diagnostics(StageDiagnostics(stage="validate"))
    return context
