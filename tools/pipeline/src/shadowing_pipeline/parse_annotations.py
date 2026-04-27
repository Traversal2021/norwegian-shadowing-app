"""
Parser for Norwegian inline gloss syntax.

Supported forms:

    består (consists)
    cifre(digits)

Gloss text is attached to the immediately preceding lexical token and is removed
from the clean plain-text output.
"""

from __future__ import annotations

from .models import Token
from .text_utils import is_word_char


def parse_annotated_line(line: str) -> list[Token]:
    """Parse one annotated sentence into token-level Norwegian text plus glosses."""
    tokens: list[Token] = []
    index = 0
    length = len(line)

    while index < length:
        char = line[index]

        if char.isspace():
            index += 1
            continue

        if is_word_char(char):
            start = index
            index += 1
            while index < length and is_word_char(line[index]):
                index += 1

            token = Token(text=line[start:index])
            index = _attach_optional_gloss(line, index, tokens, token)
            continue

        tokens.append(Token(text=char))
        index += 1

    return tokens


def strip_annotations(annotated_text: str) -> str:
    """Remove inline English glosses while preserving visible Norwegian text."""
    clean_lines = [_strip_annotations_from_line(line) for line in annotated_text.splitlines()]
    return "\n".join(line for line in clean_lines if line)


def _strip_annotations_from_line(line: str) -> str:
    """Remove gloss markup without reconstructing or respacing visible text."""
    output: list[str] = []
    index = 0
    length = len(line)

    while index < length:
        char = line[index]
        if char != "(":
            output.append(char)
            index += 1
            continue

        closing = line.find(")", index + 1)
        if closing == -1 or not _looks_like_gloss_start(line, index):
            output.append(char)
            index += 1
            continue

        while output and output[-1].isspace():
            output.pop()
        index = closing + 1

    return "".join(output).strip()


def _looks_like_gloss_start(line: str, open_paren_index: int) -> bool:
    probe = open_paren_index - 1
    while probe >= 0 and line[probe].isspace():
        probe -= 1
    return probe >= 0 and is_word_char(line[probe])


def _attach_optional_gloss(
    line: str,
    index: int,
    tokens: list[Token],
    token: Token,
) -> int:
    probe = index
    while probe < len(line) and line[probe].isspace():
        probe += 1

    if probe < len(line) and line[probe] == "(":
        closing = line.find(")", probe + 1)
        if closing == -1:
            # Keep malformed gloss text visible rather than silently swallowing it.
            tokens.append(token)
            return index

        gloss = line[probe + 1 : closing].strip()
        tokens.append(Token(text=token.text, gloss=gloss or None))
        return closing + 1

    tokens.append(token)
    return index
