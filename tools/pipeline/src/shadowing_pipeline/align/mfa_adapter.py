"""Montreal Forced Aligner adapter."""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from dataclasses import replace
from pathlib import Path

from ..errors import AlignmentError
from ..models import Segment, Token
from ..text_utils import is_punctuation_token
from .base import AlignerRun, AlignerRuntimeInfo, BaseAligner
from .whisperx_adapter import _find_next_word, _float_or_none, _normalize_word


class MfaAligner(BaseAligner):
    @property
    def name(self) -> str:
        return "mfa"

    @property
    def supports_token_timing(self) -> bool:
        return True

    def check_available(self) -> AlignerRuntimeInfo:
        if not shutil.which("mfa"):
            return AlignerRuntimeInfo(False, "Montreal Forced Aligner executable 'mfa' is not on PATH.")
        if not os.environ.get("SHADOWING_MFA_DICTIONARY") or not os.environ.get("SHADOWING_MFA_ACOUSTIC_MODEL"):
            return AlignerRuntimeInfo(
                False,
                "MFA requires SHADOWING_MFA_DICTIONARY and SHADOWING_MFA_ACOUSTIC_MODEL.",
            )
        return AlignerRuntimeInfo(True)

    def align(self, audio_path: str, segments: list[Segment]) -> AlignerRun:
        availability = self.check_available()
        if not availability.available:
            raise AlignmentError(availability.reason)
        dictionary = os.environ["SHADOWING_MFA_DICTIONARY"]
        acoustic_model = os.environ["SHADOWING_MFA_ACOUSTIC_MODEL"]

        with tempfile.TemporaryDirectory(prefix="shadowing-mfa-") as temp_root:
            root = Path(temp_root)
            corpus = root / "corpus"
            output = root / "output"
            corpus.mkdir()
            output.mkdir()
            shutil.copyfile(audio_path, corpus / "lesson.wav")
            transcript = " ".join(segment.text_plain or " ".join(t.text for t in segment.tokens) for segment in segments)
            (corpus / "lesson.lab").write_text(transcript, encoding="utf-8")
            command = [
                "mfa",
                "align",
                str(corpus),
                dictionary,
                acoustic_model,
                str(output),
                "--clean",
                "--overwrite",
                "--single_speaker",
            ]
            try:
                subprocess.run(command, check=True, capture_output=True, text=True)
            except (OSError, subprocess.CalledProcessError) as exc:
                stderr = exc.stderr.strip() if isinstance(exc, subprocess.CalledProcessError) else str(exc)
                raise AlignmentError(f"MFA alignment failed: {stderr}") from exc

            textgrid = next(output.rglob("*.TextGrid"), None)
            if textgrid is None:
                raise AlignmentError("MFA did not produce a TextGrid output.")
            word_intervals = _parse_textgrid_words(textgrid)
            if not word_intervals:
                raise AlignmentError("MFA TextGrid did not contain word intervals.")
            return AlignerRun(
                segments=_map_words_to_segments(segments, word_intervals),
                notes=["MFA TextGrid word intervals were mapped back to canonical sentence segments."],
            )


def _parse_textgrid_words(path: Path) -> list[dict[str, object]]:
    lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    intervals: list[dict[str, object]] = []
    current: dict[str, object] = {}
    for raw in lines:
        line = raw.strip()
        if line.startswith("xmin ="):
            current["start"] = _float_or_none(line.split("=", 1)[1].strip())
        elif line.startswith("xmax ="):
            current["end"] = _float_or_none(line.split("=", 1)[1].strip())
        elif line.startswith("text ="):
            text = line.split("=", 1)[1].strip().strip('"')
            if text and text not in {"<eps>", "sil", "sp"}:
                intervals.append(
                    {
                        "word": _normalize_word(text),
                        "start": current.get("start"),
                        "end": current.get("end"),
                        "score": None,
                    }
                )
            current = {}
    return [item for item in intervals if item["word"] and item["start"] is not None and item["end"] is not None]


def _map_words_to_segments(segments: list[Segment], word_intervals: list[dict[str, object]]) -> list[Segment]:
    cursor = 0
    result: list[Segment] = []
    for segment in segments:
        tokens: list[Token] = []
        timings: list[dict[str, object]] = []
        for token in segment.tokens:
            if is_punctuation_token(token.text):
                tokens.append(token)
                continue
            match_index = _find_next_word(word_intervals, _normalize_word(token.text), cursor)
            if match_index is None:
                tokens.append(token)
                continue
            timing = word_intervals[match_index]
            cursor = match_index + 1
            timings.append(timing)
            tokens.append(replace(token, start=timing["start"], end=timing["end"]))
        if not timings:
            raise AlignmentError(f"MFA could not map timestamps for segment {segment.id}.")
        result.append(
            replace(
                segment,
                start_time=round(float(timings[0]["start"]), 3),
                end_time=round(float(timings[-1]["end"]), 3),
                tokens=tokens,
            )
        )
    return result
