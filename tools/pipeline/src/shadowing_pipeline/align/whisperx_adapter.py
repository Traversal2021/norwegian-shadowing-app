"""WhisperX alignment adapter.

The adapter is availability-aware and intentionally conservative. If WhisperX is
not installed, selector logic can fall back or strict modes can fail clearly.
"""

from __future__ import annotations

import importlib.util
import re
import shutil
from dataclasses import replace

from ..errors import AlignmentError
from ..language_config import DEFAULT_LANGUAGE
from ..models import Segment, Token
from ..text_utils import is_punctuation_token
from .base import AlignerRun, AlignerRuntimeInfo, BaseAligner


class WhisperXAligner(BaseAligner):
    @property
    def name(self) -> str:
        return "whisperx"

    @property
    def supports_token_timing(self) -> bool:
        return True

    def check_available(self) -> AlignerRuntimeInfo:
        if importlib.util.find_spec("whisperx") is None and shutil.which("whisperx") is None:
            return AlignerRuntimeInfo(False, "WhisperX is not installed or on PATH.")
        return AlignerRuntimeInfo(True)

    def align(self, audio_path: str, segments: list[Segment]) -> AlignerRun:
        availability = self.check_available()
        if not availability.available:
            raise AlignmentError(availability.reason)
        if importlib.util.find_spec("whisperx") is None:
            raise AlignmentError("WhisperX Python package is required for in-process alignment.")

        try:
            import os
            import whisperx  # type: ignore[import-not-found]

            device = os.environ.get("SHADOWING_WHISPERX_DEVICE", "cpu")
            model_name = os.environ.get("SHADOWING_WHISPERX_MODEL", "small")
            compute_type = os.environ.get("SHADOWING_WHISPERX_COMPUTE_TYPE", "int8")
            batch_size = int(os.environ.get("SHADOWING_WHISPERX_BATCH_SIZE", "8"))
            asr_language = DEFAULT_LANGUAGE.asr_language
            model = whisperx.load_model(model_name, device, compute_type=compute_type, language=asr_language)
            transcription = model.transcribe(audio_path, batch_size=batch_size, language=asr_language)
            language = transcription.get("language") or asr_language
            align_model, metadata = whisperx.load_align_model(language_code=language, device=device)
            aligned = whisperx.align(
                transcription["segments"],
                align_model,
                metadata,
                audio_path,
                device,
                return_char_alignments=False,
            )
        except Exception as exc:
            raise AlignmentError(f"WhisperX alignment failed: {exc}") from exc

        word_segments = aligned.get("word_segments") or []
        if not word_segments:
            raise AlignmentError("WhisperX did not return word timestamps.")
        aligned_segments = _map_words_to_segments(segments, word_segments)
        return AlignerRun(
            segments=aligned_segments,
            notes=[
                f"WhisperX model={model_name}, device={device}, computeType={compute_type}.",
                "Word timestamps were mapped back to canonical sentence segments in order.",
            ],
        )


def segment_text(segment: Segment) -> str:
    return " ".join(token.text for token in segment.tokens)


def _map_words_to_segments(segments: list[Segment], word_segments: list[dict[str, object]]) -> list[Segment]:
    normalized_words = [
        {
            "word": _normalize_word(str(item.get("word", ""))),
            "start": _float_or_none(item.get("start")),
            "end": _float_or_none(item.get("end")),
            "score": _float_or_none(item.get("score")),
        }
        for item in word_segments
    ]
    normalized_words = [
        item for item in normalized_words if item["word"] and item["start"] is not None and item["end"] is not None
    ]
    cursor = 0
    result: list[Segment] = []

    for segment in segments:
        tokens: list[Token] = []
        segment_word_timings: list[dict[str, object]] = []
        for token in segment.tokens:
            if is_punctuation_token(token.text):
                tokens.append(token)
                continue
            wanted = _normalize_word(token.text)
            match_index = _find_next_word(normalized_words, wanted, cursor)
            if match_index is None:
                tokens.append(token)
                continue
            timing = normalized_words[match_index]
            cursor = match_index + 1
            segment_word_timings.append(timing)
            tokens.append(
                replace(
                    token,
                    start=timing["start"],
                    end=timing["end"],
                    confidence=timing["score"],
                )
            )

        if not segment_word_timings:
            raise AlignmentError(f"WhisperX could not map timestamps for segment {segment.id}.")
        start = round(float(segment_word_timings[0]["start"]), 3)
        end = round(float(segment_word_timings[-1]["end"]), 3)
        result.append(replace(segment, start_time=start, end_time=end, tokens=tokens))

    return result


def _find_next_word(words: list[dict[str, object]], wanted: str, start: int) -> int | None:
    if not wanted:
        return None
    for index in range(start, len(words)):
        if words[index]["word"] == wanted:
            return index
    return None


def _normalize_word(value: str) -> str:
    return re.sub(r"[^\wæøåÆØÅ]+", "", value, flags=re.UNICODE).casefold()


def _float_or_none(value: object) -> float | None:
    try:
        return float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
