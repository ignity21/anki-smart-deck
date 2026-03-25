# English (US) Phrase / Idiom Card Generation

Generate one JSON object describing the phrase.

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
  "notes": ["Useful usage notes, register, common mistakes"],
  "associations": ["Similar or contrastive phrases, e.g. 'pay attention to'"]
}
```

- Never return `null` for array fields (`definitions`, `examples`, `notes`, `associations`).
- `notes` can be an empty array if you have nothing important to say.
- `associations` can be empty if there are no strong related phrases.
- Output **only** valid JSON (no markdown, no comments, no extra keys or text).

## Key Rules

- `"phrase"` can be a multi‑word expression, idiom, or short sentence/pattern.
- `"difficulty"` uses CEFR levels `A1`–`C2`.

**Definitions (1–3):**
- `target_lang`: clear English explanation of the typical meaning.
- `native_lang`: concise translation in the user's native language.

**Examples (2–4):**
- Natural, contemporary English sentences.
- Each `sentence` must contain the phrase (or a very close surface form).
- `highlight` must be exactly the phrase text inside `sentence` (same casing/inflection).  
  If it appears multiple times, pick the most important occurrence.

**Notes (0–3):**
- Only include points that are truly important for correct or natural use.
- Focus on common mistakes, register warnings (formal / informal / slang), strong collocations, or grammatical constraints.
- If there is nothing noteworthy, use an empty array.

**Associations (0–5):**
- Short related phrases learners can mentally connect to this one.
- Near‑synonyms (`"focus on" → "pay attention to"`), contrastive pairs (`"lend" vs. "borrow"`), or common alternative patterns.
- One phrase per item, no extra explanation.

## Output Requirements

- Return exactly one JSON object (not an array).
- Follow the JSON schema above strictly.
- Do not include pronunciation, IPA, images, or any other fields.
