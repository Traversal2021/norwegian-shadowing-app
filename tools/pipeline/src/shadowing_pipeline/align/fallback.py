"""Deterministic fallback aligner for approximate sentence timestamps."""

from __future__ import annotations

from dataclasses import replace

from ..audio_convert import get_duration_seconds
from ..models import Segment
from ..text_utils import is_punctuation_token, tokens_to_text
from .base import AlignerRun, BaseAligner


class FallbackAligner(BaseAligner):
    """Assign timestamps using audio duration plus text-length heuristics."""

    @property
    def name(self) -> str:
        return "fallback"

    def align(self, audio_path: str, segments: list[Segment]) -> AlignerRun:
        """Assign timestamps proportionally to lexical token counts and length."""
        total_duration = get_duration_seconds(audio_path)
        return AlignerRun(
            segments=self._distribute(segments, total_duration),
            notes=["Fallback timing is approximate and sentence-level only."],
        )

    def _distribute(self, segments: list[Segment], total_duration: float) -> list[Segment]:
        if not segments:
            return []
        if total_duration <= 0:
            raise ValueError("Audio duration must be greater than zero for alignment.")

        min_duration = min(0.2, total_duration / (len(segments) * 2))
        flexible_duration = max(total_duration - (min_duration * len(segments)), 0.0)
        weights = [self._segment_weight(segment) for segment in segments]
        total_weight = sum(weights) or float(len(segments))

        raw_durations = [
            min_duration + (flexible_duration * (weight / total_weight)) for weight in weights
        ]

        result: list[Segment] = []
        cursor = 0.0
        for index, (segment, duration) in enumerate(zip(segments, raw_durations, strict=True)):
            start = round(cursor, 3)
            if index == len(segments) - 1:
                end = round(total_duration, 3)
            else:
                remaining = len(segments) - index - 1
                latest_end = round(total_duration - (remaining * min_duration), 3)
                proposed_end = round(cursor + duration, 3)
                earliest_end = round(cursor + min_duration, 3)
                end = min(max(proposed_end, earliest_end), latest_end)
                if end <= start:
                    end = round(start + min_duration, 3)

            result.append(replace(segment, start_time=start, end_time=end))
            cursor = end

        if result:
            result[-1] = replace(result[-1], end_time=round(total_duration, 3))

        return result

    def _segment_weight(self, segment: Segment) -> float:
        lexical_tokens = [token.text for token in segment.tokens if not is_punctuation_token(token.text)]
        lexical_chars = sum(len(token) for token in lexical_tokens)
        lexical_words = len(lexical_tokens)
        if lexical_words == 0:
            lexical_chars = len(tokens_to_text(segment.tokens))
        return max((lexical_words * 2) + lexical_chars, 1)
