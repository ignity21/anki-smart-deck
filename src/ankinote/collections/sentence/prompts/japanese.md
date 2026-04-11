# Japanese Sentence Card Generation
Generate **one** JSON object for the given target sentence
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
  "target_sentence": "Japanese sentence exactly or very close to the input with <Kanji:reading>",
  "native_sentence": "user's native language translation conveying the same meaning.",
  "notes": ["short observations in user's native language. Cover nuance, register, common pitfalls, context, and any JLPT N3+ grammar points. All in native lanuage."],
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
| `target_sentence` | keep exactly as provided; minor spelling/kana fixes allowed |
| `native_sentence` | faithful, natural translation in user's native language |
| `notes` | 0–3 items; useful expressions extracted from the sentence |
| `phrases` | 0–3 entries; useful phrases or collocations from the sentence, with translations and example sentences |
