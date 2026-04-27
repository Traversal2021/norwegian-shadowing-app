"""Language defaults for the Norwegian shadowing app."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LanguageConfig:
    human_label: str
    written_standard: str
    metadata_language: str
    asr_language: str
    spacy_model: str
    primary_raw_suffix: str
    accepted_raw_suffixes: tuple[str, ...]
    default_source: str
    default_tags: tuple[str, ...]
    default_level: str

    @property
    def original_filename(self) -> str:
        return f"original.{self.primary_raw_suffix}.txt"

    @property
    def annotated_filename(self) -> str:
        return f"annotated.{self.primary_raw_suffix}.txt"

    @property
    def canonical_annotated_filename(self) -> str:
        return f"annotated.canonical.{self.primary_raw_suffix}.txt"

    @property
    def regenerated_annotated_filename(self) -> str:
        return f"annotated.regenerated.{self.primary_raw_suffix}.txt"

    @property
    def backup_annotated_filename(self) -> str:
        return f"annotated.backup.{self.primary_raw_suffix}.txt"

    @property
    def clean_text_filename(self) -> str:
        return f"clean.{self.primary_raw_suffix}.txt"


DEFAULT_LANGUAGE = LanguageConfig(
    human_label="Norwegian",
    written_standard="Bokmål",
    metadata_language="nb",
    asr_language="no",
    spacy_model="nb_core_news_sm",
    primary_raw_suffix="no",
    accepted_raw_suffixes=("no", "nb", "da"),
    default_source="Norwegian learning material",
    default_tags=("norwegian", "shadowing"),
    default_level="unknown",
)

