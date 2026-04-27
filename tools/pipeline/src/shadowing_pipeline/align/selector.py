"""Alignment mode selection with external JSON and external runner preference."""

from __future__ import annotations

from .base import AlignmentMode, BaseAligner
from .external_file import (
    FASTWHISPER_ALIGNER_ENV,
    WHISPERX_ALIGNER_ENV,
    ExistingExternalAlignmentAligner,
    ExternalRunnerAligner,
)
from .fallback import FallbackAligner
from ..errors import AlignmentError
from ..language_config import DEFAULT_LANGUAGE
from ..models import AlignmentMeta, AlignmentResult, Segment


def align_segments(
    audio_path: str,
    segments: list[Segment],
    *,
    lesson_id: str,
    language: str,
    transcript_path: str,
    segments_json_path: str,
    external_alignment_path: str | None = None,
    requested: AlignmentMode = "auto",
    strict_alignment: bool = False,
) -> AlignmentResult:
    """Align segments using the requested backend.

    ``auto`` prefers an existing external JSON, then faster-whisper, then
    WhisperX, then the deterministic fallback with a warning.
    """
    warnings: list[str] = []
    asr_language = DEFAULT_LANGUAGE.asr_language
    fallback = FallbackAligner()
    external_file = ExistingExternalAlignmentAligner(
        lesson_id=lesson_id,
        language=asr_language,
        external_alignment_path=external_alignment_path,
    )
    if external_alignment_path is None:
        raise AlignmentError("An external alignment path is required for alignment selection.")
    fastwhisper = ExternalRunnerAligner(
        lesson_id=lesson_id,
        language=asr_language,
        transcript_path=transcript_path,
        segments_json_path=segments_json_path,
        external_alignment_path=external_alignment_path,
        command_env_var=FASTWHISPER_ALIGNER_ENV,
        backend_name="fastwhisper",
        include_transcript=False,
    )
    whisperx = ExternalRunnerAligner(
        lesson_id=lesson_id,
        language=asr_language,
        transcript_path=transcript_path,
        segments_json_path=segments_json_path,
        external_alignment_path=external_alignment_path,
        command_env_var=WHISPERX_ALIGNER_ENV,
        backend_name="whisperx",
        include_transcript=True,
    )

    if requested == "fallback":
        return _run_selected(fallback, audio_path, segments, requested, strict_alignment, False, warnings)

    candidates = _candidate_aligners(requested, external_file, fastwhisper, whisperx)
    for aligner in candidates:
        availability = aligner.check_available()
        if not availability.available:
            message = f"{aligner.name} unavailable: {availability.reason}"
            if strict_alignment and requested in {"external", "fastwhisper", "whisperx"}:
                raise AlignmentError(message)
            warnings.append(message)
            continue
        try:
            return _run_selected(
                aligner,
                audio_path,
                segments,
                requested,
                strict_alignment,
                False,
                warnings,
            )
        except AlignmentError as exc:
            message = f"{aligner.name} failed: {exc}"
            if strict_alignment or requested in {"external", "fastwhisper", "whisperx"}:
                raise AlignmentError(message) from exc
            warnings.append(message)

    if strict_alignment and requested in {"external", "fastwhisper", "whisperx"}:
        raise AlignmentError(
            f"No requested real aligner could run for mode {requested!r}: {'; '.join(warnings)}"
        )

    warnings.append("Falling back to approximate sentence-level alignment.")
    return _run_selected(fallback, audio_path, segments, requested, strict_alignment, requested != "fallback", warnings)


def _candidate_aligners(
    requested: AlignmentMode,
    external_file: ExistingExternalAlignmentAligner,
    fastwhisper: ExternalRunnerAligner,
    whisperx: ExternalRunnerAligner,
) -> list[BaseAligner]:
    if requested == "auto":
        return [external_file, fastwhisper, whisperx]
    if requested == "external":
        return [external_file]
    if requested == "fastwhisper":
        return [fastwhisper]
    if requested == "whisperx":
        return [whisperx]
    return []


def _run_selected(
    aligner: BaseAligner,
    audio_path: str,
    segments: list[Segment],
    requested: AlignmentMode,
    strict_alignment: bool,
    fallback_occurred: bool,
    prior_warnings: list[str],
) -> AlignmentResult:
    run = aligner.align(audio_path, segments)
    return AlignmentResult(
        segments=run.segments,
        meta=AlignmentMeta(
            aligner_requested=requested,
            aligner_used=run.aligner_used or aligner.name,
            fallback_occurred=fallback_occurred,
            has_token_timings=_has_token_timings(run.segments),
            strict_alignment=strict_alignment,
            external_alignment_path=run.external_alignment_path,
            warnings=prior_warnings + run.warnings,
            notes=run.notes,
        ),
    )


def _has_token_timings(segments: list[Segment]) -> bool:
    return any(
        token.start is not None and token.end is not None
        for segment in segments
        for token in segment.tokens
    )
