"""Tests for external alignment JSON validation and pipeline import."""

from __future__ import annotations

import builtins
import json
from dataclasses import replace
from pathlib import Path

import pytest

from shadowing_pipeline.align.external_file import load_external_alignment
from shadowing_pipeline.align.base import AlignerRun
from shadowing_pipeline.align.fallback import FallbackAligner
from shadowing_pipeline.builder import build_lesson
from shadowing_pipeline.errors import AlignmentError
from shadowing_pipeline.models import Segment, Token


def _seed_segments() -> list[Segment]:
    return [
        Segment(
            id="s1",
            start_time=0.0,
            end_time=0.0,
            tokens=[Token("Hei"), Token(".")],
            text_plain="Hei.",
            text_annotated="Hei.",
        )
    ]


def _write_external_alignment(path: Path, *, lesson_id: str = "lesson-a") -> Path:
    path.write_text(
        json.dumps(
            {
                "schemaVersion": 1,
                "lessonId": lesson_id,
                "aligner": "faster-whisper-external",
                "language": "no",
                "segments": [
                    {
                        "id": "s1",
                        "text": "Hei.",
                        "start": 0.0,
                        "end": 1.0,
                        "sourceAsrText": "Hei.",
                        "confidence": 0.92,
                        "words": [{"word": "Hei", "start": 0.1, "end": 0.4, "confidence": 0.95}],
                    }
                ],
                "warnings": ["mapped externally"],
                "notes": ["test payload"],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return path


def _write_raw_lesson(root: Path) -> Path:
    lesson_dir = root / "lesson-a"
    lesson_dir.mkdir()
    (lesson_dir / "original.no.txt").write_text("Hei.\n", encoding="utf-8")
    (lesson_dir / "annotated.no.txt").write_text("Hei.\n", encoding="utf-8")
    (lesson_dir / "audio.wav").write_bytes(b"fake")
    (lesson_dir / "meta.json").write_text(
        json.dumps({"id": "lesson-a", "title": "Hei", "source": "test", "language": "nb"}),
        encoding="utf-8",
    )
    return lesson_dir


def test_external_alignment_json_validation_rejects_mismatched_lesson_id(tmp_path: Path) -> None:
    path = _write_external_alignment(tmp_path / "alignment.external.json", lesson_id="other")

    with pytest.raises(AlignmentError, match="lessonId mismatch"):
        load_external_alignment(
            payload_path=path,
            lesson_id="lesson-a",
            expected_language="no",
            seed_segments=_seed_segments(),
        )


def test_pipeline_imports_external_alignment_into_build_outputs(tmp_path: Path, monkeypatch) -> None:
    raw_dir = _write_raw_lesson(tmp_path)
    external_path = _write_external_alignment(raw_dir / "alignment.external.json")

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
    monkeypatch.setattr("shadowing_pipeline.builder.stage_manifest", lambda *args, **kwargs: Path("index.json"))

    output_dir = build_lesson(
        raw_dir,
        processed_root=tmp_path / "processed",
        aligner="external",
        external_alignment_path=external_path,
    )
    alignment = json.loads((output_dir / "alignment.json").read_text(encoding="utf-8"))
    report = json.loads((output_dir / "build-report.json").read_text(encoding="utf-8"))

    assert alignment["alignerUsed"] == "faster-whisper-external"
    assert alignment["externalAlignmentPath"] == str(external_path.resolve())
    assert report["alignment"]["alignerUsed"] == "faster-whisper-external"
    assert report["alignment"]["externalAlignmentPath"] == str(external_path.resolve())


def test_auto_falls_back_when_external_alignment_is_unavailable(tmp_path: Path, monkeypatch) -> None:
    raw_dir = _write_raw_lesson(tmp_path)

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
    monkeypatch.setattr("shadowing_pipeline.builder.stage_manifest", lambda *args, **kwargs: Path("index.json"))
    monkeypatch.setattr(
        FallbackAligner,
        "align",
        lambda self, audio_path, segments: AlignerRun(
            segments=[replace(segments[0], start_time=0.0, end_time=1.0)]
        ),
    )

    output_dir = build_lesson(raw_dir, processed_root=tmp_path / "processed", aligner="auto")
    report = json.loads((output_dir / "build-report.json").read_text(encoding="utf-8"))

    assert report["alignment"]["alignerUsed"] == "fallback"
    assert report["alignment"]["fallbackOccurred"] is True


def test_external_alignment_path_does_not_require_whisperx_import(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = _write_external_alignment(tmp_path / "alignment.external.json")
    original_import = builtins.__import__

    def guarded_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "whisperx":
            raise AssertionError("whisperx should not be imported in the main pipeline")
        return original_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", guarded_import)
    result = load_external_alignment(
        payload_path=path,
        lesson_id="lesson-a",
        expected_language="no",
        seed_segments=_seed_segments(),
    )

    assert result.aligner_used == "faster-whisper-external"
