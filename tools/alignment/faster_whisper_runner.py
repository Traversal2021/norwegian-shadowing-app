#!/usr/bin/env python3
"""Run faster-whisper externally and write standardized alignment JSON."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
PIPELINE_SRC = REPO_ROOT / "tools" / "pipeline" / "src"
if str(PIPELINE_SRC) not in sys.path:
    sys.path.insert(0, str(PIPELINE_SRC))

from shadowing_pipeline.align.asr_mapping import (  # noqa: E402
    AsrSegmentEntry,
    SentenceEntry,
    map_asr_segments_to_sentences,
)
from shadowing_pipeline.language_config import DEFAULT_LANGUAGE  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="External faster-whisper runner for Norwegian shadowing lessons")
    parser.add_argument("--lesson-id")
    parser.add_argument("--audio", type=Path)
    parser.add_argument("--segments-json", type=Path)
    parser.add_argument("--language", default=DEFAULT_LANGUAGE.asr_language)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--model-size", default="small")
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--compute-type", default="int8")
    parser.add_argument("--self-check", action="store_true", help="Import faster-whisper and exit.")
    args = parser.parse_args()

    try:
        from faster_whisper import WhisperModel  # type: ignore[import-not-found]
        import faster_whisper  # type: ignore[import-not-found]
    except Exception as exc:  # pragma: no cover - exercised only in real ASR envs
        raise SystemExit(f"faster-whisper import failed in external environment: {exc}") from exc

    if args.self_check:
        print(f"faster-whisper self-check ok {getattr(faster_whisper, '__version__', 'unknown')}")
        return

    if not all([args.lesson_id, args.audio, args.segments_json, args.output]):
        raise SystemExit("Missing required arguments for faster-whisper alignment run.")

    sentence_entries = _load_segments_json(args.segments_json)

    try:  # pragma: no cover - depends on real faster-whisper installation/models
        model = WhisperModel(args.model_size, device=args.device, compute_type=args.compute_type)
        segments_iter, info = model.transcribe(str(args.audio), language=args.language)
        asr_segments = [
            AsrSegmentEntry(
                start=round(float(segment.start), 3),
                end=round(float(segment.end), 3),
                text=segment.text.strip(),
                confidence=_confidence_from_avg_logprob(getattr(segment, "avg_logprob", None)),
            )
            for segment in segments_iter
            if segment.text and float(segment.end) > float(segment.start)
        ]
    except Exception as exc:
        raise SystemExit(f"faster-whisper execution failed: {exc}") from exc

    if not asr_segments:
        raise SystemExit("faster-whisper returned no usable ASR segments.")

    try:
        mapping = map_asr_segments_to_sentences(sentence_entries, asr_segments)
    except ValueError as exc:
        raise SystemExit(f"faster-whisper mapping failed: {exc}") from exc

    payload = {
        "schemaVersion": 1,
        "lessonId": args.lesson_id,
        "aligner": "faster-whisper-external",
        "language": args.language,
        "segments": [
            {
                "id": segment.id,
                "text": segment.text,
                "start": segment.start,
                "end": segment.end,
                "sourceAsrText": segment.source_asr_text,
                **({"confidence": segment.confidence} if segment.confidence is not None else {}),
                "words": [],
            }
            for segment in mapping.segments
        ],
        "warnings": mapping.warnings,
        "notes": mapping.notes
        + [
            f"model={args.model_size}",
            f"device={args.device}",
            f"computeType={args.compute_type}",
            f"detectedLanguage={getattr(info, 'language', args.language)}",
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


def _confidence_from_avg_logprob(value: object) -> float | None:
    if not isinstance(value, (int, float)):
        return None
    normalized = max(0.0, min(1.0, 1.0 + float(value) / 5.0))
    return round(normalized, 3)


if __name__ == "__main__":
    main()
