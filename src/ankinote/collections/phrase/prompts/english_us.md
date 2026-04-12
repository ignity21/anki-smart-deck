# US English Phrase / Idiom Card Generation

Return **only** valid JSON, no markdown, no comments.

```json
{
  "phrase": "string",
  "difficulty": "A1|A2|B1|B2|C1|C2",
  "definitions": [
    {
      "target_lang": "English explanation",
      "native_lang": "Translation in user's native language"
    }
  ],
  "examples": [
    {
      "sentence": "Natural english sentence containing the phrase.",
      "translation": "Native language translation.",
      "highlight": "Exact surface form of the phrase as it appears in sentence"
    }
  ],
  "notes": ["Use user's native lanuage; Register, common mistakes, grammatical constraints — omit if nothing important"],
  "associations": ["Related or contrastive phrases, one per item"]
}
```

## Rules
- `level ≤ difficulty` means "Calibrate examples and notes to the word's CEFR level: use only vocabulary and grammar ≤ that difficulty"

| Field | Constraint |
|---|---|
| `definitions` | 1–3 items; target language must be `level ≤ difficulty` |
| `examples` | 2–4 items; sentence must be `level ≤ difficulty`; `highlight` must match the exact casing/inflection in `sentence` |
| `associations` | 0–5 items; near-synonyms, contrastive pairs, or common alternatives |
| `notes` | 0–3 items; use `[]` if nothing noteworthy |
