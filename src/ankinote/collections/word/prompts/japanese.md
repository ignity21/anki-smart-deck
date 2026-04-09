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
        "target_lang": "Japanese definition (per-character furigana, e.g. '食[た]べ物[もの]を口[くち]に入[い]れること')",
        "native_lang": "Chinese translation (2–6 characters, e.g. '进食' not '将食物放入口中的行为')",
        "is_visualizable": "true for concrete objects/actions; false for abstract concepts"
      }
    ],
    "synonyms": ["word1 (per-character furigana)", "word2 (per-character furigana)"],
    "examples": [
      {
        "sentence": "Natural Japanese sentence (per-character furigana, e.g. '毎[まい]日[にち]朝[あさ]ご飯[はん]を食[た]べます').",
        "translation": "Chinese translation.",
        "highlights": ["collocation or pattern containing the word (per-character furigana)"]
      }
    ],
    "etymology": "Word origin (per-character furigana if applicable), or null",
    "collocations": ["collocation1 (per-character furigana)", "collocation2 (per-character furigana)"],
    "notes": ["Important usage notes (all Japanese text with per-character furigana)"]
  }
]
```

## Rules

| Field | Constraint |
|---|---|
| `definitions` | 1–4 per POS; never null |
| `synonyms` | 3–5 true synonyms; words/phrases that can substitute in context; per-character furigana |
| `examples` | 2–4 items; each `highlights` item must contain the word or an inflected form; per-character furigana |
| `etymology` | Include only if genuinely useful for learning; otherwise `null`; per-character furigana |
| `collocations` | 0–5 most frequent combinations; `[]` for function words; per-character furigana |
| `notes` | 0–3 items; `[]` if nothing notable; all Japanese text with per-character furigana |

## Per-Character Furigana Annotation Rules

- **Each kanji must be annotated individually** with its reading in square brackets immediately after it
- Format: `漢[かん]字[じ]` (NOT `漢字[かんじ]`)
- For compound words, annotate each kanji separately: `食[しょく]事[じ]`, `学[がっ]校[こう]`, `天[てん]気[き]`
- Okurigana (trailing kana) should appear outside the brackets: `食[た]べる`, `美[うつく]しい`
- Single kanji words: `本[ほん]`, `人[ひと]`
- Mixed kanji-kana words: `食[た]べ物[もの]` (each kanji individually annotated)
- Apply this to ALL fields containing Japanese text: definitions, examples, collocations, notes, synonyms, etymology
- The `word` field should NOT have furigana annotation
