# Japanese Phrase / Idiom Anki Card Generation

Return only valid JSON. No markdown. No comments.

Goal: generate compact learning data for Anki cards optimized for recognition and recall. No spelling or image cards.

## Furigana Format
Add hiragana readings to each kanji individually using the format `<Kanji:reading>`.

e.g.
-- ✅ Correct: `<商:しょう><売:ばい><繁:はん><盛:じょう>` (Each kanji has its own block)
-- ❌ WRONG: `<商売繁盛:しょうばいはんじょう>` (Do NOT group kanji)

-- ✅ Correct: `<縁:えん><起:ぎ><物:もの>`
-- ❌ WRONG: `<縁起物:えんぎもの>` (Do NOT group kanji)

-- ✅ Correct: `<招:まね>き<猫:ねこ>`
-- ❌ WRONG: `<招:まね><き><猫:ねこ>`

## JSON Output
```json
{
  "phrase": "string (no furigana annotation e.g. '一石二鳥')",
  "difficulty": "N5|N4|N3|N2|N1",
  "core_meaning": {
    "target_text": "日本語の説明。漢字には必ず <Kanji:reading> を付ける。",
    "native_text": "母語での短い訳"
  },
  "supporting_meanings": [
    {
      "target_text": "短い補助義項。漢字には必ず <Kanji:reading> を付ける。",
      "native_text": "母語での短い訳"
    }
  ],
  "examples": [
    {
      "sentence": "自然な例文。漢字には必ず <Kanji:reading> を付ける。",
      "translation": "母語訳",
      "highlights": ["語形または慣用句。漢字には必ず <Kanji:reading> を付ける。"]
    }
  ],
  "usage_pattern": "用法パターン。例：'動詞＋目的語'、'固定表現'、'〜という意味で使う'。単純なら null。",
  "production_hint": "フレーズを思い出すための短いヒント（母語で）。フレーズ自体を含まないこと。",
  "confusions": ["似た表現との違いや誤用を母語で短く説明。日本語を使うなら漢字は必ず <Kanji:reading> を付ける。"],
  "etymology_or_memory": "必要なら母語で語源・記憶フック。主要な母語訳を文中に明示する。不要なら null。",
  "associations": ["関連表現や対義表現。漢字には必ず <Kanji:reading> を付ける。"]
}
```

## Field Rules
- `level ≤ difficulty` means "Calibrate examples and notes to the phrase's JLPT level: use only vocabulary and grammar ≤ that difficulty"

| Field | Constraint |
|---|---|
| `core_meaning` | 1つだけ。短く覚えやすく。 |
| `supporting_meanings` | 0–2個。core_meaningと重複しないこと。 |
| `examples` | 1–3個。例文は `level ≤ difficulty`。`highlights` は文中の表層形と完全一致。 |
| `usage_pattern` | 慣用句・固定表現・助詞の用法に便利。単純なフレーズなら null。 |
| `production_hint` | フレーズを直接書かずに、思い出すための短いヒント。 |
| `confusions` | 0–2個。日本語を使うなら全漢字に個別 `<Kanji:reading>`。 |
| `etymology_or_memory` | 母語で書き、主要な母語訳を文中に明示。不要なら null。 |
| `associations` | 0–5個。類義語・対義語・関連表現。 |
- 学習者価値を優先し、辞書的な網羅性より簡潔さを重視。
