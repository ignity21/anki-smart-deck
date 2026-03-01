# 日本語 語彙カード生成

## 出力形式
JSON配列を返す。各オブジェクト = 一つの品詞

例：「聞く」（複数の意味）→ 同じ品詞なら1つのオブジェクトで複数定義
```json
[
  {
    "word": "string",
    "part_of_speech": "名|動|形|形動|副|助|接|感",
    "pronunciation": "ひらがな" or null,
    "syllables": ["モ", "ー", "ラ"],
    "difficulty": "N5|N4|N3|N2|N1",
    "definitions": [
      {
        "target_lang": "日本語の定義",
        "native_lang": "母語訳",
        "is_visualizable": true|false
      }
    ],
    "synonyms": ["類義語1", "関連語2"],
    "examples": [
      {
        "sentence": "自然な日本語の文",
        "translation": "母語での翻訳",
        "highlights": ["コロケーション"] or null
      }
    ],
    "etymology": "語源" or null,
    "notes": ["活用形", "よくある間違い", "関連語"]
  }
]
```

## 主要ルール

**基本情報:**
- `pronunciation`: ひらがな読み（漢字の場合必須）
- `syllables`: モーラ単位で区切る
- `difficulty`: JLPT レベル推奨

**定義（品詞ごとに2-4個）:**
- `target_lang`: 明確な日本語定義
- `native_lang`: 簡潔な母語訳
- `is_visualizable`: 具体物/動作はtrue、抽象概念はfalse

**類義語（3-5個）:** 一般的な代替語

**用例（2-3個）:**
- 自然で現代的な文
- `highlights`: コロケーション、慣用句をマーク（またはnull）

**語源:** 任意、学習に役立つ場合

**注釈:** 活用形、よくある間違い、関連語、使用域

## 出力要件
- 有効なJSON配列 `[...]` のみを返す
- 説明やマークダウンブロックは不要
- 品詞ごとに一つのオブジェクト

## 例

単語「桜」、母語：英語
```json
[
  {
    "word": "桜",
    "part_of_speech": "名",
    "pronunciation": "さくら",
    "syllables": ["さ", "く", "ら"],
    "difficulty": "N5",
    "definitions": [
      {
        "target_lang": "春に淡紅色の花を咲かせる落葉樹",
        "native_lang": "Cherry blossom tree",
        "is_visualizable": true
      },
      {
        "target_lang": "その花。日本の春の象徴",
        "native_lang": "Cherry blossom flower",
        "is_visualizable": true
      }
    ],
    "synonyms": ["桜の花", "花見の花"],
    "examples": [
      {
        "sentence": "公園の桜が満開です。",
        "translation": "The cherry blossoms are in full bloom.",
        "highlights": ["満開"]
      },
      {
        "sentence": "桜を見に行きます。",
        "translation": "I'm going to see the cherry blossoms.",
        "highlights": ["桜を見に行く"]
      }
    ],
    "etymology": "「咲く」が変化。古くから日本文化で重要",
    "notes": ["「花」は桜を指すことが多い", "花見：桜を見る伝統行事"]
  }
]
```
