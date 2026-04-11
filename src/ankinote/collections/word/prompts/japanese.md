# Japanese Vocabulary Card Generation
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
[
  {
    "word": "string (no furigana)",
    "part_of_speech": "名詞|動詞|形容詞|形容動詞|副詞|助詞|接続詞|感動詞",
    "pronunciation": "hiragana or null",
    "syllables": ["ta", "be", "ru"],
    "difficulty": "N5|N4|N3|N2|N1",
    "definitions": [
      {
        "target_lang": "Japanese definition using <Kanji:reading> format strictly.",
        "native_lang": "Brief translation in user's native language",
        "is_visualizable": true|false
      }
    ],
    "synonyms": ["<word:reading>1", "<word:reading>2"],
    "examples": [
      {
        "sentence": "Japanese sentence with <Kanji:reading> applied to EVERY kanji.",
        "translation": "Translation.",
        "highlights": ["pattern with <Kanji:reading>"]
      }
    ],
    "etymology": "Memory aid in native language, or null",
    "collocations": ["collocation1 with <Kanji:reading>"],
    "notes": ["usage notes in native language"]
  }
]
```

## Field Rules

| Field | Constraint |
|---|---|
| `definitions` | 1–3 per `part_of_speech`; never null |
| `synonyms` | 0–3 true synonyms; words/phrases that can substitute in context |
| `examples` | 1–4 items; each `highlights` item must contain the word or an inflected form |
| `etymology` | Include only if genuinely useful for learning; otherwise `null` |
| `collocations` | 0–5 most frequent combinations; `[]` for function words |
| `notes` | 0–3 items; `[]` if nothing notable |
