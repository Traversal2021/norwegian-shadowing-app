"""Tests for build output shape with optional manual summaries."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

from shadowing_pipeline.align.base import AlignerRun
from shadowing_pipeline.align.fallback import FallbackAligner
from shadowing_pipeline.builder import build_lesson
from shadowing_pipeline.models import Segment


def _write_raw_lesson(root: Path) -> Path:
    lesson_dir = root / "lesson-a"
    lesson_dir.mkdir()
    (lesson_dir / "original.no.txt").write_text("Hei verden.\n", encoding="utf-8")
    (lesson_dir / "annotated.no.txt").write_text("Hei (hello) verden.\n", encoding="utf-8")
    (lesson_dir / "audio.wav").write_bytes(b"fake")
    (lesson_dir / "meta.json").write_text(
        json.dumps({"id": "lesson-a", "title": "Hei", "source": "test", "language": "nb"}),
        encoding="utf-8",
    )
    (lesson_dir / "vocab.json").write_text(
        json.dumps([{"word": "hej", "definition": "hello"}]),
        encoding="utf-8",
    )
    (lesson_dir / "grammar.md").write_text(
        "## Greeting\nExplanation: A greeting phrase.\n",
        encoding="utf-8",
    )
    return lesson_dir


def test_build_lesson_includes_optional_summaries(
    tmp_path: Path,
    monkeypatch,
) -> None:
    raw_dir = _write_raw_lesson(tmp_path)

    def fake_normalize(input_path, output_path, sample_rate=16000, channels=1):
        Path(output_path).write_bytes(b"wav")
        return Path(output_path)

    def fake_convert(input_path, output_path, bitrate="128k"):
        Path(output_path).write_bytes(b"mp3")
        return Path(output_path)

    def fake_align(self: FallbackAligner, audio_path: str, segments: list[Segment]) -> AlignerRun:
        return AlignerRun(segments=[replace(segments[0], start_time=0, end_time=1)])

    monkeypatch.setattr("shadowing_pipeline.pipeline.stage_normalize_audio.normalize_to_wav", fake_normalize)
    monkeypatch.setattr("shadowing_pipeline.pipeline.stage_normalize_audio.convert_to_mp3", fake_convert)
    monkeypatch.setattr("shadowing_pipeline.pipeline.stage_normalize_audio.probe_audio", lambda path: {})
    monkeypatch.setattr("shadowing_pipeline.pipeline.stage_normalize_audio.get_duration_seconds", lambda path: 1.0)
    monkeypatch.setattr(FallbackAligner, "align", fake_align)
    monkeypatch.setattr("shadowing_pipeline.builder.stage_manifest", lambda *args, **kwargs: Path("index.json"))

    output_dir = build_lesson(raw_dir, processed_root=tmp_path / "processed", aligner="fallback")
    payload = json.loads((output_dir / "lesson.json").read_text(encoding="utf-8"))

    assert payload["vocabSummary"][0]["word"] == "hej"
    assert payload["grammarSummary"][0]["title"] == "Greeting"
    assert payload["vocab"][0]["definition"] == "hello"
