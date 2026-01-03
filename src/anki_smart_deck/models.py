from dataclasses import dataclass


@dataclass
class AIWord:
    word: str
    us_pron: str
    uk_pron: str
    frequency: str
    word_form: str
    def_en: list[str]
    def_cn: list[str]
    synonyms: list[str]
    notes: list[str]
    examples: dict[str, list[str]]
