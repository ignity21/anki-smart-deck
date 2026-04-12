# US English Vocabulary Card Generation

Return **only** valid JSON, no markdown, no comments.

```json
[
  {
    "word": "string",
    "part_of_speech": "n.|vt.|vi.|adj.|adv.|prep.|conj.|interj.",
    "pronunciation": "/IPA/ or null; use US English",
    "syllables": ["syl", "la", "bles"],
    "difficulty": "A1|A2|B1|B2|C1|C2",
    "definitions": [
      {
        "target_lang": "English definition",
        "native_lang": "Simple translation in native language",
        "is_visualizable": true
      }
    ],
    "synonyms": ["word1", "word2"],
    "examples": [
      {
        "sentence": "English sentence using word or inflected form.",
        "translation": "Native language translation.",
        "highlights": ["word/collocation containing the word"]
      }
    ],
    "etymology": "Use user's native lanuage; Content: Word origin or null",
    "collocations": ["phrase1", "phrase2"],
    "notes": ["Use user's native lanuage; Content: Irregular forms, UK/US differences, common mistakes;"]
  }
]
```

## Rules
- `level ≤ difficulty` means "Calibrate examples and notes to the word's CEFR level: use only vocabulary and grammar ≤ that difficulty"

| Field | Constraint |
|---|---|
| `definitions` | 1–3 per `part_of_speech`; target language must be `level ≤ difficulty` |
| `synonyms` | 0-3 true synonyms(word or phrase); `level ≤ difficulty` |
| `examples` | 1–4 items; sentence must be `level ≤ difficulty`; highlights must contain word or inflected form |
| `etymology` | Include if useful for memorizing; else `null` |
| `collocations` | 0–5 most frequent combinations |
| `notes` | 0–3 items; `[]` if nothing notable |
