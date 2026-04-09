# Japanese Sentence Card Generation
Generate one JSON object describing a bilingual sentence pair. The *input* you receive will be the **target language sentence** (Japanese).

```json
{
  "target_sentence": "Japanese sentence exactly or very close to the input (per-character furigana, e.g. '今[きょ]日[う]は天[てん]気[き]がいいですね').",
  "native_sentence": "Chinese translation conveying the same meaning.",
  "notes": ["Optional important usage notes about the target sentence (all Japanese text with per-character furigana)."],
  "phrases": {
    "useful Japanese phrase or collocation (per-character furigana)": "simple example sentence in Japanese (per-character furigana)"
  }
}
```

## Field Rules
- `target_sentence` — keep exactly as provided; minor spelling/kana fixes are allowed, but do not "correct" colloquial or dialectal forms (e.g. contracted forms like `〜ちゃう`, `〜てる`) — preserve them and note them in `notes` instead; per-character furigana
- `native_sentence` — faithful, natural translation in Chinese
- `notes` — short, worthy-of-attention observations in Chinese only (can be empty `[]`). Cover nuance, register, common pitfalls, context, and any JLPT N3+ grammar points present in the sentence. If a non-standard structure is grammatically incorrect but very common in spoken Japanese, acknowledge both — note that it is non-standard, explain the correct form, and explicitly state that it is common in spoken Japanese. All quoted Japanese text must have per-character furigana.
- `phrases` — useful expressions or collocations extracted from the sentence; key = Japanese phrase (per-character furigana), value = one simple Japanese example sentence (per-character furigana); can be empty `{}`

## General Guidelines
- Prefer contemporary, common usage; avoid archaic or overly formal expressions unless contextually appropriate
- Never return `null` for any field
- Output **only** valid JSON — no markdown, no comments, no extra keys or text

## Per-Character Furigana Annotation Rules

- **Each kanji must be annotated individually** with its reading in square brackets immediately after it
- Format: `漢[かん]字[じ]` (NOT `漢字[かんじ]`)
- For compound words, annotate each kanji separately: `今[きょ]日[う]`, `天[てん]気[き]`, `学[がっ]校[こう]`
- Okurigana (trailing kana) should appear outside the brackets: `食[た]べる`, `美[うつく]しい`
- Even particle-attached words should have per-character furigana: `学[がっ]校[こう]に行[い]く`
- Apply this to ALL fields containing Japanese text: target_sentence, notes (when quoting Japanese), phrases (both keys and values)
