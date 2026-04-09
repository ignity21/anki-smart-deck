# Japanese Vocabulary Card Generation
Return **only** valid JSON, no markdown, no comments.

## CRITICAL: Furigana Format (Strict 1-to-1 Mapping)
You MUST map the reading to **EACH KANJI INDIVIDUALLY**. Never group multiple kanji together. Break down compound words character by character.

**Format Rule:** `<Kanji:reading>`
- ✅ Correct: `<商:しょう><売:ばい><繁:はん><盛:じょう>` (Each kanji has its own block)
- ✅ Correct: `<縁:えん><起:ぎ><物:もの>`
- ❌ WRONG: `<商売繁盛:しょうばいはんじょう>` (Do NOT group kanji)
- ❌ WRONG: `<縁起物:えんぎもの>` (Do NOT group kanji)

For words with okurigana, leave the hiragana outside the blocks:
- ✅ Correct: `<食:た>べる`
- ✅ Correct: `<美:うつく>しい`

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
