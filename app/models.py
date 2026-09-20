"""Word entry — mirrors one row of the CSV's `Your words` section."""

from dataclasses import dataclass


@dataclass
class WordEntry:
    word: str = ""
    language: str = ""
    translation: str = ""
    contexts: str = ""
    last_modified: str = ""
    alternatives: str = ""
    spaced_repetition_next_date: str | None = ""
    spaced_repetition_interval: str | None = ""
    spaced_repetition_easiness_factor: str | None = ""
    spaced_repetition_recall_attempts: str | None = ""
    spaced_repetition_last_recall_ease: str | None = ""
    spaced_repetition_previous_interval: str | None = ""
    spaced_repetition_previous_interval_date: str | None = ""
    deleted_date: str | None = ""
    favorite: str | None = ""
    relevancy: str | None = ""
