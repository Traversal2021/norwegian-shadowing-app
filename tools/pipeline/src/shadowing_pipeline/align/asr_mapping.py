"""Utilities for monotonic ASR-to-sentence alignment mapping."""

from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher


@dataclass(frozen=True)
class SentenceEntry:
    id: str
    text: str


@dataclass(frozen=True)
class AsrSegmentEntry:
    start: float
    end: float
    text: str
    confidence: float | None = None


@dataclass(frozen=True)
class SentenceTiming:
    id: str
    text: str
    start: float
    end: float
    source_asr_text: str
    confidence: float | None = None


@dataclass(frozen=True)
class AsrMappingResult:
    segments: list[SentenceTiming]
    warnings: list[str]
    notes: list[str]


def map_asr_segments_to_sentences(
    sentences: list[SentenceEntry],
    asr_segments: list[AsrSegmentEntry],
) -> AsrMappingResult:
    if not sentences:
        raise ValueError("Expected at least one sentence to map.")
    if not asr_segments:
        raise ValueError("Expected at least one ASR segment to map.")

    sentence_cursor = 0
    asr_cursor = 0
    mapped: list[SentenceTiming] = []
    warnings: list[str] = []
    low_confidence_count = 0

    while sentence_cursor < len(sentences) and asr_cursor < len(asr_segments):
        sentence_count, asr_count, score = _best_window(
            sentences[sentence_cursor:],
            asr_segments[asr_cursor:],
        )
        sentence_window = sentences[sentence_cursor : sentence_cursor + sentence_count]
        asr_window = asr_segments[asr_cursor : asr_cursor + asr_count]

        if score < 0.45:
            low_confidence_count += sentence_count
            warnings.append(
                "Low-confidence ASR mapping for "
                f"{', '.join(item.id for item in sentence_window)}: score={score:.2f} "
                f"from ASR text {joined_asr_text(asr_window)!r}."
            )

        mapped.extend(_project_sentence_window(sentence_window, asr_window, score))
        sentence_cursor += sentence_count
        asr_cursor += asr_count

    if sentence_cursor != len(sentences):
        raise ValueError(
            f"ASR mapping exhausted early: mapped {sentence_cursor} of {len(sentences)} sentence(s)."
        )
    if asr_cursor < len(asr_segments):
        warnings.append(
            f"{len(asr_segments) - asr_cursor} trailing ASR segment(s) were unused after monotonic mapping."
        )

    if low_confidence_count > max(1, len(sentences) // 3):
        raise ValueError(
            f"ASR mapping confidence was too low for {low_confidence_count} sentence(s)."
        )

    return AsrMappingResult(
        segments=mapped,
        warnings=warnings,
        notes=["Sentence timings were derived from monotonic ASR segment matching."],
    )


def joined_asr_text(segments: list[AsrSegmentEntry]) -> str:
    return " ".join(segment.text.strip() for segment in segments if segment.text.strip())


def _best_window(
    remaining_sentences: list[SentenceEntry],
    remaining_asr_segments: list[AsrSegmentEntry],
) -> tuple[int, int, float]:
    best: tuple[int, int, float] = (1, 1, -1.0)
    max_sentence_window = min(3, len(remaining_sentences))
    max_asr_window = min(3, len(remaining_asr_segments))

    for sentence_count in range(1, max_sentence_window + 1):
        for asr_count in range(1, max_asr_window + 1):
            score = _window_score(
                remaining_sentences[:sentence_count],
                remaining_asr_segments[:asr_count],
            )
            if score > best[2]:
                best = (sentence_count, asr_count, score)
    return best


def _window_score(sentences: list[SentenceEntry], asr_segments: list[AsrSegmentEntry]) -> float:
    sentence_text = _normalize_text(" ".join(sentence.text for sentence in sentences))
    asr_text = _normalize_text(joined_asr_text(asr_segments))
    if not sentence_text or not asr_text:
        return 0.0

    seq_ratio = SequenceMatcher(None, sentence_text, asr_text).ratio()
    sentence_tokens = sentence_text.split()
    asr_tokens = asr_text.split()
    overlap = _token_overlap(sentence_tokens, asr_tokens)
    length_penalty = 0.02 * (len(sentences) + len(asr_segments) - 2)
    return max(0.0, min(1.0, 0.7 * seq_ratio + 0.3 * overlap - length_penalty))


def _token_overlap(left: list[str], right: list[str]) -> float:
    if not left or not right:
        return 0.0
    left_remaining = list(left)
    matched = 0
    for token in right:
        if token in left_remaining:
            left_remaining.remove(token)
            matched += 1
    return (2 * matched) / (len(left) + len(right))


def _project_sentence_window(
    sentences: list[SentenceEntry],
    asr_segments: list[AsrSegmentEntry],
    score: float,
) -> list[SentenceTiming]:
    start = round(asr_segments[0].start, 3)
    end = round(asr_segments[-1].end, 3)
    asr_text = joined_asr_text(asr_segments)
    confidence = _combine_confidence(asr_segments, score)

    if len(sentences) == 1:
        sentence = sentences[0]
        return [
            SentenceTiming(
                id=sentence.id,
                text=sentence.text,
                start=start,
                end=end,
                source_asr_text=asr_text,
                confidence=confidence,
            )
        ]

    total_duration = max(end - start, 0.001)
    weights = [_sentence_weight(sentence.text) for sentence in sentences]
    total_weight = sum(weights) or len(sentences)
    cursor = start
    projected: list[SentenceTiming] = []

    for index, sentence in enumerate(sentences):
        if index == len(sentences) - 1:
            sentence_end = end
        else:
            portion = total_duration * (weights[index] / total_weight)
            sentence_end = min(end, round(cursor + portion, 3))
        projected.append(
            SentenceTiming(
                id=sentence.id,
                text=sentence.text,
                start=round(cursor, 3),
                end=round(max(sentence_end, cursor + 0.001), 3),
                source_asr_text=asr_text,
                confidence=confidence,
            )
        )
        cursor = projected[-1].end

    if projected[-1].end != end:
        projected[-1] = SentenceTiming(
            id=projected[-1].id,
            text=projected[-1].text,
            start=projected[-1].start,
            end=end,
            source_asr_text=projected[-1].source_asr_text,
            confidence=projected[-1].confidence,
        )
    return projected


def _combine_confidence(asr_segments: list[AsrSegmentEntry], score: float) -> float | None:
    confidences = [segment.confidence for segment in asr_segments if segment.confidence is not None]
    if confidences:
        return round((sum(confidences) / len(confidences) + score) / 2, 3)
    return round(score, 3)


def _sentence_weight(text: str) -> int:
    normalized = _normalize_text(text)
    if not normalized:
        return 1
    return max(len(normalized.replace(" ", "")), len(normalized.split()))


def _normalize_text(value: str) -> str:
    normalized_chars: list[str] = []
    for char in value.casefold():
        if char.isalnum() or char in {" ", "æ", "ø", "å"}:
            normalized_chars.append(char)
        else:
            normalized_chars.append(" ")
    return " ".join("".join(normalized_chars).split())
