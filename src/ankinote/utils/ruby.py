import regex

_RUBY_ANNOTATION_PATTERN = regex.compile(r"(\X)\[([^\]]+)\]")


def convert_to_ruby_annotation(text: str) -> str:
    """Convert bracket-style phonetic annotations to HTML ruby tags.

    Supports per-character annotations used in multiple writing systems:
      - Japanese furigana:  食[た]べる  →  <ruby>食<rt>た</rt></ruby>べる
      - Chinese pinyin:     汉[hàn]字[zì]  →  <ruby>汉<rt>hàn</rt></ruby><ruby>字<rt>zì</rt></ruby>
      - Bopomofo:           你[ㄋㄧˇ]  →  <ruby>你<rt>ㄋㄧˇ</rt></ruby>

    Each annotated character should correspond to a single ruby unit.
    For multi-character words, annotate each character separately:
      Preferred:   汉[hàn]字[zì]
      Avoid:       汉字[hàn zì]

    Args:
        text: Text containing bracket-style phonetic annotations.

    Returns:
        Text with annotations converted to HTML ruby format.
    """
    return _RUBY_ANNOTATION_PATTERN.sub(r"<ruby>\1<rt>\2</rt></ruby>", text)
