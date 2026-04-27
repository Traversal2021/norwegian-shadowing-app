"""External alignment JSON ingestion and external runner adapters."""

from __future__ import annotations

import json
import os
import shlex
import shutil
import subprocess
import tempfile
from dataclasses import replace
from pathlib import Path

from ..errors import AlignmentError
from ..language_config import DEFAULT_LANGUAGE
from ..models import Segment, Token
from ..text_utils import is_punctuation_token
from .base import AlignerRun, AlignerRuntimeInfo, BaseAligner

FASTWHISPER_ALIGNER_ENV = "SHADOWING_FASTWHISPER_CMD"
WHISPERX_ALIGNER_ENV = "SHADOWING_WHISPERX_CMD"


class ExistingExternalAlignmentAligner(BaseAligner):
    """Load an already-written standardized external alignment JSON file."""

    def __init__(
        self,
        *,
        lesson_id: str,
        language: str,
        external_alignment_path: str | Path | None,
    ) -> None:
        self.lesson_id = lesson_id
        self.language = language
        self.external_alignment_path = (
            Path(external_alignment_path).resolve() if external_alignment_path is not None else None
        )

    @property
    def name(self) -> str:
        return "external-file"

    def check_available(self) -> AlignerRuntimeInfo:
        if self.external_alignment_path and self.external_alignment_path.is_file():
            return AlignerRuntimeInfo(True)
        if self.external_alignment_path is None:
            return AlignerRuntimeInfo(False, "no external alignment path configured")
        return AlignerRuntimeInfo(False, f"external alignment JSON not found at {self.external_alignment_path}")

    def align(self, audio_path: str, segments: list[Segment]) -> AlignerRun:
        availability = self.check_available()
        if not availability.available:
            raise AlignmentError(availability.reason)
        assert self.external_alignment_path is not None
        return load_external_alignment(
            payload_path=self.external_alignment_path,
            lesson_id=self.lesson_id,
            expected_language=self.language,
            seed_segments=segments,
        )


class ExternalRunnerAligner(BaseAligner):
    """Run an external backend that writes a standardized alignment JSON file."""

    def __init__(
        self,
        *,
        lesson_id: str,
        language: str,
        transcript_path: str | Path,
        segments_json_path: str | Path,
        external_alignment_path: str | Path,
        command_env_var: str,
        backend_name: str,
        include_transcript: bool,
    ) -> None:
        self.lesson_id = lesson_id
        self.language = language
        self.transcript_path = Path(transcript_path).resolve()
        self.segments_json_path = Path(segments_json_path).resolve()
        self.external_alignment_path = Path(external_alignment_path).resolve()
        self.command_env_var = command_env_var
        self.backend_name = backend_name
        self.include_transcript = include_transcript

    @property
    def name(self) -> str:
        return self.backend_name

    @property
    def supports_token_timing(self) -> bool:
        return True

    def check_available(self) -> AlignerRuntimeInfo:
        command = os.environ.get(self.command_env_var, "").strip()
        if not command:
            return AlignerRuntimeInfo(False, f"{self.command_env_var} is not set.")
        executable = shlex.split(command)[0]
        if shutil.which(executable) is None:
            return AlignerRuntimeInfo(False, f"configured executable not found on PATH: {executable}")
        return AlignerRuntimeInfo(True)

    def align(self, audio_path: str, segments: list[Segment]) -> AlignerRun:
        availability = self.check_available()
        if not availability.available:
            raise AlignmentError(availability.reason)

        command = os.environ[self.command_env_var].strip()
        with tempfile.TemporaryDirectory(prefix=f"shadowing-{self.backend_name}-") as tmp:
            output_path = Path(tmp) / "alignment.external.json"
            args = [
                *shlex.split(command),
                "--lesson-id",
                self.lesson_id,
                "--audio",
                str(Path(audio_path).resolve()),
                "--segments-json",
                str(self.segments_json_path),
                "--language",
                self.language,
                "--output",
                str(output_path),
            ]
            if self.include_transcript:
                args.extend(["--transcript", str(self.transcript_path)])
            try:
                completed = subprocess.run(
                    args,
                    check=False,
                    capture_output=True,
                    text=True,
                    timeout=3600,
                )
            except (OSError, subprocess.TimeoutExpired) as exc:
                raise AlignmentError(f"{self.backend_name} runner failed to start or timed out: {exc}") from exc

            if completed.returncode != 0:
                detail = (completed.stderr or completed.stdout or "no output").strip()
                raise AlignmentError(
                    f"{self.backend_name} runner exited with code {completed.returncode}: {detail}"
                )
            if not output_path.is_file():
                raise AlignmentError(
                    f"{self.backend_name} runner completed but did not write the expected alignment JSON."
                )
            payload_text = output_path.read_text(encoding="utf-8")

        self.external_alignment_path.parent.mkdir(parents=True, exist_ok=True)
        self.external_alignment_path.write_text(payload_text, encoding="utf-8")
        return load_external_alignment(
            payload_path=self.external_alignment_path,
            lesson_id=self.lesson_id,
            expected_language=self.language,
            seed_segments=segments,
        )


def load_external_alignment(
    *,
    payload_path: str | Path,
    lesson_id: str,
    expected_language: str,
    seed_segments: list[Segment],
) -> AlignerRun:
    path = Path(payload_path).resolve()
    if not path.is_file():
        raise AlignmentError(f"External alignment JSON does not exist: {path}")

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise AlignmentError(f"External alignment JSON is invalid: {exc}") from exc

    if not isinstance(payload, dict):
        raise AlignmentError("External alignment payload must be a JSON object.")
    if payload.get("schemaVersion") != 1:
        raise AlignmentError("External alignment schemaVersion must be 1.")
    if payload.get("lessonId") != lesson_id:
        raise AlignmentError(
            f"External alignment lessonId mismatch: expected {lesson_id!r}, got {payload.get('lessonId')!r}."
        )

    language = payload.get("language")
    accepted_languages = {expected_language, DEFAULT_LANGUAGE.metadata_language, DEFAULT_LANGUAGE.asr_language}
    if language and language not in accepted_languages:
        raise AlignmentError(
            "External alignment language mismatch: "
            f"expected one of {sorted(accepted_languages)!r}, got {language!r}."
        )

    aligner_used = payload.get("aligner")
    if not isinstance(aligner_used, str) or not aligner_used.strip():
        raise AlignmentError("External alignment must include a non-empty aligner field.")

    raw_segments = payload.get("segments")
    if not isinstance(raw_segments, list) or not raw_segments:
        raise AlignmentError("External alignment must include a non-empty segments array.")

    by_id = {segment.id: segment for segment in seed_segments}
    aligned: list[Segment] = []
    warnings = _string_list(payload.get("warnings"))
    notes = _string_list(payload.get("notes"))

    for raw_segment in raw_segments:
        if not isinstance(raw_segment, dict):
            raise AlignmentError("Each external alignment segment must be an object.")
        segment_id = _required_str(raw_segment, "id")
        seed = by_id.get(segment_id)
        if seed is None:
            raise AlignmentError(f"External alignment returned unknown segment id: {segment_id}")
        start = _required_float(raw_segment, "start")
        end = _required_float(raw_segment, "end")
        if end <= start:
            raise AlignmentError(f"External alignment segment {segment_id} has non-positive duration.")

        words = raw_segment.get("words")
        tokens = _merge_external_words(seed.tokens, words)
        aligned.append(
            replace(
                seed,
                start_time=round(start, 3),
                end_time=round(end, 3),
                text_plain=_optional_str(raw_segment.get("text")) or seed.text_plain,
                tokens=tokens,
            )
        )

    if len(aligned) != len(seed_segments):
        raise AlignmentError(
            f"External alignment returned {len(aligned)} segment(s), expected {len(seed_segments)}."
        )

    ordered = [next(segment for segment in aligned if segment.id == seed.id) for seed in seed_segments]
    return AlignerRun(
        segments=ordered,
        warnings=warnings,
        notes=notes,
        aligner_used=aligner_used.strip(),
        external_alignment_path=str(path),
    )


def _merge_external_words(seed_tokens: list[Token], raw_words: object) -> list[Token]:
    if not isinstance(raw_words, list):
        return seed_tokens

    normalized_words: list[dict[str, object]] = []
    for raw_word in raw_words:
        if not isinstance(raw_word, dict):
            continue
        word = _optional_str(raw_word.get("word"))
        start = _optional_float(raw_word.get("start"))
        end = _optional_float(raw_word.get("end"))
        if not word or start is None or end is None or end <= start:
            continue
        normalized_words.append(
            {
                "word": _normalize_word(word),
                "start": round(start, 3),
                "end": round(end, 3),
                "confidence": _optional_float(raw_word.get("confidence")),
            }
        )

    if not normalized_words:
        return seed_tokens

    merged: list[Token] = []
    cursor = 0
    for token in seed_tokens:
        if is_punctuation_token(token.text):
            merged.append(token)
            continue
        wanted = _normalize_word(token.text)
        match_index = _find_next_word(normalized_words, wanted, cursor)
        if match_index is None:
            merged.append(token)
            continue
        timing = normalized_words[match_index]
        cursor = match_index + 1
        merged.append(
            replace(
                token,
                start=float(timing["start"]),
                end=float(timing["end"]),
                confidence=_optional_float(timing.get("confidence")),
            )
        )
    return merged


def _find_next_word(words: list[dict[str, object]], wanted: str, start: int) -> int | None:
    for index in range(start, len(words)):
        if words[index]["word"] == wanted:
            return index
    return None


def _normalize_word(value: str) -> str:
    return "".join(ch.casefold() for ch in value if ch.isalnum())


def _required_str(payload: dict[str, object], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise AlignmentError(f"External alignment segment missing non-empty string field {key!r}.")
    return value


def _optional_str(value: object) -> str | None:
    return value if isinstance(value, str) and value else None


def _required_float(payload: dict[str, object], key: str) -> float:
    value = payload.get(key)
    if not isinstance(value, int | float):
        raise AlignmentError(f"External alignment segment missing numeric field {key!r}.")
    return float(value)


def _optional_float(value: object) -> float | None:
    if isinstance(value, int | float):
        return float(value)
    return None


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]
