# Japanese Phrase / Idiom Card Generation

Generate **one** JSON object for the given phrase. Output **only** valid JSON — no markdown, no comments, no extra keys.

```json
{
  "phrase": "string (no furigana annotation e.g. '一石二鳥')",
  "difficulty": "N5|N4|N3|N2|N1",
  "definitions": [
    {
      "target_lang": "Japanese explanation (all kanji annotated)",
      "native_lang": "Chinese translation"
    }
  ],
  "examples": [
    {
      "sentence": "Natural Japanese sentence containing the phrase (all kanji annotated).",
      "translation": "Chinese translation.",
      "highlight": "Exact surface form of the phrase as it appears in sentence (kanji annotated)"
    }
  ],
  "notes": ["Register, common mistakes, grammatical constraints (all Japanese text with kanji annotated) — omit if nothing important"],
  "associations": ["Related or contrastive phrases (all kanji annotated), one per item"]
}
```

## Rules

| Field | Constraint |
|---|---|
| `definitions` | 1–3 items; never null or empty; all Japanese text with kanji annotated |
| `examples` | 2–4 items; `highlight` must match the exact casing/inflection in `sentence`; all kanji annotated |
| `notes` | 0–3 items; use `[]` if nothing noteworthy; all Japanese text with kanji annotated |
| `associations` | 0–5 items; near-synonyms, contrastive pairs, or common alternatives; all kanji annotated |

## Kanji Annotation Rules

- **All kanji must be annotated** with hiragana readings in square brackets immediately after the kanji
- Format: `漢字[かんじ]`
- For compound words with multiple kanji, annotate each morpheme separately: `一石[いっせき]二鳥[にちょう]`
- For phrases with okurigana: `立[た]ち上[あ]がる`
- Apply this to ALL fields containing Japanese text: phrase, definitions, examples, highlights, notes, associations
