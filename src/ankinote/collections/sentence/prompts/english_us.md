# US English Sentence Card Generation
Return **only** valid JSON object, no markdown, no comments. The *input* you receive will be the **target language sentence**.

```json
{
  "target_sentence": "Sentence in the target language (exactly or very close to the input).",
  "native_sentence": "Sentence in the user's native language conveying the same meaning.",
  "notes": ["Optional important usage notes about the target sentence."],
  "phrases": {
    "useful target-language phrase or collocation": "simple example sentence in the target language"
  }
}
```

## Field Rules
- `target_sentence` — keep exactly as provided; minor spelling fixes are allowed, but do not "correct" colloquial or non-standard structures (e.g. declarative questions like *"You attended high school at Winston Farmer?"*) — preserve them and note them in `notes` instead.
- `native_sentence` — faithful, natural translation in the user's native language.
- `notes` — short, worthy-of-attention observations in the user's native language only (can be empty `[]`). Cover nuance, register, common pitfalls, context, and any B1+ grammar points present in the sentence. If a non-standard structure is grammatically incorrect but very common in spoken English, acknowledge both — note that it is non-standard, explain the correct form, and explicitly state that it is non-standard but very common in spoken English.
- `phrases` — useful expressions or collocations extracted from the sentence; key = target-language phrase, value = one simple target-language example sentence (can be empty `{}`).

## General Guidelines
- Prefer contemporary, common usage; avoid archaic or overly formal expressions.
- Never return `null` for any field.
- Output **only** valid JSON — no markdown, no comments, no extra keys or text.
