# Japanese Sentence Anki Card Generation
Generate **one** JSON object for the given native sentence.
Return **only** valid JSON, no markdown, no comments.

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
  "target_sentence": "Japanese sentence (faithful translation of the input) with <Kanji:reading>",
  "native_sentence": "The input sentence in the user's native language (mirror back exactly as provided).",
  "notes": ["short observations in user's native language. Cover nuance, register, common pitfalls, context, and any JLPT N3+ grammar points. All in native language."],
  "phrases": [{
    "phrase": "useful Japanese phrase or collocation with <Kanji:reading>",
    "translation": "the phrase in user's native language",
    "example": "a simple example sentence in Japanese using the phrase, with <Kanji:reading>"
  }]
}
```
## Field Rules
| Field | Constraint |
|---|---|
| `target_sentence` | produce a faithful, natural Japanese translation of the input native sentence. Apply furigana annotations to all kanji. |
| `native_sentence` | mirror the input sentence back exactly as provided. |
| `notes` | 0–3 items; useful observations about the target sentence in user's native language. |
| `phrases` | 0–3 entries; useful Japanese phrases or collocations from the target sentence, with translations and example sentences. |
