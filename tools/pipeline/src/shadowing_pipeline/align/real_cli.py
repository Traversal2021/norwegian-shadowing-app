"""Optional subprocess adapter for an external real alignment command.

The adapter is intentionally generic. Set ``SHADOWING_REAL_ALIGNER_CMD`` to a
command that accepts:

    <command> --audio audio.mp3 --text clean.no.txt --segments segments.json

and writes JSON to stdout:

    {
      "segments": [
        {
          "id": "s1",
          "startTime": 0.0,
          "endTime": 2.1,
          "tokens": [{"index": 0, "start": 0.0, "end": 0.4, "confidence": 0.9}],
          "confidence": 0.88,
          "notes": []
        }
      ],
      "warnings": [],
      "notes": []
    }
"""

from __future__ import annotations

import json
import os
import shlex
import shutil
import subprocess
import tempfile
from dataclasses import replace
from pathlib import Path
from typing import Any

from ..errors import AlignmentError
from ..language_config import DEFAULT_LANGUAGE
from ..models import Segment, Token
from ..text_utils import tokens_to_text
from .base import AlignerRun, AlignerRuntimeInfo, BaseAligner

REAL_ALIGNER_ENV = "SHADOWING_REAL_ALIGNER_CMD"


class RealCliAligner(BaseAligner):
    """Adapter for an explicitly configured external aligner command."""

    @property
    def name(self) -> str:
        return "real-cli"

    @property
    def supports_token_timing(self) -> bool:
        return True

    def check_available(self) -> AlignerRuntimeInfo:
        command = os.environ.get(REAL_ALIGNER_ENV, "").strip()
        if not command:
            return AlignerRuntimeInfo(
                available=False,
                reason=f"{REAL_ALIGNER_ENV} is not set.",
            )
        executable = shlex.split(command)[0]
        if not shutil.which(executable):
            return AlignerRuntimeInfo(
                available=False,
                reason=f"Configured real aligner executable not found on PATH: {executable}",
            )
        return AlignerRuntimeInfo(available=True)

    def align(self, audio_path: str, segments: list[Segment]) -> AlignerRun:
        availability = self.check_available()
        if not availability.available:
            raise AlignmentError(availability.reason)

        command = os.environ[REAL_ALIGNER_ENV]
        with tempfile.TemporaryDirectory(prefix="shadowing-align-") as tmp:
            tmp_dir = Path(tmp)
            clean_text_path = tmp_dir / DEFAULT_LANGUAGE.clean_text_filename
            segments_path = tmp_dir / "segments.json"
            clean_text_path.write_text(
                "\n".join(tokens_to_text(segment.tokens) for segment in segments) + "\n",
                encoding="utf-8",
            )
            segments_path.write_text(
                json.dumps(
                    [
                        {
                            "id": segment.id,
                            "text": tokens_to_text(segment.tokens),
                            "tokens": [token.text for token in segment.tokens],
                        }
                        for segment in segments
                    ],
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )

            args = [
                *shlex.split(command),
                "--audio",
                str(Path(audio_path).resolve()),
                "--text",
                str(clean_text_path),
                "--segments",
                str(segments_path),
            ]
            try:
                completed = subprocess.run(
                    args,
                    check=False,
                    capture_output=True,
                    text=True,
                    timeout=600,
                )
            except (OSError, subprocess.TimeoutExpired) as exc:
                raise AlignmentError(f"Real aligner command failed to start or timed out: {exc}") from exc

        if completed.returncode != 0:
            stderr = completed.stderr.strip() or "no stderr"
            raise AlignmentError(
                f"Real aligner exited with code {completed.returncode}: {stderr}"
            )

        try:
            payload = json.loads(completed.stdout)
        except json.JSONDecodeError as exc:
            raise AlignmentError(f"Real aligner returned invalid JSON: {exc}") from exc

        return _parse_real_aligner_payload(payload, segments)


def _parse_real_aligner_payload(payload: object, seed_segments: list[Segment]) -> AlignerRun:
    if not isinstance(payload, dict):
        raise AlignmentError("Real aligner output must be a JSON object.")
    raw_segments = payload.get("segments")
    if not isinstance(raw_segments, list):
        raise AlignmentError("Real aligner output must include a segments array.")

    by_id = {segment.id: segment for segment in seed_segments}
    aligned: list[Segment] = []
    for raw in raw_segments:
        if not isinstance(raw, dict):
            raise AlignmentError("Each real aligner segment must be an object.")
        segment_id = _string(raw, "id")
        seed = by_id.get(segment_id)
        if seed is None:
            raise AlignmentError(f"Real aligner returned unknown segment id: {segment_id}")
        start = _float(raw, "startTime")
        end = _float(raw, "endTime")
        if end <= start:
            raise AlignmentError(f"Real aligner segment {segment_id} has non-positive duration.")
        aligned.append(
            replace(
                seed,
                start_time=round(start, 3),
                end_time=round(end, 3),
                tokens=_merge_token_timings(seed.tokens, raw.get("tokens")),
            )
        )

    if len(aligned) != len(seed_segments):
        raise AlignmentError(
            f"Real aligner returned {len(aligned)} segment(s), expected {len(seed_segments)}."
        )

    aligned.sort(key=lambda segment: seed_segments.index(by_id[segment.id]))
    warnings = _string_list(payload.get("warnings"))
    notes = _string_list(payload.get("notes"))
    return AlignerRun(segments=aligned, warnings=warnings, notes=notes)


def _merge_token_timings(seed_tokens: list[Token], raw_tokens: object) -> list[Token]:
    if not isinstance(raw_tokens, list):
        return seed_tokens
    merged = list(seed_tokens)
    for raw in raw_tokens:
        if not isinstance(raw, dict):
            continue
        index = raw.get("index")
        if not isinstance(index, int) or index < 0 or index >= len(merged):
            continue
        merged[index] = replace(
            merged[index],
            start=_optional_float(raw.get("start")),
            end=_optional_float(raw.get("end")),
            confidence=_optional_float(raw.get("confidence")),
        )
    return merged


def _string(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value:
        raise AlignmentError(f"Real aligner segment missing string field {key!r}.")
    return value


def _float(payload: dict[str, Any], key: str) -> float:
    value = payload.get(key)
    if not isinstance(value, int | float):
        raise AlignmentError(f"Real aligner segment missing numeric field {key!r}.")
    return float(value)


def _optional_float(value: object) -> float | None:
    if isinstance(value, int | float):
        return round(float(value), 3)
    return None


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]
