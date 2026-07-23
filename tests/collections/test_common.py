"""Tests for shared collection text helpers."""

from ankinote.collections.common import convert_to_html_ruby, strip_phonetic_annotations


def test_convert_to_html_ruby_supports_inline_style_annotations():
    text = "商<しょう>売<ばい>繁<はん>盛<じょう>を願<ねが>う"
    converted = convert_to_html_ruby(text)

    assert "<ruby>商<rt>しょう</rt></ruby>" in converted
    assert "<ruby>願<rt>ねが</rt></ruby>う" in converted


def test_strip_phonetic_annotations_supports_inline_style_annotations():
    text = "商<しょう>売<ばい>繁<はん>盛<じょう>を願<ねが>う"

    assert strip_phonetic_annotations(text) == "商売繁盛を願う"
