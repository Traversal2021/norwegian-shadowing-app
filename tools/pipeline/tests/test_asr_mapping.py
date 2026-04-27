"""Tests for monotonic ASR-to-sentence mapping."""

from __future__ import annotations

import pytest

from shadowing_pipeline.align.asr_mapping import (
    AsrSegmentEntry,
    SentenceEntry,
    map_asr_segments_to_sentences,
)


def test_monotonic_mapping_keeps_sentence_order() -> None:
    result = map_asr_segments_to_sentences(
        [
            SentenceEntry(id="s1", text="Godmorgen"),
            SentenceEntry(id="s2", text="Hvordan går det"),
        ],
        [
            AsrSegmentEntry(start=0.0, end=1.0, text="Godmorgen"),
            AsrSegmentEntry(start=1.0, end=2.0, text="Hvordan går det"),
        ],
    )

    assert [segment.id for segment in result.segments] == ["s1", "s2"]
    assert result.segments[0].end <= result.segments[1].start


def test_one_asr_segment_can_cover_multiple_sentence_segments() -> None:
    result = map_asr_segments_to_sentences(
        [
            SentenceEntry(id="s1", text="Hei"),
            SentenceEntry(id="s2", text="Hvordan går det"),
        ],
        [AsrSegmentEntry(start=0.0, end=4.0, text="Hei hvordan går det")],
    )

    assert result.segments[0].start == 0.0
    assert result.segments[1].end == 4.0
    assert result.segments[0].end <= result.segments[1].start


def test_multiple_asr_segments_can_cover_one_sentence_segment() -> None:
    result = map_asr_segments_to_sentences(
        [SentenceEntry(id="s1", text="Det her er en længere sætning")],
        [
            AsrSegmentEntry(start=0.0, end=1.2, text="Det her er"),
            AsrSegmentEntry(start=1.2, end=3.0, text="en længere sætning"),
        ],
    )

    assert result.segments[0].start == 0.0
    assert result.segments[0].end == 3.0


def test_low_confidence_mapping_warns() -> None:
    result = map_asr_segments_to_sentences(
        [
            SentenceEntry(id="s1", text="Hei verden"),
            SentenceEntry(id="s2", text="Tak for i dag"),
        ],
        [
            AsrSegmentEntry(start=0.0, end=1.0, text="Hei"),
            AsrSegmentEntry(start=1.0, end=2.0, text="Tak"),
        ],
    )

    assert result.warnings
    assert "Low-confidence ASR mapping" in result.warnings[0]


def test_bad_mapping_fails() -> None:
    with pytest.raises(ValueError, match="too low"):
        map_asr_segments_to_sentences(
            [
                SentenceEntry(id="s1", text="A"),
                SentenceEntry(id="s2", text="B"),
                SentenceEntry(id="s3", text="C"),
            ],
            [
                AsrSegmentEntry(start=0.0, end=1.0, text="x"),
                AsrSegmentEntry(start=1.0, end=2.0, text="y"),
                AsrSegmentEntry(start=2.0, end=3.0, text="z"),
            ],
        )
