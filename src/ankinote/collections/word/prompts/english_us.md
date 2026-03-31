# English (US) Vocabulary Card Generation

Return a **JSON array** — one object per part of speech. Output **only** valid JSON, no markdown, no comments.

```json
[
  {
    "word": "string",
    "part_of_speech": "n.|vt.|vi.|adj.|adv.|prep.|conj.|interj.",
    "pronunciation": "/IPA/ or null",
    "syllables": ["syl", "la", "bles"],
    "difficulty": "A1|A2|B1|B2|C1|C2",
    "definitions": [
      {
        "target_lang": "English definition",
        "native_lang": "Translation (Chinese: 2–6 chars, e.g. '书籍' not '一本印刷或电子的出版物')",
        "is_visualizable": "true for concrete objects/actions; false for abstract concepts"
      }
    ],
    "synonyms": ["word1", "word2"],
    "examples": [
      {
        "sentence": "Natural English sentence.",
        "translation": "Native language translation.",
        "highlights": ["collocation or idiom containing the word"]
      }
    ],
    "etymology": "Word origin, or null",
    "collocations": ["make a decision", "strong coffee"],
    "notes": ["Irregular forms, UK/US differences, common mistakes"]
  }
]
```

## Rules

| Field | Constraint |
|---|---|
| `definitions` | 1–4 per POS; never null |
| `synonyms` | 3–5 true synonyms; words/phrases that can substitute in context |
| `examples` | 2–4 items; each `highlights` item must contain the word or an inflected form |
| `etymology` | Include only if genuinely useful for learning; otherwise `null` |
| `collocations` | 0–5 most frequent combinations; `[]` for function words |
| `notes` | 0–3 items; `[]` if nothing notable |
