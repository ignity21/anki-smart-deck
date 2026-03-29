# English (US) Sentence Card Generation

Generate one JSON object describing a bilingual sentence pair.

The *input* you receive will be the **target language sentence**.
You must:
- keep `"target_sentence"` exactly as provided (or a very natural minor tweak),
- generate a faithful `"native_sentence"` translation,
- and optionally add brief, important `"notes"`.

```json
{
  "target_sentence": "Sentence in the target language (exactly or very close to the input).",
  "native_sentence": "Sentence in the user's native language conveying the same meaning.",
  "notes": [
    "Optional important usage or grammar notes about the target sentence."
  ]
}
```

- Never return `null` for array fields (`notes`).
- `notes` can be an empty array if there is nothing noteworthy.
- Output **only** valid JSON (no markdown, no comments, no extra keys or text).

## Key Rules

- `target_sentence`: the sentence in the target language, based on the input.
- `native_sentence`: clear, natural sentence in the user's native language, faithful to the meaning.
- Prefer contemporary, common usage; avoid archaic or overly formal expressions.
- If there is a strong grammatical pattern, collocation, or pitfall, add a short note.
- In `notes`, you may also list useful phrases or idioms that appear in the sentence.
  - Each phrase should be a separate bullet point string.
  - Each bullet should contain the phrase plus one **very simple** example sentence that uses that phrase.

## Output Requirements

- Return exactly one JSON object (not an array).
- Follow the JSON schema above strictly.
- Do not include pronunciation, IPA, images, or any other fields.
