"""Small, file-backed translation layer for the NiceGUI interface."""

import contextvars
import json
from pathlib import Path
from typing import Any

SUPPORTED_LOCALES = {"en": "English", "zh-CN": "简体中文"}
DEFAULT_LOCALE = "en"
_locale = contextvars.ContextVar("ankinote_ui_locale", default=DEFAULT_LOCALE)
_catalogs: dict[str, dict[str, str]] = {}


def set_locale(locale: str) -> None:
    """Set the locale for the current NiceGUI request/task."""
    _locale.set(locale if locale in SUPPORTED_LOCALES else DEFAULT_LOCALE)


def get_locale() -> str:
    return _locale.get()


def _catalog(locale: str) -> dict[str, str]:
    if locale not in _catalogs:
        path = Path(__file__).with_name("locales") / f"{locale}.json"
        _catalogs[locale] = json.loads(path.read_text(encoding="utf-8"))
    return _catalogs[locale]


def t(key: str, **values: Any) -> str:
    """Translate a stable key, falling back to English for missing entries."""
    text = _catalog(get_locale()).get(key) or _catalog(DEFAULT_LOCALE).get(key) or key
    return text.format(**values)
