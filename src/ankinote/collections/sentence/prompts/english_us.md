# US English Sentence Anki Card Generation
Return **only** valid JSON object, no markdown, no comments. The *input* you receive will be the **native language sentence**.

```json
{
  "target_sentence": "Sentence in the target language (a faithful natural translation of the input).",
  "native_sentence": "The input sentence in the user's native language (mirror back exactly as provided).",
  "notes": ["Optional important usage notes about the target sentence."],
  "phrases": [{
    "phrase": "useful target language phrase or collocation",
    "translation": "the phrase in user's native language",
    "example": "a simple example sentence in the target language"
  }]
}
```

## Field Rules
- `target_sentence` — produce a faithful, natural translation of the input native sentence into the target language. Minor spelling fixes are allowed, but do not "correct" colloquial or non-standard structures — preserve them and note them in `notes` instead.
- `native_sentence` — mirror the input sentence back exactly as provided.
- `notes` — short, worthy-of-attention observations in the user's native language only (can be empty `[]`). Cover nuance, register, common pitfalls, context, and any B1+ grammar points present in the target sentence.
- `phrases` — useful expressions or collocations extracted from the target sentence; each phrase is in the target language, with a translation and a simple example sentence in the target language (can be empty `[]`).

## General Guidelines
- Prefer contemporary, common usage; avoid archaic or overly formal expressions.
- Never return `null` for any field.
- Output **only** valid JSON — no markdown, no comments, no extra keys or text.
