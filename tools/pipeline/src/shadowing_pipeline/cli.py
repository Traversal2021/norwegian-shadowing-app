"""CLI entry point for the shadowing pipeline."""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

from .annotated_repair import repair_lesson_annotated
from .errors import PipelineError
from .ingest import list_raw_lesson_dirs, load_raw_lesson, validate_raw_lesson
from .summaries import load_grammar_summary, load_vocab_summary

PROJECT_ROOT = Path(__file__).resolve().parents[4]
RAW_ROOT = PROJECT_ROOT / "content" / "raw"
PROCESSED_ROOT = PROJECT_ROOT / "content" / "processed"


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="shadowing-pipeline",
        description="Norwegian Shadowing lesson ingestion pipeline",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    build_parser = subparsers.add_parser("build", help="Build one or more raw lessons")
    _add_lesson_selection_args(build_parser)
    build_parser.add_argument("--force", action="store_true", help="Rebuild even if output exists")
    build_parser.add_argument(
        "--aligner",
        choices=["auto", "external", "fastwhisper", "whisperx", "fallback"],
        default="auto",
        help="Alignment mode: auto prefers external alignment, then faster-whisper, then WhisperX, then fallback.",
    )
    build_parser.add_argument(
        "--strict-alignment",
        action="store_true",
        help="Fail instead of falling back when real alignment is requested but unavailable/failing.",
    )
    build_parser.add_argument(
        "--external-alignment",
        type=Path,
        help="Path to an external alignment JSON file. Defaults to content/raw/<lesson>/alignment.external.json.",
    )

    validate_parser = subparsers.add_parser("validate", help="Validate one or more raw lessons")
    _add_lesson_selection_args(validate_parser)

    clean_parser = subparsers.add_parser("clean", help="Remove processed output")
    _add_lesson_selection_args(clean_parser)
    clean_parser.add_argument("--yes", action="store_true", help="Confirm deletion")

    init_parser = subparsers.add_parser("init-lesson", help="Create a raw lesson template")
    init_parser.add_argument("--lesson", required=True, help="Lesson id to create under content/raw")
    init_parser.add_argument("--title", required=True, help="Human-readable lesson title")

    repair_parser = subparsers.add_parser(
        "regenerate-annotated",
        help="Regenerate annotated.no.txt from original.no.txt plus old gloss references",
    )
    repair_parser.add_argument("--lesson", required=True, help="Lesson id under content/raw")
    repair_parser.add_argument(
        "--write",
        action="store_true",
        help="Overwrite annotated.no.txt instead of writing annotated.regenerated.no.txt",
    )
    repair_parser.add_argument(
        "--backup",
        action="store_true",
        help="Create annotated.backup.no.txt before overwriting annotated.no.txt",
    )
    repair_parser.add_argument("--output", type=Path, help="Custom output path")
    repair_parser.add_argument(
        "--report",
        action="store_true",
        help="Write annotated.repair-report.json beside the lesson files",
    )
    repair_parser.add_argument(
        "--force",
        action="store_true",
        help="Allow overwriting existing regenerated, backup, or report files",
    )

    legacy_repair_parser = subparsers.add_parser(
        "repair-annotated",
        help="Alias for regenerate-annotated",
    )
    _add_regenerate_args(legacy_repair_parser)

    inspect_parser = subparsers.add_parser("inspect", help="Inspect processed pipeline artifacts")
    inspect_parser.add_argument("--lesson", required=True, help="Lesson id under content/raw")
    inspect_parser.add_argument(
        "--stage",
        required=True,
        choices=["segmentation", "alignment", "regeneration", "report"],
        help="Stage artifact to print",
    )

    refresh_parser = subparsers.add_parser(
        "refresh",
        help="Build lesson(s), sync processed assets to the web app, and refresh manifest",
    )
    _add_lesson_selection_args(refresh_parser)
    refresh_parser.add_argument("--force", action="store_true", help="Rebuild even if output exists")
    refresh_parser.add_argument(
        "--aligner",
        choices=["auto", "external", "fastwhisper", "whisperx", "fallback"],
        default="auto",
        help="Alignment mode: auto prefers external alignment, then faster-whisper, then WhisperX, then fallback.",
    )
    refresh_parser.add_argument("--strict-alignment", action="store_true")
    refresh_parser.add_argument(
        "--external-alignment",
        type=Path,
        help="Path to an external alignment JSON file. Defaults to content/raw/<lesson>/alignment.external.json.",
    )

    args = parser.parse_args()

    try:
        if args.command == "build":
            _cmd_build(args)
        elif args.command == "validate":
            _cmd_validate(args)
        elif args.command == "clean":
            _cmd_clean(args)
        elif args.command == "init-lesson":
            _cmd_init_lesson(args)
        elif args.command in {"repair-annotated", "regenerate-annotated"}:
            _cmd_repair_annotated(args)
        elif args.command == "inspect":
            _cmd_inspect(args)
        elif args.command == "refresh":
            _cmd_refresh(args)
    except PipelineError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc


def _cmd_build(args: argparse.Namespace) -> None:
    from .builder import build_lesson, refresh_manifest

    raw_dirs = _resolve_raw_dirs(args)
    if not raw_dirs:
        print("No raw lessons found.")
        return

    built = 0
    skipped = 0
    for raw_dir in raw_dirs:
        lesson_id = raw_dir.name
        processed_dir = PROCESSED_ROOT / lesson_id
        if processed_dir.exists() and not args.force:
            print(f"Skipping {lesson_id}: processed output already exists (use --force to rebuild).")
            skipped += 1
            continue

        print(f"Building {lesson_id}...")
        output_dir = build_lesson(
            raw_dir,
            aligner=args.aligner,
            strict_alignment=args.strict_alignment,
            external_alignment_path=args.external_alignment,
        )
        report = _load_build_report(output_dir)
        alignment = report.get("alignment", {})
        for warning in report.get("warnings", []):
            print(f"  warning: {warning}")
        print(
            "  alignment: "
            f"requested={alignment.get('alignerRequested')} "
            f"used={alignment.get('alignerUsed')} "
            f"fallback={alignment.get('fallbackOccurred')}"
        )
        built += 1

    manifest_path = refresh_manifest()
    print(f"Built {built} lesson(s); skipped {skipped}.")
    print(f"Updated lesson manifest: {manifest_path}")


def _cmd_validate(args: argparse.Namespace) -> None:
    raw_dirs = _resolve_raw_dirs(args)
    if not raw_dirs:
        print("No raw lessons found.")
        return

    for raw_dir in raw_dirs:
        meta = validate_raw_lesson(raw_dir)
        raw_lesson_dir = RAW_ROOT / meta.id
        raw = load_raw_lesson(raw_lesson_dir)
        vocab_count = len(load_vocab_summary(raw.vocab_path))
        grammar_count = len(load_grammar_summary(raw.grammar_path))
        print(f"[ok] {meta.id}: {meta.title} ({meta.language}) from {meta.source}")
        print(f"  optional summaries: vocab={vocab_count}, grammar={grammar_count}")


def _cmd_clean(args: argparse.Namespace) -> None:
    from .builder import refresh_manifest

    if not args.yes:
        raise PipelineError("Refusing to clean processed outputs without --yes.")

    lesson_ids = _resolve_lesson_ids(args)
    if not lesson_ids:
        print("No processed lessons found.")
        return

    for lesson_id in lesson_ids:
        processed_dir = PROCESSED_ROOT / lesson_id
        if processed_dir.exists():
            shutil.rmtree(processed_dir)
            print(f"Removed {processed_dir}")

    manifest_path = refresh_manifest()
    print(f"Updated lesson manifest: {manifest_path}")


def _cmd_init_lesson(args: argparse.Namespace) -> None:
    from .init_lesson import init_lesson

    path = init_lesson(args.lesson, args.title)
    print(f"Created raw lesson template: {path}")
    print("Replace audio.wav with a real WAV before building.")


def _cmd_repair_annotated(args: argparse.Namespace) -> None:
    if args.output and args.write:
        raise PipelineError("Use either --output or --write, not both.")
    if args.backup and not args.write:
        raise PipelineError("--backup only applies with --write.")

    output_path, report_path, result = repair_lesson_annotated(
        args.lesson,
        write=args.write,
        backup=args.backup,
        output_path=args.output,
        write_report=args.report,
        force=args.force,
    )
    print(f"Wrote repaired annotated text: {output_path}")
    if report_path:
        print(f"Wrote repair report: {report_path}")
    print(
        "Repair summary: "
        f"paired={result.report['pairedSentences']} "
        f"unresolved={result.report['unresolvedSentences']} "
        f"inserted={result.report['insertedGlossCount']} "
        f"skipped={result.report['skippedGlossCount']}"
    )
    for warning in result.report["warnings"][:10]:
        print(f"  warning: {warning}")
    if len(result.report["warnings"]) > 10:
        print(f"  ... {len(result.report['warnings']) - 10} more warning(s)")


def _cmd_inspect(args: argparse.Namespace) -> None:
    mapping = {
        "segmentation": PROCESSED_ROOT / args.lesson / "sentence-segments.json",
        "alignment": PROCESSED_ROOT / args.lesson / "alignment.json",
        "regeneration": PROCESSED_ROOT / args.lesson / "annotated.regeneration-report.json",
        "report": PROCESSED_ROOT / args.lesson / "build-report.json",
    }
    path = mapping[args.stage]
    if not path.is_file():
        raise PipelineError(f"Inspect artifact does not exist for stage {args.stage!r}: {path}")
    print(path.read_text(encoding="utf-8"))


def _cmd_refresh(args: argparse.Namespace) -> None:
    from .sync_public import sync_processed_lessons_to_public

    _cmd_build(args)
    sync_processed_lessons_to_public()
    print("Synced processed lessons into apps/web/public/lessons.")


def _add_regenerate_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--lesson", required=True, help="Lesson id under content/raw")
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--backup", action="store_true")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--report", action="store_true")
    parser.add_argument("--force", action="store_true")


def _add_lesson_selection_args(parser: argparse.ArgumentParser) -> None:
    selection = parser.add_mutually_exclusive_group(required=True)
    selection.add_argument("--lesson", help="Lesson id under content/raw/<lesson-id>")
    selection.add_argument("--all", action="store_true", help="Target all lessons under content/raw")


def _resolve_raw_dirs(args: argparse.Namespace) -> list[Path]:
    if args.all:
        return list_raw_lesson_dirs(RAW_ROOT)
    lesson_dir = RAW_ROOT / args.lesson
    return [lesson_dir]


def _resolve_lesson_ids(args: argparse.Namespace) -> list[str]:
    if args.all:
        if not PROCESSED_ROOT.exists():
            return []
        return sorted(entry.name for entry in PROCESSED_ROOT.iterdir() if entry.is_dir())
    return [args.lesson]


def _load_build_report(output_dir: Path) -> dict[str, object]:
    import json

    report_path = output_dir / "build-report.json"
    if not report_path.is_file():
        return {}
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


if __name__ == "__main__":
    main()
