# Japanese Phrase / Idiom Card Generation
Generate **one** JSON object for the given phrase. Output **only** valid JSON — no markdown, no comments.

## Furigana Format
Add hiragana readings to each kanji individually using the format `<Kanji:reading>`.

e.g.
-- ✅ Correct: `<商:しょう><売:ばい><繁:はん><盛:じょう>` (Each kanji has its own block)
-- ❌ WRONG: `<商売繁盛:しょうばいはんじょう>` (Do NOT group kanji)

-- ✅ Correct: `<縁:えん><起:ぎ><物:もの>`
-- ❌ WRONG: `<縁起物:えんぎもの>` (Do NOT group kanji)

## Json Output
```json
{
  "phrase": "string (no furigana annotation e.g. '一石二鳥')",
  "difficulty": "N5|N4|N3|N2|N1",
  "definitions": [
    {
      "target_lang": "Japanese explanation with <Kanji:reading>",
      "native_lang": "Translation in user's native language"
    }
  ],
  "examples": [
    {
      "sentence": "Natural Japanese sentence containing the phrase with <Kanji:reading>.",
      "translation": "Native language translation.",
      "highlight": "Exact surface form of the phrase as it appears in sentence with <Kanji:reading>"
    }
  ],
  "notes": ["Register, common mistakes, grammatical constraints, etc. All in user's native language"],
  "associations": ["Related or contrastive phrases with <Kanji:reading>"]
}
```

## Field Rules

| Field | Constraint |
|---|---|
| `definitions` | 1–3 items; never null or empty |
| `examples` | 1–4 items; `highlight` must match the exact casing/inflection in `sentence` |
| `notes` | 0–3 items; use `[]` if nothing noteworthy |
| `associations` | 0–5 items; near-synonyms, contrastive pairs, or common alternatives |
