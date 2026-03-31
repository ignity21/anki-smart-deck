# English (US) Phrase / Idiom Card Generation

Generate **one** JSON object for the given phrase. Output **only** valid JSON — no markdown, no comments, no extra keys.

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
      "sentence": "Natural sentence containing the phrase.",
      "translation": "Native language translation.",
      "highlight": "Exact surface form of the phrase as it appears in sentence"
    }
  ],
  "notes": ["Register, common mistakes, grammatical constraints — omit if nothing important"],
  "associations": ["Related or contrastive phrases, one per item"]
}
```

## Rules

| Field | Constraint |
|---|---|
| `definitions` | 1–3 items; never null or empty |
| `examples` | 2–4 items; `highlight` must match the exact casing/inflection in `sentence` |
| `notes` | 0–3 items; use `[]` if nothing noteworthy |
| `associations` | 0–5 items; near-synonyms, contrastive pairs, or common alternatives |
