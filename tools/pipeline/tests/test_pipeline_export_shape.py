"""Tests for staged pipeline export artifact shape."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

from shadowing_pipeline.align.base import AlignerRun
from shadowing_pipeline.align.fallback import FallbackAligner
from shadowing_pipeline.builder import build_lesson
from shadowing_pipeline.models import Segment


def test_build_exports_new_schema_and_intermediates(tmp_path: Path, monkeypatch) -> None:
    raw_dir = tmp_path / "lesson-a"
    raw_dir.mkdir()
    (raw_dir / "original.no.txt").write_text(
        "Hei, og velkommen til ”Norsk i ørene”.\n",
        encoding="utf-8",
    )
    (raw_dir / "annotated.no.txt").write_text(
        "Hei(greeting), og velkommen til ”Norsk i ørene”.\n",
        encoding="utf-8",
    )
    (raw_dir / "audio.wav").write_bytes(b"fake")

    monkeypatch.setattr(
        "shadowing_pipeline.pipeline.stage_normalize_audio.normalize_to_wav",
        lambda input_path, output_path, sample_rate=16000, channels=1: Path(output_path),
    )
    monkeypatch.setattr(
        "shadowing_pipeline.pipeline.stage_normalize_audio.convert_to_mp3",
        lambda input_path, output_path, bitrate="128k": Path(output_path),
    )
    monkeypatch.setattr("shadowing_pipeline.pipeline.stage_normalize_audio.probe_audio", lambda path: {})
    monkeypatch.setattr("shadowing_pipeline.pipeline.stage_normalize_audio.get_duration_seconds", lambda path: 1.0)

    def fake_align(self: FallbackAligner, audio_path: str, segments: list[Segment]) -> AlignerRun:
        return AlignerRun(segments=[replace(segments[0], start_time=0, end_time=1)])

    monkeypatch.setattr(FallbackAligner, "align", fake_align)
    monkeypatch.setattr("shadowing_pipeline.builder.stage_manifest", lambda *args, **kwargs: Path("index.json"))

    output_dir = build_lesson(raw_dir, processed_root=tmp_path / "processed", aligner="fallback")
    lesson = json.loads((output_dir / "lesson.json").read_text(encoding="utf-8"))
    alignment = json.loads((output_dir / "alignment.json").read_text(encoding="utf-8"))

    assert lesson["schemaVersion"] == 2
    assert lesson["audioFile"] == "audio.mp3"
    assert lesson["segments"][0]["textPlain"] == "Hei, og velkommen til ”Norsk i ørene”."
    assert lesson["segments"][0]["tokens"][0]["gloss"] == "greeting"
    assert alignment["schemaVersion"] == 2
    assert alignment["segments"][0]["start"] == 0
    assert (output_dir / "annotated.canonical.no.txt").is_file()
    assert (output_dir / "sentence-segments.json").is_file()
