# US English Vocabulary Anki Card Generation

Return only valid JSON. No markdown. No comments.

Goal: generate compact learning data for Anki cards optimized for recognition, recall, and spelling.

```json
[
  {
    "lemma": "string",
    "part_of_speech": "noun|verb|adjective|adverb|phrasal verb",
    "pronunciation": "/IPA/ or null; use US English IPA",
    "difficulty": "A1|A2|B1|B2|C1|C2",
    "morphology": "Short morphology note such as plural, past tense, comparative, stress pattern, or null",
    "core_meaning": {
      "target_text": "One short English definition for the main sense.",
      "native_text": "Short native-language translation for the main sense.",
      "is_visualizable": true
    },
    "supporting_meanings": [
      {
        "target_text": "Short English gloss for a secondary useful sense.",
        "native_text": "Short native-language translation.",
        "is_visualizable": false
      }
    ],
    "examples": [
      {
        "sentence": "One high-value English example sentence using the lemma or an inflected form.",
        "translation": "Native-language translation.",
        "highlights": ["useful collocation or inflected form"]
      }
    ],
    "collocations": ["high-frequency phrase", "another phrase"],
    "confusions": ["brief contrast with a similar word"],
    "etymology_or_memory": "Optional memory hook in the user's native language. Explicitly include the main native-language translation or meaning anchor, or null",
    "production_hint": "A short cue that helps the learner recall the lemma without revealing it."
  }
]
```

Rules:
- Return 1 to 2 records total for the queried word. Keep only the most common and worth-learning parts of speech.
- `core_meaning` must contain exactly one primary sense. Keep it short and memorable.
- `supporting_meanings` may contain 0 to 2 brief secondary sense summaries. Do not duplicate the core meaning.
- `examples` must contain 1 to 2 high-value examples tied to the core meaning.
- `collocations` must contain 2 to 4 common combinations when available.
- `confusions` may contain 0 to 2 items about near-synonyms, false friends, or common misuse.
- `production_hint` must help recall the target word but must not contain the lemma itself.
- `etymology_or_memory`, when present, must be written in the user's native language and should explicitly mention the main native-language meaning anchor.
- Prefer concise, learner-friendly wording over dictionary-style detail.
- Keep every target-language string at or below the stated difficulty level.
