"""Stage C: regenerate canonical annotated text from original + gloss reference."""

from __future__ import annotations

import json

from ..annotated_repair import repair_annotated_text
from ..errors import ValidationError
from ..language_config import DEFAULT_LANGUAGE
from .context import BuildContext, StageDiagnostics


def stage_regenerate_annotated(context: BuildContext) -> BuildContext:
    raw = context.raw_lesson
    if raw is None:
        raise ValidationError(
            f"Stage regenerate-annotated failed for {context.lesson_id}: raw lesson not loaded."
        )

    result = repair_annotated_text(
        lesson_id=raw.lesson_id,
        original_text=raw.original_text,
        annotated_text=raw.annotated_text,
        original_path=raw.original_path,
        annotated_path=raw.annotated_path,
    )
    context.output_dir.mkdir(parents=True, exist_ok=True)
    annotated_path = context.output_dir / DEFAULT_LANGUAGE.canonical_annotated_filename
    report_path = context.output_dir / "annotated.regeneration-report.json"
    annotated_path.write_text(result.text.rstrip() + "\n", encoding="utf-8")
    report_path.write_text(
        json.dumps(result.report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    context.canonical_annotated_text = result.text
    context.clean_text = raw.original_text
    context.regeneration_report = result.report
    context.add_diagnostics(
        StageDiagnostics(
            stage="regenerate-annotated",
            warnings=list(result.report.get("warnings", [])),
            artifacts={"canonicalAnnotated": str(annotated_path), "report": str(report_path)},
        )
    )
    return context
