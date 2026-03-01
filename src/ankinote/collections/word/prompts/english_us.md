# English (US) Vocabulary Card Generation

## Output Format
Return a JSON array. Each object = one part of speech.

Example: "book" (noun + verb) → return 2 objects
```json
[
  {
    "word": "string",
    "part_of_speech": "n.|vt.|vi.|adj.|adv.|prep.|conj.|interj.",
    "pronunciation": "/IPA/" or null,
    "syllables": ["syl", "la", "bles"],
    "difficulty": "A1|A2|B1|B2|C1|C2",
    "definitions": [
      {
        "target_lang": "English definition",
        "native_lang": "Translation (Chinese: 2-6 chars)",
        "is_visualizable": true|false
      }
    ],
    "synonyms": ["word1", "phrase2"],
    "examples": [
      {
        "sentence": "Natural English sentence",
        "translation": "Native language translation",
        "highlights": ["collocation", "idiom"],
      }
    ],
    "etymology": "Word origin" or null,
    "collocations": ["collocation1", "collocation2"],
    "notes": ["Irregular forms", "UK vs US", "Common mistakes"]
  }
]
```
- Never return `null` for array fields

## Key Rules

**Basic Info:**
- `pronunciation`: US IPA, e.g., "/bʊk/"
- `syllables`: Break into pronounceable units
- `difficulty`: CEFR level preferred

**Definitions (2-4 per POS):**
- `target_lang`: Clear English definition
- `native_lang`: Concise translation (Chinese: 2-6 chars like "书籍" not "一本印刷或电子的出版物")
- `is_visualizable`: true for concrete objects/actions, false for abstract concepts

**Synonyms (3-5):** Common alternatives

**Examples (2-3):**
- Natural, contemporary sentences
- `highlights`: Mark collocations, phrasal verbs, idioms (or null)

**Etymology:** Optional, if interesting for learning

**Collocations (3-5):** Common word combinations
- List most frequent collocations with this word
- Examples: "make a decision", "strong coffee"
- Return null if not applicable (e.g., function words)

**Notes:** Irregular forms, UK/US differences, common mistakes, related terms

## Output Requirements
- Return ONLY valid JSON array `[...]`
- No explanations, no markdown blocks
- One object per part of speech

## Example

Word "book", native language: Chinese (Simplified)
```json
[
  {
    "word": "book",
    "part_of_speech": "n.",
    "pronunciation": "/bʊk/",
    "syllables": ["book"],
    "difficulty": "A1",
    "definitions": [
      {
        "target_lang": "A written work with printed pages bound together",
        "native_lang": "书；书籍",
        "is_visualizable": true
      }
    ],
    "synonyms": ["volume", "publication", "text"],
    "examples": [
      {
        "sentence": "I'm reading an interesting book about history.",
        "translation": "我正在读一本关于历史的有趣的书。",
        "highlights": []
      }
    ],
    "etymology": "From Old English 'bōc', related to beech tree",
    "collocations": ["read/write/publish a book"],
    "notes": ["Plural: books"]
  },
  {
    "word": "book",
    "part_of_speech": "vt.",
    "pronunciation": "/bʊk/",
    "syllables": ["book"],
    "difficulty": "A2",
    "definitions": [
      {
        "target_lang": "To reserve or arrange something in advance",
        "native_lang": "预订；预约",
        "is_visualizable": false
      }
    ],
    "synonyms": ["reserve", "schedule"],
    "examples": [
      {
        "sentence": "I need to book a table for dinner.",
        "translation": "我需要预订晚餐的桌子。",
        "highlights": ["book a table"]
      }
    ],
    "etymology": "Extended from noun - 'to register in a book'",
    "collocations": ["book a flight/hotel/ticket/appointment"],
    "notes": []
  }
]
```
