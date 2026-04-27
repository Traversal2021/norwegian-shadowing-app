"""Tests for backward-compatible Phase 3 lesson.json extensions."""

from __future__ import annotations

from shadowing_pipeline.exporters.lesson_json import _lesson_to_dict
from shadowing_pipeline.models import AlignmentMeta, Lesson, LessonLevel, Segment, Token


def test_lesson_json_includes_optional_token_timing_shape() -> None:
    lesson = Lesson(
        id="timed",
        title="Timed",
        description="",
        level=LessonLevel.BEGINNER,
        duration_seconds=1.0,
        audio_file="audio.mp3",
        segments=[
            Segment(
                id="s1",
                start_time=0,
                end_time=1,
                tokens=[Token("Hei", start=0.1, end=0.4, confidence=0.92), Token(".")],
                text_plain="Hei.",
                text_annotated="Hei.",
            )
        ],
        alignment_meta=AlignmentMeta(
            aligner_requested="real",
            aligner_used="real-cli",
            fallback_occurred=False,
            has_token_timings=True,
            external_alignment_path="/tmp/alignment.external.json",
        ),
    )

    payload = _lesson_to_dict(lesson)

    assert payload["segments"][0]["tokens"][0]["start"] == 0.1
    assert payload["segments"][0]["tokens"][0]["end"] == 0.4
    assert payload["schemaVersion"] == 2
    assert payload["audioFile"] == "audio.mp3"
    assert payload["segments"][0]["textPlain"] == "Hei."
    assert payload["segments"][0]["start"] == 0
    assert payload["segments"][0]["end"] == 1
    assert payload["alignmentMeta"]["hasTokenTimings"] is True
    assert payload["alignmentMeta"]["externalAlignmentPath"] == "/tmp/alignment.external.json"


def test_lesson_json_omits_phase_3_fields_for_phase_2_style_lessons() -> None:
    lesson = Lesson(
        id="old",
        title="Old",
        description="",
        level=LessonLevel.BEGINNER,
        duration_seconds=1.0,
        audio_file="audio.mp3",
        segments=[Segment(id="s1", start_time=0, end_time=1, tokens=[Token("Hei")])],
    )

    payload = _lesson_to_dict(lesson)

    assert "alignmentMeta" not in payload
    assert "start" not in payload["segments"][0]["tokens"][0]
