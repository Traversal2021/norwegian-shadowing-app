"""
Core dataclasses for the Norwegian Shadowing pipeline.

The exported ``Lesson`` structure mirrors the TypeScript schema in
``apps/web/src/types/lesson.ts``. Supporting dataclasses model the raw lesson
inputs, merged sentence pairs, alignment payload, and manifest entries used by
the build flow.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional


class LessonLevel(str, Enum):
    """Web-app lesson difficulty labels."""

    UNKNOWN = "unknown"
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"

    @classmethod
    def from_meta(cls, value: object) -> "LessonLevel":
        """Parse an optional meta.json level, defaulting to unknown."""
        if value is None:
            return cls.UNKNOWN
        if isinstance(value, cls):
            return value
        if isinstance(value, str):
            normalized = value.strip().lower()
            for member in cls:
                if member.value == normalized:
                    return member
        raise ValueError(
            f"Invalid lesson level {value!r}. Expected one of: "
            f"{', '.join(member.value for member in cls)}."
        )


@dataclass(frozen=True)
class Token:
    """One word or punctuation unit in a segment."""

    text: str
    gloss: Optional[str] = None
    start: Optional[float] = None
    end: Optional[float] = None
    confidence: Optional[float] = None


@dataclass(frozen=True)
class Segment:
    """One time-aligned sentence-sized chunk of audio and text."""

    id: str
    start_time: float
    end_time: float
    tokens: list[Token] = field(default_factory=list)
    translation: Optional[str] = None
    text_plain: str = ""
    text_annotated: str = ""


@dataclass(frozen=True)
class VocabItem:
    word: str
    definition: str
    example: Optional[str] = None


@dataclass(frozen=True)
class GrammarItem:
    title: str
    explanation: str
    example: Optional[str] = None


@dataclass(frozen=True)
class Lesson:
    """Top-level lesson.json payload consumed by the web app."""

    id: str
    title: str
    description: str
    level: LessonLevel
    duration_seconds: float
    audio_file: str
    segments: list[Segment] = field(default_factory=list)
    vocab: list[VocabItem] = field(default_factory=list)
    grammar: list[GrammarItem] = field(default_factory=list)
    created_at: str = ""
    alignment_meta: Optional["AlignmentMeta"] = None
    schema_version: int = 2
    source: str = ""
    language: str = "nb"
    tags: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class RawLessonMeta:
    """Validated metadata loaded from ``meta.json``."""

    id: str
    title: str
    source: str
    language: str
    tags: list[str] = field(default_factory=list)
    description: str = ""
    level: LessonLevel = LessonLevel.UNKNOWN
    warnings: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class RawLesson:
    """Normalized raw lesson content loaded from ``content/raw/{lesson-id}``."""

    lesson_id: str
    root_dir: Path
    original_text: str
    annotated_text: str
    original_path: Path
    annotated_path: Path
    audio_path: Path
    meta: RawLessonMeta
    vocab_path: Optional[Path] = None
    grammar_path: Optional[Path] = None


@dataclass(frozen=True)
class SentencePair:
    """One original/annotated sentence pair after deterministic splitting."""

    id: str
    original_text: str
    annotated_text: str
    tokens: list[Token]


@dataclass(frozen=True)
class AlignmentItem:
    """Serializable alignment payload for one sentence segment."""

    id: str
    text: str
    start_time: float
    end_time: float
    tokens: list[Token] = field(default_factory=list)
    confidence: Optional[float] = None
    notes: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class AlignmentMeta:
    """Metadata describing the aligner used to produce lesson timing."""

    aligner_requested: str
    aligner_used: str
    fallback_occurred: bool
    has_token_timings: bool
    strict_alignment: bool = False
    external_alignment_path: Optional[str] = None
    warnings: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class AlignmentResult:
    """Result returned by aligners and aligner selection."""

    segments: list[Segment]
    meta: AlignmentMeta


@dataclass(frozen=True)
class ManifestEntry:
    """One row in ``apps/web/public/lessons/index.json``."""

    id: str
    title: str
    source: str
    language: str
    tags: list[str]
    audio_src: str
    lesson_json_src: str
    captions_src: str
    duration_sec: float
    segment_count: int
    description: str = ""
    level: LessonLevel = LessonLevel.UNKNOWN
    aligner_used: str = ""
    built_at: str = ""
