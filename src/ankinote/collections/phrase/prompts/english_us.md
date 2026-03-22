# English (US) Phrase / Idiom Card Generation

## Output Format

Return a single JSON object with this exact structure:

```json
{
  "phrase": "string",
  "difficulty": "A1|A2|B1|B2|C1|C2",
  "definitions": [
    {
      "target_lang": "English explanation of the phrase",
      "native_lang": "Translation in user's native language"
    }
  ],
  "examples": [
    {
      "sentence": "Natural English sentence showing the phrase in context.",
      "translation": "Native language translation.",
      "highlight": "The exact surface form of the phrase as it appears in the sentence"
    }
  ],
  "notes": ["Useful usage notes, register, common mistakes"]
}
```

- Never return `null` for array fields (`definitions`, `examples`, `notes`).
- `notes` can be an empty array if you have nothing important to say.
- Output **only** valid JSON (no markdown, no comments, no extra keys).

## Key Rules

**Phrase Types:**
- The `"phrase"` field can be:
  - multi-word expressions (`"take something for granted"`)
  - idioms (`"break the ice"`)
  - short sentences or patterns (`"Nice to meet you."`, `"Would you mind if I...?"`)

**Difficulty:**
- Use CEFR levels (`A1`–`C2`) to approximate how advanced the phrase is.

**Definitions (1–3):**
- `target_lang`: Clear English explanation of the phrase's meaning in typical use.
- `native_lang`: Concise translation in the user's native language.

**Examples (2–4):**
- Natural, contemporary English sentences.
- Each `sentence` MUST contain the phrase (or a very close surface form).
- `highlight`:
  - MUST be exactly the text span of the phrase inside `sentence`.
  - Use the same casing and inflection as it appears in `sentence`.
  - If the phrase appears multiple times, highlight the most important occurrence.

**Notes (0–5):**
- Register: formal / informal / slang / written / spoken.
- Typical contexts: business, everyday conversation, academic, etc.
- Common mistakes, grammatical constraints, or collocational patterns.

## Output Requirements

- Return exactly **one** JSON object (not an array).
- Follow the schema of `PhraseModel` strictly.
- Do not include pronunciation, IPA, images, or any extra metadata.
