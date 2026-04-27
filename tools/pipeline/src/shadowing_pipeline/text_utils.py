"""Token/text helpers shared by parsing, alignment, and exporters."""

from __future__ import annotations

from .models import Token

_NO_LEADING_SPACE = {
    ".",
    ",",
    "!",
    "?",
    ":",
    ";",
    ")",
    "]",
    "}",
    "%",
    "»",
    "”",
    "’",
}
_NO_TRAILING_SPACE = {"(", "[", "{", "«", "“", "‘"}


def is_word_char(char: str) -> bool:
    """Return True for characters that belong to lexical tokens."""
    return char.isalnum() or char in {"-", "'", "/", "_"}


def is_punctuation_token(text: str) -> bool:
    """Best-effort check for punctuation-only tokens."""
    return bool(text) and all(not is_word_char(char) for char in text)


def tokens_to_text(tokens: list[Token]) -> str:
    """Render tokens back to normalized readable text without glosses."""
    parts: list[str] = []
    for token in tokens:
        if not parts:
            parts.append(token.text)
            continue

        previous = parts[-1]
        if token.text in _NO_LEADING_SPACE or previous in _NO_TRAILING_SPACE:
            parts[-1] = f"{previous}{token.text}"
        else:
            parts.append(token.text)

    return " ".join(parts)
