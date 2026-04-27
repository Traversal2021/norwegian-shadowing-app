"""Tests for the fallback timestamp distributor."""

from __future__ import annotations

from shadowing_pipeline.align.fallback import FallbackAligner
from shadowing_pipeline.models import Segment, Token


def test_fallback_distribution_is_monotonic_and_uses_duration() -> None:
    segments = [
        Segment(id="s1", start_time=0, end_time=0, tokens=[Token("Kort"), Token(".")]),
        Segment(
            id="s2",
            start_time=0,
            end_time=0,
            tokens=[Token("En"), Token("meget"), Token("længere"), Token("sætning"), Token(".")],
        ),
        Segment(id="s3", start_time=0, end_time=0, tokens=[Token("Slut"), Token(".")]),
    ]

    aligned = FallbackAligner()._distribute(segments, total_duration=12.0)

    assert aligned[0].start_time == 0
    assert aligned[-1].end_time == 12.0
    assert all(segment.end_time > segment.start_time for segment in aligned)
    assert aligned[0].end_time <= aligned[1].start_time
    assert aligned[1].end_time <= aligned[2].start_time
    assert (aligned[1].end_time - aligned[1].start_time) > (
        aligned[0].end_time - aligned[0].start_time
    )
