"""Tests for conservative annotated text regeneration."""

from shadowing_pipeline.annotated_repair import (
    normalize_for_matching,
    repair_annotated_text,
)


def test_repairs_simple_single_word_gloss() -> None:
    result = repair_annotated_text(
        lesson_id="lesson",
        original_text="Nummeret består av ti siffer.",
        annotated_text="Nummeret består(consists) av ti siffer(digits).",
    )

    assert result.text == "Nummeret består(consists) av ti siffer(digits)."
    assert result.report["insertedGlossCount"] == 2


def test_repairs_phrase_gloss_when_phrase_is_explicit_segment() -> None:
    result = repair_annotated_text(
        lesson_id="lesson",
        original_text="På grunn av regn blir vi inne.",
        annotated_text="På grunn av(because of) regn blir vi inne.",
    )

    assert result.text == "På grunn av(because of) regn blir vi inne."
    assert result.report["skippedGlossCount"] == 0


def test_pairs_through_punctuation_and_quote_spacing_drift() -> None:
    result = repair_annotated_text(
        lesson_id="lesson",
        original_text='Hun sa: "Hei, Mads!"',
        annotated_text='Hun sa : “Hei(greeting) , Mads!”',
    )

    assert result.text == 'Hun sa: "Hei(greeting), Mads!"'
    assert result.report["pairedSentences"] == 1


def test_repeated_word_uses_occurrence_order() -> None:
    result = repair_annotated_text(
        lesson_id="lesson",
        original_text="Far får far til å smile.",
        annotated_text="Far(dad) får far(father) til å smile.",
    )

    assert result.text == "Far(dad) får far(father) til å smile."
    assert result.report["insertedGlossCount"] == 2


def test_unresolved_sentence_warns_and_keeps_original_text() -> None:
    result = repair_annotated_text(
        lesson_id="lesson",
        original_text="Det her er korrekt.",
        annotated_text="Noget andet(wrong) er korrekt.",
    )

    assert result.text == "Det her er korrekt."
    assert result.report["pairedSentences"] == 0
    assert result.report["unresolvedSentences"] == 1
    assert result.report["warnings"]


def test_original_backbone_is_unchanged_after_stripping_glosses() -> None:
    original = 'Først sier han: "Takk!"\nSå går han hjem.'
    annotated = 'Først(first) sier han : “Takk(thanks) !” Så går(goes) han hjem.'

    result = repair_annotated_text(
        lesson_id="lesson",
        original_text=original,
        annotated_text=annotated,
    )

    without_insertions = (
        result.text.replace("(first)", "").replace("(thanks)", "").replace("(goes)", "")
    )
    assert without_insertions == original
    assert normalize_for_matching(without_insertions) == normalize_for_matching(original)
