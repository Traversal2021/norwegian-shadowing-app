"""Tests for staged alignment mode selection and fallback behavior."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from shadowing_pipeline.align.base import AlignerRun, AlignerRuntimeInfo
from shadowing_pipeline.align.external_file import ExistingExternalAlignmentAligner, ExternalRunnerAligner
from shadowing_pipeline.align.fallback import FallbackAligner
from shadowing_pipeline.align.selector import align_segments
from shadowing_pipeline.errors import AlignmentError
from shadowing_pipeline.models import Segment, Token


def _segments() -> list[Segment]:
    return [Segment(id="s1", start_time=0, end_time=0, tokens=[Token("Hei"), Token(".")])]


def _fake_fallback(self: FallbackAligner, audio_path: str, segments: list[Segment]) -> AlignerRun:
    return AlignerRun(segments=[replace(segments[0], start_time=0, end_time=1)])


def _external_payload(tmp_path: Path, *, aligner: str = "faster-whisper-external") -> Path:
    path = tmp_path / "alignment.external.json"
    path.write_text(
        json.dumps(
            {
                "schemaVersion": 1,
                "lessonId": "lesson-a",
                "aligner": aligner,
                "language": "no",
                "segments": [
                    {
                        "id": "s1",
                        "text": "Hei .",
                        "start": 0.0,
                        "end": 1.0,
                        "words": [{"word": "Hei", "start": 0.1, "end": 0.4}],
                    }
                ],
                "warnings": [],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return path


def test_auto_prefers_existing_external_alignment_when_available(tmp_path: Path) -> None:
    external_path = _external_payload(tmp_path)

    result = align_segments(
        "audio.wav",
        _segments(),
        lesson_id="lesson-a",
        language="nb",
        transcript_path=str(tmp_path / "original.no.txt"),
        segments_json_path=str(tmp_path / "sentence-segments.json"),
        external_alignment_path=str(external_path),
        requested="auto",
    )

    assert result.meta.aligner_used == "faster-whisper-external"
    assert result.meta.fallback_occurred is False


def test_auto_prefers_fastwhisper_runner_before_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        ExistingExternalAlignmentAligner, "check_available", lambda self: AlignerRuntimeInfo(False, "no file")
    )
    monkeypatch.setattr(ExternalRunnerAligner, "check_available", lambda self: AlignerRuntimeInfo(True))
    def fake_external_align(self, audio_path, segments):
        assert self.language == "no"
        return AlignerRun(
            segments=[replace(segments[0], start_time=0, end_time=1)],
            aligner_used="faster-whisper-external" if self.name == "fastwhisper" else "whisperx-external",
        )

    monkeypatch.setattr(ExternalRunnerAligner, "align", fake_external_align)

    result = align_segments(
        "audio.wav",
        _segments(),
        lesson_id="lesson-a",
        language="nb",
        transcript_path="original.no.txt",
        segments_json_path="sentence-segments.json",
        external_alignment_path="alignment.external.json",
        requested="auto",
    )

    assert result.meta.aligner_used == "faster-whisper-external"
    assert result.meta.fallback_occurred is False


def test_auto_falls_back_when_fastwhisper_and_whisperx_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_check(self):
        if self.name == "external-file":
            return AlignerRuntimeInfo(False, "no file")
        return AlignerRuntimeInfo(False, f"no {self.name}")

    monkeypatch.setattr(ExistingExternalAlignmentAligner, "check_available", fake_check)
    monkeypatch.setattr(ExternalRunnerAligner, "check_available", fake_check)
    monkeypatch.setattr(FallbackAligner, "align", _fake_fallback)

    result = align_segments(
        "audio.wav",
        _segments(),
        lesson_id="lesson-a",
        language="nb",
        transcript_path="original.no.txt",
        segments_json_path="sentence-segments.json",
        external_alignment_path="alignment.external.json",
        requested="auto",
    )

    assert result.meta.aligner_used == "fallback"
    assert result.meta.fallback_occurred is True
    assert "external-file unavailable" in result.meta.warnings[0]
    assert "fastwhisper unavailable" in result.meta.warnings[1]


def test_fastwhisper_request_does_not_silently_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ExternalRunnerAligner, "check_available", lambda self: AlignerRuntimeInfo(True))
    monkeypatch.setattr(
        ExternalRunnerAligner,
        "align",
        lambda self, audio_path, segments: (_ for _ in ()).throw(AlignmentError("boom")),
    )

    with pytest.raises(AlignmentError, match="boom"):
        align_segments(
            "audio.wav",
            _segments(),
            lesson_id="lesson-a",
            language="nb",
            transcript_path="original.no.txt",
            segments_json_path="sentence-segments.json",
            external_alignment_path="alignment.external.json",
            requested="fastwhisper",
        )
