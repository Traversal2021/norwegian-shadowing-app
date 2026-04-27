"""Deterministic sentence splitting and original/annotated sentence merging."""

from __future__ import annotations

from .errors import SentenceAlignmentError
from .models import SentencePair
from .parse_annotations import parse_annotated_line, strip_annotations

_ABBREVIATIONS = ("f.eks.", "bl.a.", "osv.", "ca.", "mr.", "fr.", "dr.")
_CLOSING_QUOTES = {'"', "'", "”", "’", "»"}


def split_sentences(text: str) -> list[str]:
    """Split text into normalized sentence strings without losing punctuation."""
    normalized = " ".join(text.replace("\r\n", "\n").split())
    if not normalized:
        return []

    sentences: list[str] = []
    buffer: list[str] = []
    paren_depth = 0
    index = 0
    length = len(normalized)

    while index < length:
        char = normalized[index]
        buffer.append(char)

        if char == "(":
            paren_depth += 1
        elif char == ")" and paren_depth > 0:
            paren_depth -= 1
        elif char in ".?!" and paren_depth == 0:
            lookahead = index + 1
            while lookahead < length and normalized[lookahead] in _CLOSING_QUOTES:
                buffer.append(normalized[lookahead])
                lookahead += 1

            candidate = "".join(buffer).strip()
            next_is_boundary = lookahead >= length or normalized[lookahead].isspace()
            if next_is_boundary and not _ends_with_abbreviation(candidate):
                sentences.append(candidate)
                buffer = []
                index = lookahead
                while index < length and normalized[index].isspace():
                    index += 1
                continue

        index += 1

    tail = "".join(buffer).strip()
    if tail:
        sentences.append(tail)

    return sentences


def split_annotated_sentences(annotated_text: str) -> list[str]:
    """Split annotated text with the same rules, keeping gloss markup intact."""
    return split_sentences(annotated_text)


def merge_sentence_streams(original_text: str, annotated_text: str) -> list[SentencePair]:
    """Split and merge original/annotated texts by sentence index."""
    original_sentences = split_sentences(original_text)
    annotated_sentences = split_annotated_sentences(annotated_text)

    if len(original_sentences) != len(annotated_sentences):
        raise SentenceAlignmentError(
            "Sentence count mismatch while merging lesson text: "
            f"{len(original_sentences)} original sentence(s) vs "
            f"{len(annotated_sentences)} annotated sentence(s)."
        )

    pairs: list[SentencePair] = []
    for index, (original_sentence, annotated_sentence) in enumerate(
        zip(original_sentences, annotated_sentences, strict=True),
        start=1,
    ):
        cleaned_annotated = " ".join(strip_annotations(annotated_sentence).split())
        cleaned_original = " ".join(original_sentence.split())
        if cleaned_annotated != cleaned_original:
            raise SentenceAlignmentError(
                "Original and annotated sentence text diverged after stripping glosses "
                f"at sentence {index}: original={cleaned_original!r}, "
                f"annotated={cleaned_annotated!r}. "
                "Try: shadowing-pipeline repair-annotated --lesson <lesson-id> --report"
            )

        pairs.append(
            SentencePair(
                id=f"s{index}",
                original_text=cleaned_original,
                annotated_text=annotated_sentence,
                tokens=parse_annotated_line(annotated_sentence),
            )
        )

    return pairs


def _ends_with_abbreviation(candidate: str) -> bool:
    lowered = candidate.lower()
    return any(lowered.endswith(abbreviation) for abbreviation in _ABBREVIATIONS)
