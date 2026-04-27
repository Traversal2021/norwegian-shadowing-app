"""Exporter for ``captions.vtt``."""

from __future__ import annotations

from pathlib import Path

from ..language_config import DEFAULT_LANGUAGE
from ..models import Lesson, Segment
from ..text_utils import tokens_to_text


def export_vtt(lesson: Lesson, output_path: str | Path) -> Path:
    """Write lesson captions as valid WebVTT."""
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    lines = ["WEBVTT", "Kind: captions", f"Language: {DEFAULT_LANGUAGE.metadata_language}", ""]
    for segment in lesson.segments:
        lines.append(_format_cue(segment))

    output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return output.resolve()


def _format_cue(segment: Segment) -> str:
    start = _format_timestamp(segment.start_time)
    end = _format_timestamp(segment.end_time)
    text = segment.text_plain or tokens_to_text(segment.tokens)
    return f"{start} --> {end}\n{text}\n"


def _format_timestamp(seconds: float) -> str:
    total_ms = int(round(seconds * 1000))
    ms = total_ms % 1000
    total_s = total_ms // 1000
    s = total_s % 60
    total_m = total_s // 60
    m = total_m % 60
    h = total_m // 60
    if h > 0:
        return f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}"
    return f"{m:02d}:{s:02d}.{ms:03d}"
