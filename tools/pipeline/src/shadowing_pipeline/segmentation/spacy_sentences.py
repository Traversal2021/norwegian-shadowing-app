"""Norwegian sentence segmentation via spaCy with deterministic fallback."""

from __future__ import annotations

from dataclasses import dataclass, field

from ..annotated_repair import split_original_sentence_spans
from ..language_config import DEFAULT_LANGUAGE


@dataclass(frozen=True)
class SentenceSegment:
    id: str
    text: str
    start_char: int
    end_char: int
    token_count: int
    diagnostics: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class SentenceSegmentationResult:
    segments: list[SentenceSegment]
    backend: str
    warnings: list[str] = field(default_factory=list)


def segment_sentences(text: str) -> SentenceSegmentationResult:
    """Segment original text into exact sentence spans.

    The Norwegian Bokmål spaCy model is preferred. If spaCy or the model is
    unavailable in the local environment, the deterministic project splitter is
    used with a clear warning so fallback builds remain inspectable.
    """
    try:
        import spacy  # type: ignore[import-not-found]
    except ModuleNotFoundError:
        return _fallback_result(
            text,
            "spaCy is not installed; used deterministic sentence splitter fallback.",
        )

    try:
        nlp = spacy.load(DEFAULT_LANGUAGE.spacy_model)
    except OSError:
        return _fallback_result(
            text,
            f"spaCy model {DEFAULT_LANGUAGE.spacy_model!r} is unavailable; "
            "used deterministic sentence splitter fallback.",
        )
    if "sentencizer" not in nlp.pipe_names and "parser" not in nlp.pipe_names and "senter" not in nlp.pipe_names:
        nlp.add_pipe("sentencizer")
    doc = nlp(text)
    segments: list[SentenceSegment] = []
    for index, sentence in enumerate(doc.sents, start=1):
        raw = text[sentence.start_char : sentence.end_char]
        leading = len(raw) - len(raw.lstrip())
        trailing = len(raw.rstrip())
        start = sentence.start_char + leading
        end = sentence.start_char + trailing
        visible = text[start:end]
        if visible:
            segments.append(
                SentenceSegment(
                    id=f"s{index}",
                    text=visible,
                    start_char=start,
                    end_char=end,
                    token_count=len([token for token in sentence if not token.is_space]),
                )
            )

    return SentenceSegmentationResult(segments=segments, backend=DEFAULT_LANGUAGE.spacy_model)


def _fallback_result(text: str, warning: str) -> SentenceSegmentationResult:
    return SentenceSegmentationResult(
        segments=_fallback_segments(text),
        backend="deterministic-fallback",
        warnings=[warning],
    )


def _fallback_segments(text: str) -> list[SentenceSegment]:
    return [
        SentenceSegment(
            id=f"s{index}",
            text=span.text,
            start_char=span.start,
            end_char=span.end,
            token_count=len(span.text.split()),
            diagnostics=["Segmented by deterministic fallback splitter."],
        )
        for index, span in enumerate(split_original_sentence_spans(text), start=1)
    ]
