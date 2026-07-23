# Japanese Vocabulary Anki Card Generation

Return only valid JSON. No markdown. No comments.

Goal: generate compact learning data for Anki cards optimized for recognition, recall, and spelling.

Furigana rule:
- Add hiragana readings to every kanji individually with `<Kanji:reading>`.
- Correct: `<招:まね>き<猫:ねこ>`
- Wrong: `<招き猫:まねきねこ>`

```json
[
  {
    "lemma": "string without furigana",
    "part_of_speech": "名詞|動詞|形容詞|形容動詞|副詞|助詞|接続詞|感動詞",
    "pronunciation": "hiragana or null",
    "difficulty": "N5|N4|N3|N2|N1",
    "morphology": "活用・読み分け・送り仮名の要点。なければ null",
    "core_meaning": {
      "target_text": "短い日本語の説明。漢字には必ず <Kanji:reading> を付ける。",
      "native_text": "母語での短い訳",
      "is_visualizable": true
    },
    "supporting_meanings": [
      {
        "target_text": "短い補助義項。漢字には必ず <Kanji:reading> を付ける。",
        "native_text": "母語での短い訳",
        "is_visualizable": false
      }
    ],
    "examples": [
      {
        "sentence": "例文。漢字には必ず <Kanji:reading> を付ける。",
        "translation": "母語訳",
        "highlights": ["語形またはコロケーション。漢字には必ず <Kanji:reading> を付ける。"]
      }
    ],
    "collocations": ["よく使う組み合わせ。漢字には必ず <Kanji:reading> を付ける。"],
    "confusions": ["似た語との違いを母語で短く説明。日语を使うなら漢字は必ず <Kanji:reading> を字ごとに付ける。"],
    "etymology_or_memory": "必要なら母語で記憶フック。主要な母語訳・意味アンカーを文中に明示する。不要なら null",
    "production_hint": "単語を直接書かずに、思い出すための短いヒント"
  }
]
```

Rules:
- Return 1 to 2 records total for the queried word. Keep only the most common and worth-learning parts of speech.
- `core_meaning` must contain exactly one primary sense.
- `supporting_meanings` may contain 0 to 2 brief secondary sense summaries. Do not duplicate the core meaning.
- `examples` must contain 1 to 2 high-value examples tied to the core meaning.
- `collocations` must contain 2 to 4 common combinations when available.
- `confusions` may contain 0 to 2 short native-language contrasts or misuse warnings.
- Prefer the user's native language in `confusions`. If you use Japanese anywhere in `confusions`, every kanji must use per-character `<Kanji:reading>` annotation. Never group multiple kanji inside one annotation block.
- `production_hint` must help recall the lemma but must not contain the lemma itself.
- `etymology_or_memory`, when present, must be written in the user's native language and should explicitly mention the main native-language meaning anchor.
- Prioritize learner value over exhaustive dictionary coverage.
- Keep Japanese wording at or below the stated JLPT difficulty level.
