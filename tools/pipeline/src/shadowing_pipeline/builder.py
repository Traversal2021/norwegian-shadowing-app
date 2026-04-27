"""Staged lesson build orchestration."""

from __future__ import annotations

import shutil
from pathlib import Path

from .align.base import AlignmentMode
from .manifest import generate_manifest
from .pipeline.context import BuildContext
from .pipeline.stage_align_audio import stage_align_audio
from .pipeline.stage_export import stage_export
from .pipeline.stage_load import stage_load
from .pipeline.stage_manifest import stage_manifest
from .pipeline.stage_normalize_audio import stage_normalize_audio
from .pipeline.stage_regenerate_annotated import stage_regenerate_annotated
from .pipeline.stage_segment_sentences import stage_segment_sentences
from .pipeline.stage_validate import stage_validate

PROJECT_ROOT = Path(__file__).resolve().parents[4]
RAW_ROOT = PROJECT_ROOT / "content" / "raw"
PROCESSED_ROOT = PROJECT_ROOT / "content" / "processed"
WEB_LESSONS_ROOT = PROJECT_ROOT / "apps" / "web" / "public" / "lessons"
WEB_MANIFEST_PATH = WEB_LESSONS_ROOT / "index.json"


def build_lesson(
    raw_dir: str | Path,
    processed_root: str | Path = PROCESSED_ROOT,
    aligner: AlignmentMode = "auto",
    strict_alignment: bool = False,
    external_alignment_path: str | Path | None = None,
) -> Path:
    """Build one raw lesson through explicit ingestion stages."""
    context = build_lesson_context(
        raw_dir,
        processed_root=processed_root,
        aligner=aligner,
        strict_alignment=strict_alignment,
        external_alignment_path=external_alignment_path,
    )
    stage_manifest(Path(processed_root).resolve(), WEB_MANIFEST_PATH)
    return context.output_dir


def build_lesson_context(
    raw_dir: str | Path,
    processed_root: str | Path = PROCESSED_ROOT,
    aligner: AlignmentMode = "auto",
    strict_alignment: bool = False,
    external_alignment_path: str | Path | None = None,
) -> BuildContext:
    """Build one raw lesson and return the full inspectable context."""
    raw_path = Path(raw_dir).resolve()
    output_dir = Path(processed_root).resolve() / raw_path.name
    output_dir.mkdir(parents=True, exist_ok=True)

    context = stage_load(raw_path, output_dir)
    if external_alignment_path is not None:
        context.external_alignment_path = Path(external_alignment_path).resolve()
    context = stage_validate(context)
    context = stage_regenerate_annotated(context)
    context = stage_segment_sentences(context)
    context = stage_normalize_audio(context)
    context = stage_align_audio(context, aligner=aligner, strict_alignment=strict_alignment)
    context = stage_export(context)
    return context


def clean_processed_lesson(output_dir: str | Path) -> None:
    """Remove one processed lesson directory if it exists."""
    path = Path(output_dir).resolve()
    if path.exists():
        shutil.rmtree(path)


def refresh_manifest() -> Path:
    """Regenerate the web lesson manifest from processed outputs."""
    return generate_manifest(PROCESSED_ROOT, WEB_MANIFEST_PATH)
