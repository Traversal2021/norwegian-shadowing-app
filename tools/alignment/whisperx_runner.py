#!/usr/bin/env python3
"""Run WhisperX externally and write standardized alignment JSON."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
PIPELINE_SRC = REPO_ROOT / "tools" / "pipeline" / "src"
if str(PIPELINE_SRC) not in sys.path:
    sys.path.insert(0, str(PIPELINE_SRC))

from shadowing_pipeline.align.asr_mapping import SentenceEntry  # noqa: E402
from shadowing_pipeline.language_config import DEFAULT_LANGUAGE  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="External WhisperX runner for Norwegian shadowing lessons")
    parser.add_argument("--lesson-id")
    parser.add_argument("--audio", type=Path)
    parser.add_argument("--transcript", type=Path)
    parser.add_argument("--segments-json", type=Path)
    parser.add_argument("--language", default=DEFAULT_LANGUAGE.asr_language)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--self-check", action="store_true", help="Import WhisperX and exit.")
    args = parser.parse_args()

    try:
        import whisperx  # type: ignore[import-not-found]
    except Exception as exc:  # pragma: no cover - exercised only in real WhisperX envs
        raise SystemExit(f"WhisperX import failed in external environment: {exc}") from exc

    if args.self_check:
        print("whisperx self-check ok")
        return

    if not all([args.lesson_id, args.audio, args.transcript, args.segments_json, args.output]):
        raise SystemExit("Missing required arguments for WhisperX alignment run.")

    segment_entries = _load_segments_json(args.segments_json)
    transcript_text = args.transcript.read_text(encoding="utf-8").strip()

    device = os.environ.get("SHADOWING_WHISPERX_DEVICE", "cpu")
    model_name = os.environ.get("SHADOWING_WHISPERX_MODEL", "small")
    compute_type = os.environ.get("SHADOWING_WHISPERX_COMPUTE_TYPE", "int8")
    batch_size = int(os.environ.get("SHADOWING_WHISPERX_BATCH_SIZE", "8"))

    try:  # pragma: no cover - depends on real WhisperX installation/models
        model = whisperx.load_model(model_name, device, compute_type=compute_type, language=args.language)
        transcription = model.transcribe(
            str(args.audio),
            batch_size=batch_size,
            language=args.language,
        )
        detected_language = transcription.get("language") or args.language
        align_model, metadata = whisperx.load_align_model(language_code=detected_language, device=device)
        aligned = whisperx.align(
            transcription["segments"],
            align_model,
            metadata,
            str(args.audio),
            device,
            return_char_alignments=False,
        )
    except Exception as exc:
        raise SystemExit(f"WhisperX execution failed: {exc}") from exc

    raw_words = aligned.get("word_segments") or _collect_words_from_segments(aligned.get("segments"))
    normalized_words = _normalize_word_segments(raw_words)
    if not normalized_words:
        raise SystemExit("WhisperX returned no usable word timestamps.")

    mapped_segments, warnings = _map_words_to_seed_segments(segment_entries, normalized_words)
    if _normalize_text(transcript_text) and _normalize_text(" ".join(item.text for item in segment_entries)) not in {
        _normalize_text(transcript_text),
        "",
    }:
        warnings.append(
            "Transcript text and seed segment text differ after normalization; mapping relied on seed segment order."
        )

    payload = {
        "schemaVersion": 1,
        "lessonId": args.lesson_id,
        "aligner": "whisperx-external",
        "language": args.language,
        "segments": mapped_segments,
        "warnings": warnings,
        "notes": [
            f"model={model_name}",
            f"device={device}",
            f"computeType={compute_type}",
            "Word timestamps were mapped back to canonical sentence segments in order.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _load_segments_json(path: Path) -> list[SentenceEntry]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    segments = payload.get("segments")
    if not isinstance(segments, list) or not segments:
        raise SystemExit(f"Seed segments JSON must include a non-empty segments array: {path}")
    result: list[SentenceEntry] = []
    for segment in segments:
        if not isinstance(segment, dict):
            continue
        segment_id = segment.get("id")
        text = segment.get("text")
        if isinstance(segment_id, str) and isinstance(text, str) and text.strip():
            result.append(SentenceEntry(id=segment_id, text=text))
    if not result:
        raise SystemExit(f"Seed segments JSON does not include usable id/text entries: {path}")
    return result


def _collect_words_from_segments(segments: object) -> list[dict[str, object]]:
    if not isinstance(segments, list):
        return []
    words: list[dict[str, object]] = []
    for segment in segments:
        if not isinstance(segment, dict):
            continue
        raw_words = segment.get("words")
        if not isinstance(raw_words, list):
            continue
        for word in raw_words:
            if isinstance(word, dict):
                words.append(word)
    return words


def _normalize_word_segments(raw_words: list[dict[str, object]]) -> list[dict[str, object]]:
    normalized: list[dict[str, object]] = []
    for raw in raw_words:
        word = raw.get("word")
        start = raw.get("start")
        end = raw.get("end")
        if not isinstance(word, str) or not isinstance(start, (int, float)) or not isinstance(end, (int, float)):
            continue
        if end <= start:
            continue
        normalized.append(
            {
                "word": _normalize_word(word),
                "displayWord": word,
                "start": round(float(start), 3),
                "end": round(float(end), 3),
                "confidence": round(float(raw.get("score")), 3)
                if isinstance(raw.get("score"), (int, float))
                else None,
            }
        )
    return normalized


def _map_words_to_seed_segments(
    segment_entries: list[SentenceEntry],
    words: list[dict[str, object]],
) -> tuple[list[dict[str, object]], list[str]]:
    cursor = 0
    warnings: list[str] = []
    mapped: list[dict[str, object]] = []

    for segment in segment_entries:
        expected_words = [token for token in (_normalize_word(part) for part in segment.text.split()) if token]
        matched_words: list[dict[str, object]] = []
        for expected in expected_words:
            match_index = _find_next_word(words, expected, cursor)
            if match_index is None:
                continue
            matched = words[match_index]
            matched_words.append(matched)
            cursor = match_index + 1

        if not matched_words:
            raise SystemExit(f"WhisperX could not map any word timings for segment {segment.id}.")

        match_ratio = len(matched_words) / max(len(expected_words), 1)
        if match_ratio < 0.6:
            warnings.append(
                f"Low-confidence sentence mapping for {segment.id}: matched {len(matched_words)} of {len(expected_words)} words."
            )

        mapped.append(
            {
                "id": segment.id,
                "text": segment.text,
                "start": matched_words[0]["start"],
                "end": matched_words[-1]["end"],
                "words": [
                    {
                        "word": item["displayWord"],
                        "start": item["start"],
                        "end": item["end"],
                        **({"confidence": item["confidence"]} if item["confidence"] is not None else {}),
                    }
                    for item in matched_words
                ],
            }
        )

    return mapped, warnings


def _find_next_word(words: list[dict[str, object]], expected: str, start: int) -> int | None:
    for index in range(start, len(words)):
        if words[index]["word"] == expected:
            return index
    return None


def _normalize_word(value: str) -> str:
    return re.sub(r"[^\wæøåÆØÅ]+", "", value, flags=re.UNICODE).casefold()


def _normalize_text(value: str) -> str:
    return " ".join(_normalize_word(part) for part in value.split() if _normalize_word(part))


if __name__ == "__main__":
    main()
