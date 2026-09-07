"""Small, file-backed translation layer for the NiceGUI interface."""

import contextvars
import json
from pathlib import Path
from typing import Any

SUPPORTED_LOCALES = {"en": "English", "zh-CN": "简体中文"}
DEFAULT_LOCALE = "en"
_CLIENT_STORAGE_KEY = "ankinote_ui_locale"
_locale = contextvars.ContextVar("ankinote_ui_locale", default=DEFAULT_LOCALE)
_catalogs: dict[str, dict[str, str]] = {}


def _client_storage() -> dict[str, Any] | None:
    """Return the current NiceGUI client's volatile storage, when one is in scope.

    Event handlers and ``ui.timer`` callbacks run in their own asyncio tasks,
    which do not inherit the request-time value of :data:`_locale` — so a
    deferred re-render (for example the sync panel relabelling itself after a
    full sync) would fall back to English even though the page was built in
    another language. Those callbacks *do* run within the sending element's
    client context, so the client's own storage carries the locale across them.
    """
    try:
        from nicegui import context

        return context.client.storage
    except Exception:
        return None


def set_locale(locale: str) -> None:
    """Set the locale for the current NiceGUI client (and request/task)."""
    resolved = locale if locale in SUPPORTED_LOCALES else DEFAULT_LOCALE
    _locale.set(resolved)
    storage = _client_storage()
    if storage is not None:
        storage[_CLIENT_STORAGE_KEY] = resolved


def get_locale() -> str:
    storage = _client_storage()
    if storage is not None:
        stored = storage.get(_CLIENT_STORAGE_KEY)
        if stored in SUPPORTED_LOCALES:
            return stored
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
