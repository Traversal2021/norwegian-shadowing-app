"""Custom exceptions with user-friendly messages for the Phase 2 pipeline."""

from __future__ import annotations


class PipelineError(Exception):
    """Base class for build-stopping pipeline errors."""


class ValidationError(PipelineError):
    """Raised when raw lesson inputs are missing or malformed."""


class SentenceAlignmentError(PipelineError):
    """Raised when original and annotated sentence streams cannot be merged."""


class AudioConversionError(PipelineError):
    """Raised when audio conversion or duration probing fails."""


class AlignmentError(PipelineError):
    """Raised when an aligner cannot produce valid timing output."""
