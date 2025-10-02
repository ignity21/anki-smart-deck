from dataclasses import dataclass


@dataclass
class Pronunciation:
    us: str
    uk: str


@dataclass
class AIWord:
    word: str
    word_form: str
    definition_en: str
    definition_zh: str
    synonyms: list[str]
    pronunciation: Pronunciation
