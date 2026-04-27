"""Tests for deterministic sentence splitting and safe sentence merging."""

from __future__ import annotations

import pytest

from shadowing_pipeline.errors import SentenceAlignmentError
from shadowing_pipeline.sentence_split import merge_sentence_streams, split_sentences


def test_split_sentences_preserves_sentence_punctuation() -> None:
    assert split_sentences("Hei verden. Hvordan går det? Det går fint!") == [
        "Hei verden.",
        "Hvordan går det?",
        "Det går fint!",
    ]


def test_merge_sentence_streams_attaches_glosses_by_index() -> None:
    pairs = merge_sentence_streams(
        "Hei verden. Det består av siffer.",
        "Hei (hello) verden. Det består (consists) av siffer (digits).",
    )

    assert [pair.id for pair in pairs] == ["s1", "s2"]
    assert pairs[1].original_text == "Det består av siffer."
    assert {token.text: token.gloss for token in pairs[1].tokens}["består"] == "consists"


def test_merge_sentence_streams_reports_count_mismatch() -> None:
    with pytest.raises(SentenceAlignmentError, match="Sentence count mismatch"):
        merge_sentence_streams("Hei verden. Farvel.", "Hei (hello) verden.")


def test_merge_sentence_streams_reports_text_divergence() -> None:
    with pytest.raises(SentenceAlignmentError, match="diverged"):
        merge_sentence_streams("Hei verden.", "Hei Norge.")
