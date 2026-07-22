"""Template loader for word collection card templates."""

from ankinote.collections.common import create_template_loader

_PACKAGE = "ankinote.collections.word"

load_card_style, load_template = create_template_loader(_PACKAGE)
