"""Tests for staged sentence segmentation."""

from shadowing_pipeline.segmentation.spacy_sentences import segment_sentences


def test_segment_sentences_preserves_original_text_spans() -> None:
    text = "Hei, og velkommen til ”Norsk i ørene”.\nHer er neste setning."

    result = segment_sentences(text)

    assert [segment.text for segment in result.segments] == [
        "Hei, og velkommen til ”Norsk i ørene”.",
        "Her er neste setning.",
    ]
    for segment in result.segments:
        assert text[segment.start_char : segment.end_char] == segment.text
        assert segment.token_count > 0
