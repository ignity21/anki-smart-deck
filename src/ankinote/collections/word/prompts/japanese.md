# Japanese Vocabulary Card Generation

Return a **JSON array** — one object per part of speech. Output **only** valid JSON, no markdown, no comments.

```json
[
  {
    "word": "string (no furigana annotation)",
    "part_of_speech": "名詞|動詞|形容詞|形容動詞|副詞|助詞|接続詞|感動詞",
    "pronunciation": "hiragana, e.g. 'たべる', or null",
    "syllables": ["ta", "be", "ru"],
    "difficulty": "N5|N4|N3|N2|N1",
    "definitions": [
      {
        "target_lang": "Japanese definition (all kanji annotated, e.g. '食[た]べ物[もの]を口[くち]に入[い]れること')",
        "native_lang": "Chinese translation (2–6 characters, e.g. '进食' not '将食物放入口中的行为')",
        "is_visualizable": "true for concrete objects/actions; false for abstract concepts"
      }
    ],
    "synonyms": ["word1 (kanji annotated)", "word2 (kanji annotated)"],
    "examples": [
      {
        "sentence": "Natural Japanese sentence (all kanji annotated, e.g. '毎日[まいにち]朝[あさ]ご飯[はん]を食[た]べます').",
        "translation": "Chinese translation.",
        "highlights": ["collocation or pattern containing the word (kanji annotated)"]
      }
    ],
    "etymology": "Word origin (kanji annotated if applicable), or null",
    "collocations": ["collocation1 (kanji annotated)", "collocation2 (kanji annotated)"],
    "notes": ["Important usage notes (all Japanese text with kanji annotated)"]
  }
]
```

## Rules

| Field | Constraint |
|---|---|
| `definitions` | 1–4 per POS; never null |
| `synonyms` | 3–5 true synonyms; words/phrases that can substitute in context; all kanji annotated |
| `examples` | 2–4 items; each `highlights` item must contain the word or an inflected form; all kanji annotated |
| `etymology` | Include only if genuinely useful for learning; otherwise `null`; kanji annotated |
| `collocations` | 0–5 most frequent combinations; `[]` for function words; all kanji annotated |
| `notes` | 0–3 items; `[]` if nothing notable; all Japanese text with kanji annotated |

## Kanji Annotation Rules

- **All kanji must be annotated** with hiragana readings in square brackets immediately after the kanji
- Format: `漢字[かんじ]`
- For compound words with multiple kanji, annotate each morpheme separately: `食[た]べ物[もの]`
- Okurigana (trailing kana) should appear outside the brackets: `食[た]べる`
- Apply this to ALL fields containing Japanese text: word, definitions, examples, collocations, notes, etc.
