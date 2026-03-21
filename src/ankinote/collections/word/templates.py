"""Template loader for word collection card templates."""

from importlib.resources import files


def load_card_style() -> str:
    """Load the CSS styling for word cards.

    Returns:
        The CSS content as a string
    """
    return (
        files("ankinote.collections.word.card_templates")
        .joinpath("style.css")
        .read_text(encoding="utf-8")
    )


def load_template(filename: str) -> str:
    """Load the front side HTML template for word cards.

    Args:
        filename: The name of the template file to load (e.g., "front.html" or "back.html")

    Returns:
        The front template as a string
    """
    return (
        files("ankinote.collections.word.card_templates")
        .joinpath(filename)
        .read_text(encoding="utf-8")
    )
