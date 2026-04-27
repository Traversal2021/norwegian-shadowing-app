"""Tests for the VTT exporter timestamp formatter."""

from shadowing_pipeline.exporters.vtt import _format_timestamp
from shadowing_pipeline.models import Lesson, LessonLevel, Segment, Token
from shadowing_pipeline.exporters.vtt import export_vtt


def test_format_seconds_only() -> None:
    assert _format_timestamp(4.2) == "00:04.200"


def test_format_minutes_and_seconds() -> None:
    assert _format_timestamp(75.0) == "01:15.000"


def test_format_with_milliseconds() -> None:
    assert _format_timestamp(9.005) == "00:09.005"


def test_format_hours() -> None:
    assert _format_timestamp(3661.5) == "01:01:01.500"


def test_export_vtt_renders_clean_token_spacing(tmp_path) -> None:
    lesson = Lesson(
        id="lesson-a",
        title="Hei",
        description="",
        level=LessonLevel.BEGINNER,
        duration_seconds=1,
        audio_file="audio.mp3",
        segments=[
            Segment(
                id="s1",
                start_time=0,
                end_time=1,
                tokens=[Token("Hei"), Token(","), Token("verden"), Token(".")],
            )
        ],
    )

    output = export_vtt(lesson, tmp_path / "captions.vtt")
    text = output.read_text(encoding="utf-8")
    assert "Language: nb" in text
    assert "Hei, verden." in text
