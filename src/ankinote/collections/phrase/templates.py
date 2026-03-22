"""Template loader for phrase collection card templates."""

from importlib.resources import files


def load_card_style() -> str:
    """Load the CSS styling for phrase cards.

    Returns:
        The CSS content as a string.
    """
    return (
        files("ankinote.collections.phrase.card_templates")
        .joinpath("style.css")
        .read_text(encoding="utf-8")
    )


def load_template(filename: str) -> str:
    """Load an HTML template for phrase cards.

    Args:
        filename: The name of the template file to load
            (e.g., "front.html" or "back.html").

    Returns:
        The template content as a string.
    """
    return (
        files("ankinote.collections.phrase.card_templates")
        .joinpath(filename)
        .read_text(encoding="utf-8")
    )
