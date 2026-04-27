"""Tests for the annotation parser."""

from shadowing_pipeline.parse_annotations import parse_annotated_line, strip_annotations


def test_parse_no_gloss() -> None:
    tokens = parse_annotated_line("Alle i Norge har et nummer.")
    texts = [t.text for t in tokens]
    assert "Alle" in texts
    assert all(t.gloss is None for t in tokens)


def test_parse_with_gloss() -> None:
    tokens = parse_annotated_line("De første(first) seks siffer (digits).")
    by_text = {t.text: t.gloss for t in tokens}
    assert by_text.get("første") == "first"
    assert by_text.get("siffer") == "digits"
    assert by_text.get("De") is None


def test_strip_annotations() -> None:
    result = strip_annotations("De første(first) seks siffer(digits).")
    assert "(" not in result
    assert "first" not in result
    assert "første" in result
    assert "siffer" in result


def test_strip_annotations_preserves_norwegian_quote_spacing() -> None:
    sentence = "Hei, og velkommen til ”Norsk i ørene”."
    assert strip_annotations(sentence) == sentence


def test_strip_annotations_preserves_visible_sentence_with_glosses() -> None:
    original = "Hei, og velkommen til ”Norsk i ørene”, hvor vi lærer norsk."
    annotated = "Hei(greeting), og velkommen til ”Norsk(Norwegian) i ørene”, hvor vi lærer norsk."
    assert strip_annotations(annotated) == original


def test_preserves_punctuation_as_visible_tokens() -> None:
    tokens = parse_annotated_line("Består (consists) av to siffer (digits), ikke tre.")
    assert [(token.text, token.gloss) for token in tokens] == [
        ("Består", "consists"),
        ("av", None),
        ("to", None),
        ("siffer", "digits"),
        (",", None),
        ("ikke", None),
        ("tre", None),
        (".", None),
    ]
