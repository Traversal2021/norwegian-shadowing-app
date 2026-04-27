"""Conservative repair utility for Norwegian inline gloss markup."""

from __future__ import annotations

import json
import re
import shutil
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .errors import PipelineError
from .ingest import resolve_lesson_text_paths
from .language_config import DEFAULT_LANGUAGE
from .parse_annotations import strip_annotations
from .sentence_split import split_annotated_sentences

PROJECT_ROOT = Path(__file__).resolve().parents[4]
RAW_ROOT = PROJECT_ROOT / "content" / "raw"

_CLOSING_QUOTES = {'"', "'", "”", "’", "»"}
_QUOTE_TRANSLATION = str.maketrans(
    {
        "“": '"',
        "”": '"',
        "„": '"',
        "‟": '"',
        "«": '"',
        "»": '"',
        "‘": "'",
        "’": "'",
        "‚": "'",
        "‛": "'",
    }
)
_WORD_RE = re.compile(r"[^\W_]+(?:[-'][^\W_]+)*", re.UNICODE)
_PUNCT_SPACING_RE = re.compile(r"\s*([,.;:!?])\s*")
_QUOTE_SPACING_RE = re.compile(r"\s*([\"'])\s*")


@dataclass(frozen=True)
class SentenceSpan:
    text: str
    start: int
    end: int


@dataclass(frozen=True)
class GlossRecord:
    gloss: str
    options: list[str]
    occurrence_by_option: dict[str, int]
    preferred_longest: bool
    source_visible: str


@dataclass(frozen=True)
class RepairResult:
    text: str
    report: dict[str, Any]


def repair_lesson_annotated(
    lesson_id: str,
    *,
    raw_root: Path = RAW_ROOT,
    write: bool = False,
    backup: bool = False,
    output_path: Path | None = None,
    write_report: bool = False,
    force: bool = False,
) -> tuple[Path, Path | None, RepairResult]:
    """Repair one lesson and write the regenerated annotation file."""
    lesson_dir = raw_root / lesson_id
    original_path, annotated_path = resolve_lesson_text_paths(lesson_dir)
    if not original_path.is_file():
        raise PipelineError(f"Missing original text file: {original_path}")
    if not annotated_path.is_file():
        raise PipelineError(f"Missing annotated text file: {annotated_path}")

    original_text = original_path.read_text(encoding="utf-8")
    annotated_text = annotated_path.read_text(encoding="utf-8")
    result = repair_annotated_text(
        lesson_id=lesson_id,
        original_text=original_text,
        annotated_text=annotated_text,
        original_path=original_path,
        annotated_path=annotated_path,
    )

    destination = annotated_path if write else output_path
    if destination is None:
        destination = lesson_dir / DEFAULT_LANGUAGE.regenerated_annotated_filename
    destination = destination.resolve()
    if destination.exists() and not force and destination != annotated_path:
        raise PipelineError(f"Refusing to overwrite existing output without --force: {destination}")

    if write and backup:
        backup_path = lesson_dir / DEFAULT_LANGUAGE.backup_annotated_filename
        if backup_path.exists() and not force:
            raise PipelineError(f"Refusing to overwrite existing backup without --force: {backup_path}")
        shutil.copyfile(annotated_path, backup_path)

    destination.write_text(result.text, encoding="utf-8")

    report_path = None
    if write_report:
        report_path = lesson_dir / "annotated.repair-report.json"
        if report_path.exists() and not force:
            raise PipelineError(f"Refusing to overwrite existing report without --force: {report_path}")
        report_path.write_text(
            json.dumps(result.report, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    return destination, report_path, result


def repair_annotated_text(
    *,
    lesson_id: str,
    original_text: str,
    annotated_text: str,
    original_path: Path | None = None,
    annotated_path: Path | None = None,
) -> RepairResult:
    """Regenerate annotated text using original text as the exact backbone."""
    original_spans = split_original_sentence_spans(original_text)
    annotated_sentences = split_annotated_sentences(annotated_text)
    stripped_annotated = [strip_annotations(sentence) for sentence in annotated_sentences]

    warnings: list[str] = []
    details: list[dict[str, Any]] = []
    rebuilt_parts: list[str] = []
    cursor = 0
    paired = 0
    unresolved = 0
    inserted_count = 0
    skipped_count = 0

    for index, original_span in enumerate(original_spans):
        rebuilt_parts.append(original_text[cursor : original_span.start])
        original_sentence = original_span.text
        if index >= len(annotated_sentences):
            warning = f"sentence {index + 1}: no annotated sentence to pair"
            warnings.append(warning)
            details.append(_unresolved_detail(index, original_sentence, warning))
            rebuilt_parts.append(original_sentence)
            unresolved += 1
            cursor = original_span.end
            continue

        annotated_sentence = annotated_sentences[index]
        cleaned_annotated = stripped_annotated[index]
        if normalize_for_matching(cleaned_annotated) != normalize_for_matching(original_sentence):
            warning = f"sentence {index + 1}: normalized original and annotated text do not match"
            warnings.append(warning)
            details.append(_unresolved_detail(index, original_sentence, warning))
            rebuilt_parts.append(original_sentence)
            unresolved += 1
            cursor = original_span.end
            continue

        sentence_text, sentence_detail = _repair_sentence(
            sentence_index=index + 1,
            original_sentence=original_sentence,
            annotated_sentence=annotated_sentence,
        )
        warnings.extend(sentence_detail["warnings"])
        inserted_count += sentence_detail["insertedGlossCount"]
        skipped_count += sentence_detail["skippedGlossCount"]
        details.append(sentence_detail)
        rebuilt_parts.append(sentence_text)
        paired += 1
        cursor = original_span.end

    rebuilt_parts.append(original_text[cursor:])

    if len(annotated_sentences) > len(original_spans):
        for index in range(len(original_spans), len(annotated_sentences)):
            warning = f"sentence {index + 1}: annotated sentence has no original sentence to pair"
            warnings.append(warning)
            unresolved += 1
            details.append(_unresolved_detail(index, "", warning))

    report: dict[str, Any] = {
        "lessonId": lesson_id,
        "generatedAt": datetime.now(UTC).isoformat(),
        "sourceFiles": {
            "original": str(original_path) if original_path else None,
            "annotated": str(annotated_path) if annotated_path else None,
        },
        "totalOriginalSentences": len(original_spans),
        "totalAnnotatedSentences": len(annotated_sentences),
        "pairedSentences": paired,
        "unresolvedSentences": unresolved,
        "insertedGlossCount": inserted_count,
        "skippedGlossCount": skipped_count,
        "warnings": warnings,
        "sentences": details,
    }
    return RepairResult(text="".join(rebuilt_parts), report=report)


def split_original_sentence_spans(text: str) -> list[SentenceSpan]:
    """Split text into sentence spans while preserving exact source slices."""
    spans: list[SentenceSpan] = []
    start: int | None = None
    paren_depth = 0
    index = 0
    length = len(text)

    while index < length:
        char = text[index]
        if start is None and not char.isspace():
            start = index

        if start is None:
            index += 1
            continue

        if char == "(":
            paren_depth += 1
        elif char == ")" and paren_depth > 0:
            paren_depth -= 1
        elif char in ".?!" and paren_depth == 0:
            end = index + 1
            while end < length and text[end] in _CLOSING_QUOTES:
                end += 1
            if end >= length or text[end].isspace():
                spans.append(SentenceSpan(text=text[start:end], start=start, end=end))
                start = None
                index = end
                continue

        index += 1

    if start is not None:
        spans.append(SentenceSpan(text=text[start:length], start=start, end=length))
    return spans


def normalize_for_matching(text: str) -> str:
    """Normalize only for conservative comparisons, never for output."""
    normalized = text.translate(_QUOTE_TRANSLATION)
    normalized = _PUNCT_SPACING_RE.sub(r"\1 ", normalized)
    normalized = _QUOTE_SPACING_RE.sub(r"\1", normalized)
    return " ".join(normalized.split()).strip()


def extract_gloss_records(annotated_sentence: str) -> list[GlossRecord]:
    """Extract old glosses and visible-text placement candidates."""
    records: list[GlossRecord] = []
    visible_parts: list[str] = []
    previous_boundary = 0
    index = 0
    while index < len(annotated_sentence):
        char = annotated_sentence[index]
        if char != "(":
            visible_parts.append(char)
            if char in ",.;:!?":
                previous_boundary = len("".join(visible_parts))
            index += 1
            continue

        closing = annotated_sentence.find(")", index + 1)
        if closing == -1:
            visible_parts.append(char)
            index += 1
            continue

        gloss = annotated_sentence[index + 1 : closing].strip()
        visible_so_far = "".join(visible_parts)
        if gloss:
            records.append(_build_gloss_record(visible_so_far, previous_boundary, gloss))
        index = closing + 1

    return records


def _repair_sentence(
    *,
    sentence_index: int,
    original_sentence: str,
    annotated_sentence: str,
) -> tuple[str, dict[str, Any]]:
    records = extract_gloss_records(annotated_sentence)
    insertions: dict[int, list[str]] = {}
    occupied: list[tuple[int, int]] = []
    warnings: list[str] = []
    placed: list[dict[str, Any]] = []
    skipped = 0

    for record in records:
        placement = _place_record(record, original_sentence, occupied)
        if placement is None:
            warning = (
                f"sentence {sentence_index}: skipped gloss {record.gloss!r} "
                f"for visible text {record.source_visible!r}"
            )
            warnings.append(warning)
            skipped += 1
            continue

        start, end, visible = placement
        insertions.setdefault(end, []).append(record.gloss)
        occupied.append((start, end))
        placed.append({"visibleText": visible, "gloss": record.gloss, "start": start, "end": end})

    repaired = _apply_insertions(original_sentence, insertions)
    detail: dict[str, Any] = {
        "index": sentence_index,
        "paired": True,
        "insertedGlossCount": len(placed),
        "skippedGlossCount": skipped,
        "warnings": warnings,
        "insertions": placed,
    }
    return repaired, detail


def _build_gloss_record(visible_so_far: str, previous_boundary: int, gloss: str) -> GlossRecord:
    word_matches = list(_WORD_RE.finditer(visible_so_far))
    if not word_matches:
        return GlossRecord(
            gloss=gloss,
            options=[],
            occurrence_by_option={},
            preferred_longest=False,
            source_visible="",
        )

    suffix_words = [match.group(0) for match in word_matches[-4:]]
    options: list[str] = []
    for size in range(1, len(suffix_words) + 1):
        options.append(" ".join(suffix_words[-size:]))

    boundary_tail = visible_so_far[previous_boundary:].strip()
    boundary_words = list(_WORD_RE.finditer(boundary_tail))
    preferred_longest = (
        (len(boundary_words) >= 3 or (previous_boundary > 0 and len(boundary_words) >= 2))
        and len(boundary_words) <= 4
        and boundary_words[-1].group(0) == suffix_words[-1]
    )
    source_visible = options[-1] if preferred_longest else options[0]
    ordered = list(reversed(options)) if preferred_longest else options
    return GlossRecord(
        gloss=gloss,
        options=ordered,
        occurrence_by_option={
            option: len(_find_exact_spans(visible_so_far, option)) for option in ordered
        },
        preferred_longest=preferred_longest,
        source_visible=source_visible,
    )


def _place_record(
    record: GlossRecord,
    original_sentence: str,
    occupied: list[tuple[int, int]],
) -> tuple[int, int, str] | None:
    for option in record.options:
        annotated_occurrence = record.occurrence_by_option.get(option)
        if not annotated_occurrence:
            continue
        matches = _find_exact_spans(original_sentence, option)
        if not matches or annotated_occurrence > len(matches):
            continue
        start, end = matches[annotated_occurrence - 1]
        if any(not (end <= used_start or start >= used_end) for used_start, used_end in occupied):
            continue
        return start, end, original_sentence[start:end]
    return None


def _find_exact_spans(text: str, needle: str) -> list[tuple[int, int]]:
    if not needle:
        return []
    pattern = re.compile(rf"(?<!\w){re.escape(needle)}(?!\w)", re.UNICODE)
    return [(match.start(), match.end()) for match in pattern.finditer(text)]


def _apply_insertions(sentence: str, insertions: dict[int, list[str]]) -> str:
    if not insertions:
        return sentence
    parts: list[str] = []
    cursor = 0
    for end in sorted(insertions):
        parts.append(sentence[cursor:end])
        for gloss in insertions[end]:
            parts.append(f"({gloss})")
        cursor = end
    parts.append(sentence[cursor:])
    return "".join(parts)


def _unresolved_detail(index: int, original_sentence: str, warning: str) -> dict[str, Any]:
    return {
        "index": index + 1,
        "paired": False,
        "originalText": original_sentence,
        "insertedGlossCount": 0,
        "skippedGlossCount": 0,
        "warnings": [warning],
        "insertions": [],
    }
