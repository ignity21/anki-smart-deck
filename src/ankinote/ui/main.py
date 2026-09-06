"""ankinote GUI — NiceGUI-powered interface for Anki card generation."""

from nicegui import ui

from ankinote.ui.config import load_settings, save_settings
from ankinote.ui.i18n import SUPPORTED_LOCALES, set_locale, t
from ankinote.ui.pages.notetypes import notetypes_page
from ankinote.ui.pages.phrase import phrase_page
from ankinote.ui.pages.sentence import sentence_page
from ankinote.ui.pages.settings import settings_page
from ankinote.ui.pages.stem import stem_page
from ankinote.ui.pages.word import word_page


def _create_layout() -> None:
    """Create the shared layout elements (header, drawer, footer)."""
    settings = load_settings()
    set_locale(settings.ui_language)
    # Header
    with ui.header(elevated=True).classes(
        "items-center justify-between px-4 h-14 bg-primary text-white"
    ):
        ui.label("ankinote").classes("text-lg font-bold text-white")

        with ui.row().classes("items-center gap-1"):

            def _change_language(locale: str) -> None:
                settings.ui_language = locale
                save_settings(settings)
                ui.run_javascript("window.location.reload()")

            dark = ui.dark_mode()
            dark_switch = ui.switch(
                value=dark.value,
                on_change=lambda event: dark.set_value(event.value),
            ).props("dense checked-icon=dark_mode unchecked-icon=light_mode")
            dark_switch.classes("text-white")
            with dark_switch:
                ui.tooltip(t("nav.dark_mode"))

            with (
                ui.button(icon="translate")
                .props("flat round dense")
                .classes("text-white")
            ):
                ui.tooltip(t("nav.language"))
                with (
                    ui.menu()
                    .props('anchor="bottom right" self="top right"')
                    .style("width: 10rem")
                ):
                    for locale, label in SUPPORTED_LOCALES.items():
                        ui.item(
                            label,
                            on_click=lambda locale=locale: _change_language(locale),
                        ).props(
                            f"dense {'active' if locale == settings.ui_language else ''}"
                        )

    # Left drawer (navigation)
    with ui.left_drawer(value=True).classes("bg-gray-50 dark:bg-gray-900"):
        ui.label(t("nav.navigation")).classes(
            "text-sm font-semibold text-gray-500 dark:text-slate-300 px-4 pt-4 pb-2"
        )

        with ui.column().classes("w-full gap-1 px-2"):
            ui.link(t("nav.word_cards"), "/").classes(
                "w-full px-3 py-2 rounded dark:text-slate-200 hover:bg-gray-200 "
                "dark:hover:bg-gray-700"
            )
            ui.link(t("nav.phrase_cards"), "/phrases").classes(
                "w-full px-3 py-2 rounded dark:text-slate-200 hover:bg-gray-200 "
                "dark:hover:bg-gray-700"
            )
            ui.link(t("nav.sentence_cards"), "/sentences").classes(
                "w-full px-3 py-2 rounded dark:text-slate-200 hover:bg-gray-200 "
                "dark:hover:bg-gray-700"
            )
            ui.link(t("nav.stem_cards"), "/stem").classes(
                "w-full px-3 py-2 rounded dark:text-slate-200 hover:bg-gray-200 "
                "dark:hover:bg-gray-700"
            )
            ui.link(t("nav.card_types"), "/notetypes").classes(
                "w-full px-3 py-2 rounded dark:text-slate-200 hover:bg-gray-200 "
                "dark:hover:bg-gray-700"
            )
            ui.link(t("nav.settings"), "/settings").classes(
                "w-full px-3 py-2 rounded dark:text-slate-200 hover:bg-gray-200 "
                "dark:hover:bg-gray-700"
            )


@ui.page("/")
def _word_page() -> None:
    """Word card generation page."""
    _create_layout()
    word_page()


@ui.page("/phrases")
def _phrase_page() -> None:
    """Phrase and idiom card generation page."""
    _create_layout()
    phrase_page()


@ui.page("/sentences")
def _sentence_page() -> None:
    """Sentence card generation page."""
    _create_layout()
    sentence_page()


@ui.page("/stem")
def _stem_page() -> None:
    """STEM card generation page."""
    _create_layout()
    stem_page()


@ui.page("/notetypes")
def _notetypes_page() -> None:
    """Card Types (note type + deck setup) page."""
    _create_layout()
    notetypes_page()


@ui.page("/settings")
def _settings_page() -> None:
    """Settings page."""
    _create_layout()
    settings_page()


def start_gui() -> None:
    """Launch the ankinote GUI."""
    ui.run(
        title="ankinote",
        favicon="📝",
        storage_secret="ankinote-ui-session-key",
        reload=False,
    )


if __name__ in {"__main__", "__mp_main__"}:
    start_gui()
