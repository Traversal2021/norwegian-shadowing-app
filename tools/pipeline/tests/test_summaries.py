"""Tests for manual vocab/grammar sidecar parsing."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from shadowing_pipeline.errors import ValidationError
from shadowing_pipeline.summaries import load_grammar_summary, load_vocab_summary


def test_load_vocab_json(tmp_path: Path) -> None:
    path = tmp_path / "vocab.json"
    path.write_text(
        json.dumps([{"word": "ciffer", "definition": "digit", "example": "Et ciffer."}]),
        encoding="utf-8",
    )

    items = load_vocab_summary(path)

    assert items[0].word == "ciffer"
    assert items[0].definition == "digit"
    assert items[0].example == "Et ciffer."


def test_load_grammar_markdown(tmp_path: Path) -> None:
    path = tmp_path / "grammar.md"
    path.write_text(
        "## Modal verb\nExplanation: Skal plus infinitive.\nExample: Du skal lytte.\n",
        encoding="utf-8",
    )

    items = load_grammar_summary(path)

    assert items[0].title == "Modal verb"
    assert items[0].explanation == "Skal plus infinitive."
    assert items[0].example == "Du skal lytte."


def test_summary_json_requires_array(tmp_path: Path) -> None:
    path = tmp_path / "vocab.json"
    path.write_text("{}", encoding="utf-8")

    with pytest.raises(ValidationError, match="must be an array"):
        load_vocab_summary(path)
