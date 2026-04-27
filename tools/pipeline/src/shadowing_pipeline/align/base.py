"""Abstract base classes and shared types for pluggable aligners."""

from __future__ import annotations

from abc import ABC, abstractmethod

from dataclasses import dataclass, field
from typing import Literal

from ..models import Segment

AlignmentMode = Literal["auto", "external", "fastwhisper", "whisperx", "fallback"]


@dataclass(frozen=True)
class AlignerRuntimeInfo:
    """Availability and diagnostic information for one aligner adapter."""

    available: bool
    reason: str = ""


@dataclass(frozen=True)
class AlignerRun:
    """Raw aligner output before build-level fallback metadata is applied."""

    segments: list[Segment]
    warnings: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    aligner_used: str | None = None
    external_alignment_path: str | None = None


class BaseAligner(ABC):
    """Abstract aligner interface."""

    @abstractmethod
    def align(
        self,
        audio_path: str,
        segments: list[Segment],
    ) -> AlignerRun:
        """Assign timestamps to each segment in *segments*.

        Args:
            audio_path: Path to the audio file (must be MP3 or WAV).
            segments:   Segments with tokens populated but without timestamps.

        Returns:
            The segments with sentence-level and optional token-level timings.

        Note:
            Implementations must not mutate the input list; return a new list.
        """
        ...

    def check_available(self) -> AlignerRuntimeInfo:
        """Return whether this aligner can run in the current environment."""
        return AlignerRuntimeInfo(available=True)

    @property
    def supports_token_timing(self) -> bool:
        """Whether this adapter may emit token-level timing."""
        return False

    @property
    @abstractmethod
    def name(self) -> str:
        """Short identifier for this aligner, e.g. 'fallback' or 'whisperx'."""
        ...
