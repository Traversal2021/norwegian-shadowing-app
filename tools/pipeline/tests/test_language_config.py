"""Tests for Norwegian language defaults."""

from __future__ import annotations

from pathlib import Path

from shadowing_pipeline.language_config import DEFAULT_LANGUAGE


def test_norwegian_language_defaults() -> None:
    assert DEFAULT_LANGUAGE.human_label == "Norwegian"
    assert DEFAULT_LANGUAGE.written_standard == "Bokmål"
    assert DEFAULT_LANGUAGE.metadata_language == "nb"
    assert DEFAULT_LANGUAGE.asr_language == "no"
    assert DEFAULT_LANGUAGE.spacy_model == "nb_core_news_sm"
    assert DEFAULT_LANGUAGE.original_filename == "original.no.txt"
    assert DEFAULT_LANGUAGE.annotated_filename == "annotated.no.txt"


def test_core_norwegian_path_does_not_hardcode_legacy_defaults() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    scanned_roots = [
        repo_root / "tools" / "alignment",
        repo_root / "scripts",
        repo_root / "tools" / "pipeline" / "src" / "shadowing_pipeline",
    ]
    allowed = {repo_root / "tools" / "pipeline" / "src" / "shadowing_pipeline" / "language_config.py"}
    forbidden = [
        "Dan" + "ish",
        "Da" + "nsk",
        chr(100) + "a_core_news_sm",
        '"' + chr(100) + 'a"',
        "'" + chr(100) + "a'",
    ]

    hits: list[str] = []
    for root in scanned_roots:
        for path in root.rglob("*"):
            if path in allowed or not path.is_file() or path.suffix not in {".py", ".sh"}:
                continue
            text = path.read_text(encoding="utf-8")
            for needle in forbidden:
                if needle in text:
                    hits.append(f"{path.relative_to(repo_root)} contains {needle}")

    assert hits == []
