"""Common utilities for collection modules."""

from collections.abc import Callable
from importlib.resources import files
from typing import TypeVar

import re
from pydantic import BaseModel

from ankinote.consts import Language


def load_card_style(package: str) -> str:
    """Load the CSS styling for card templates.

    Args:
        package: The full package path containing card_templates
            (e.g., "ankinote.collections.word").

    Returns:
        The CSS content as a string.
    """
    return (
        files(f"{package}.card_templates")
        .joinpath("style.css")
        .read_text(encoding="utf-8")
    )


def load_template(package: str, filename: str) -> str:
    """Load an HTML template for cards.

    Args:
        package: The full package path containing card_templates
            (e.g., "ankinote.collections.word").
        filename: The name of the template file to load
            (e.g., "front.html" or "back.html").

    Returns:
        The template content as a string.
    """
    return (
        files(f"{package}.card_templates")
        .joinpath(filename)
        .read_text(encoding="utf-8")
    )


def load_prompt_template(
    package: str,
    target_language: Language,
    language_to_filename: dict[Language, str],
) -> str:
    """Load prompt template for the target language.

    Args:
        package: The full package path containing prompts
            (e.g., "ankinote.collections.word").
        target_language: The language being learned.
        language_to_filename: Mapping from Language to prompt filename.

    Returns:
        The prompt template content as a string.

    Raises:
        FileNotFoundError: If no prompt template exists for the language.
    """
    filename = language_to_filename.get(target_language)
    if filename is None:
        raise FileNotFoundError(
            f"No prompt template found for language: {target_language.value}. "
            f"Available languages: {list(language_to_filename.keys())}"
        )

    return files(f"{package}.prompts").joinpath(filename).read_text(encoding="utf-8")


# Type variable for Pydantic model types
T = TypeVar("T", bound=BaseModel)


def create_template_loader(
    package: str,
) -> tuple[
    Callable[[], str],
    Callable[[str], str],
]:
    """Create template loader functions for a specific package.

    Args:
        package: The full package path (e.g., "ankinote.collections.word").

    Returns:
        A tuple of (load_card_style, load_template) functions bound to the package.
    """

    def _load_card_style() -> str:
        return load_card_style(package)

    def _load_template(filename: str) -> str:
        return load_template(package, filename)

    return _load_card_style, _load_template


def create_prompt_loader(
    package: str,
    language_to_filename: dict[Language, str],
) -> Callable[[Language], str]:
    """Create a prompt loader function for a specific package.

    Args:
        package: The full package path (e.g., "ankinote.collections.word").
        language_to_filename: Mapping from Language to prompt filename.

    Returns:
        A function that loads prompt templates for a given language.
    """

    def _load_prompt(target_language: Language) -> str:
        return load_prompt_template(package, target_language, language_to_filename)

    return _load_prompt


_ANGLED_PHONETIC_PATTERN = re.compile(r"<([^:>]+):([^>]+)>")  # <汉:hàn>


def strip_phonetic_annotations(text: str) -> str:
    """Strip angled-style phonetic annotations to get plain text (e.g., for TTS).

    Examples:
      - Japanese:  <食:た>べる  →  食べる
      - Chinese:   <汉:hàn><字:zì>  →  汉字
      - Bopomofo:  <你:ㄋㄧˇ>  →  你

    Args:
        text: Text containing angled-style phonetic annotations.

    Returns:
        Plain text with all phonetic annotations and brackets removed.
    """
    return _ANGLED_PHONETIC_PATTERN.sub(r"\1", text)


def convert_to_html_ruby(text: str) -> str:
    """Convert angled-style phonetic annotations to HTML ruby tags."""
    return _ANGLED_PHONETIC_PATTERN.sub(r"<ruby>\1<rt>\2</rt></ruby>", text)
