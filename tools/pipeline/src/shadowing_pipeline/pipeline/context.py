"""Shared dataclasses for staged ingestion."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..models import AlignmentResult, Lesson, RawLesson, Segment
from ..segmentation.spacy_sentences import SentenceSegmentationResult


@dataclass
class StageDiagnostics:
    stage: str
    warnings: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    artifacts: dict[str, str] = field(default_factory=dict)


@dataclass
class BuildContext:
    lesson_id: str
    raw_dir: Path
    output_dir: Path
    external_alignment_path: Path | None = None
    raw_lesson: RawLesson | None = None
    canonical_annotated_text: str = ""
    clean_text: str = ""
    regeneration_report: dict[str, Any] = field(default_factory=dict)
    segmentation: SentenceSegmentationResult | None = None
    seed_segments: list[Segment] = field(default_factory=list)
    normalized_audio_path: Path | None = None
    audio_mp3_path: Path | None = None
    audio_probe: dict[str, Any] = field(default_factory=dict)
    duration_seconds: float = 0.0
    alignment: AlignmentResult | None = None
    lesson: Lesson | None = None
    diagnostics: list[StageDiagnostics] = field(default_factory=list)

    def add_diagnostics(self, diagnostics: StageDiagnostics) -> None:
        self.diagnostics.append(diagnostics)

    @property
    def warnings(self) -> list[str]:
        result: list[str] = []
        for item in self.diagnostics:
            result.extend(item.warnings)
        if self.alignment:
            result.extend(self.alignment.meta.warnings)
        return result
