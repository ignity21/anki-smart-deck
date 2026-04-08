# Japanese Sentence Card Generation
Generate one JSON object describing a bilingual sentence pair. The *input* you receive will be the **target language sentence** (Japanese).

```json
{
  "target_sentence": "Japanese sentence exactly or very close to the input (all kanji annotated, e.g. '今日[きょう]は天気[てんき]がいいですね').",
  "native_sentence": "Chinese translation conveying the same meaning.",
  "notes": ["Optional important usage notes about the target sentence (all Japanese text with kanji annotated)."],
  "phrases": {
    "useful Japanese phrase or collocation (kanji annotated)": "simple example sentence in Japanese (kanji annotated)"
  }
}
```

## Field Rules
- `target_sentence` — keep exactly as provided; minor spelling/kana fixes are allowed, but do not "correct" colloquial or dialectal forms (e.g. contracted forms like `〜ちゃう`, `〜てる`) — preserve them and note them in `notes` instead; all kanji annotated
- `native_sentence` — faithful, natural translation in Chinese
- `notes` — short, worthy-of-attention observations in Chinese only (can be empty `[]`). Cover nuance, register, common pitfalls, context, and any JLPT N3+ grammar points present in the sentence. If a non-standard structure is grammatically incorrect but very common in spoken Japanese, acknowledge both — note that it is non-standard, explain the correct form, and explicitly state that it is common in spoken Japanese. All quoted Japanese text must have kanji annotated.
- `phrases` — useful expressions or collocations extracted from the sentence; key = Japanese phrase (kanji annotated), value = one simple Japanese example sentence (kanji annotated); can be empty `{}`

## General Guidelines
- Prefer contemporary, common usage; avoid archaic or overly formal expressions unless contextually appropriate
- Never return `null` for any field
- Output **only** valid JSON — no markdown, no comments, no extra keys or text

## Kanji Annotation Rules

- **All kanji must be annotated** with hiragana readings in square brackets immediately after the kanji
- Format: `漢字[かんじ]`
- For compound words with multiple kanji, annotate each morpheme separately: `天気[てんき]`, `学校[がっこう]`
- For verbs/adjectives with okurigana: `食[た]べる`, `美[うつく]しい`
- Apply this to ALL fields containing Japanese text: target_sentence, notes (when quoting Japanese), phrases (both keys and values)
- Even particle-attached words should have kanji annotated: `学校[がっこう]に行[い]く`
