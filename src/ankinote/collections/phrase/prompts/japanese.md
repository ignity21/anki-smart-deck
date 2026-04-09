# Japanese Phrase / Idiom Card Generation

Generate **one** JSON object for the given phrase. Output **only** valid JSON — no markdown, no comments, no extra keys.

```json
{
  "phrase": "string (no furigana annotation e.g. '一石二鳥')",
  "difficulty": "N5|N4|N3|N2|N1",
  "definitions": [
    {
      "target_lang": "Japanese explanation (per-character furigana)",
      "native_lang": "Translation in user's native language"
    }
  ],
  "examples": [
    {
      "sentence": "Natural Japanese sentence containing the phrase (per-character furigana).",
      "translation": "Native language translation.",
      "highlight": "Exact surface form of the phrase as it appears in sentence (per-character furigana)"
    }
  ],
  "notes": ["Register, common mistakes, grammatical constraints (all Japanese text with per-character furigana) — omit if nothing important"],
  "associations": ["Related or contrastive phrases (per-character furigana), one per item"]
}
```

## Rules

| Field | Constraint |
|---|---|
| `definitions` | 1–3 items; never null or empty; all Japanese text with per-character furigana |
| `examples` | 2–4 items; `highlight` must match the exact casing/inflection in `sentence`; per-character furigana |
| `notes` | 0–3 items; use `[]` if nothing noteworthy; all Japanese text with per-character furigana |
| `associations` | 0–5 items; near-synonyms, contrastive pairs, or common alternatives; per-character furigana |

## Per-Character Furigana Annotation Rules

- **Each kanji must be annotated individually** with its reading in square brackets immediately after it
- Format: `漢[かん]字[じ]` (NOT `漢字[かんじ]`)
- For compound words, annotate each kanji separately: `一[いっ]石[せき]二[に]鳥[ちょう]`, `立[た]ち上[あ]がる`
- Okurigana (trailing kana) should appear outside the brackets: `食[た]べる`
- Apply this to ALL fields containing Japanese text: definitions, examples, highlights, notes, associations
- The `phrase` field should NOT have furigana annotation
