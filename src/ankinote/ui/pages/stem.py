"""STEM card page — generate a STEM card via AI, preview, and push to Anki."""

import asyncio
from typing import Literal

from nicegui import ui

from ankinote.app import Application
from ankinote.collections.stem import CardType, StemCollection, StemModel
from ankinote.services.ai import (
    LiteLLMImageService,
    LiteLLMTextService,
    resolve_thinking,
)
from ankinote.services.anki import AnkiConnectClient
from ankinote.ui.config import (
    CUSTOM_VENDOR,
    ProviderProfile,
    Settings,
    apply_env,
    get_image_provider_models,
    load_settings,
)
from ankinote.ui.pages.word import format_error

_THINKING_OPTIONS = {
    "default": "Default (thinking on)",
    "off": "Off",
    "low": "Low",
    "medium": "Medium",
    "high": "High",
}


def _build_text_service(settings: Settings) -> LiteLLMTextService:
    """Assemble the text service from the active text provider profile."""
    profile = settings.text_providers.get(settings.active_text_provider) or (
        ProviderProfile()
    )
    return LiteLLMTextService(
        api_base=profile.base_url or None,
        api_key=profile.api_key or None,
        force_openai_route=profile.vendor == CUSTOM_VENDOR,
    )


def stem_page() -> None:
    """Render the STEM card generation page."""

    settings = load_settings()
    apply_env(settings)
    client = ui.context.client

    def _notify(
        message: str,
        notification_type: Literal["positive", "negative", "warning"],
    ) -> None:
        with client:
            ui.notify(message, type=notification_type)

    def _image_model_options(profile: ProviderProfile) -> list[str]:
        models = (
            []
            if profile.vendor == CUSTOM_VENDOR
            else get_image_provider_models(profile.vendor)
        )
        if profile.model and profile.model not in models:
            models = [profile.model, *models]
        return models

    with ui.column().classes("w-full max-w-2xl mx-auto p-6 gap-4"):
        ui.label("STEM Cards").classes("text-2xl font-bold")
        ui.label(
            "One card per topic. Concept cards open an editable preview before "
            "they are saved; formula and procedure cards are added directly."
        ).classes("text-sm text-gray-500")

        topic_input = ui.input(
            label="Topic",
            placeholder="e.g. What is entropy?  /  解释贝叶斯定理",
        ).classes("w-full")

        thinking_select = ui.select(
            label="Thinking",
            options=_THINKING_OPTIONS,
            value="default",
        ).classes("w-full")

        generate_image_switch = ui.switch(
            "Generate diagram",
            value=settings.defaults.generate_image,
        )

        active_image_profile = (
            settings.image_providers.get(settings.active_image_provider)
            or ProviderProfile()
        )

        with (
            ui.row()
            .classes("w-full gap-4")
            .bind_visibility_from(generate_image_switch, "value")
        ):
            image_profile_select = ui.select(
                label="Image Provider",
                options=list(settings.image_providers.keys()),
                value=settings.active_image_provider,
            ).classes("flex-1")
            image_model_select = ui.select(
                label="Image Model",
                options=_image_model_options(active_image_profile),
                value=active_image_profile.model,
                new_value_mode="add-unique",
            ).classes("flex-1")

        def _on_image_profile_change() -> None:
            profile = (
                settings.image_providers.get(image_profile_select.value)
                or ProviderProfile()
            )
            models = _image_model_options(profile)
            current = image_model_select.value
            image_model_select.set_options(models)
            image_model_select.value = (
                current if current in models else (models[0] if models else current)
            )

        image_profile_select.on_value_change(lambda _: _on_image_profile_change())

        results_container = ui.column().classes("w-full gap-2")
        status_label = ui.label("").classes("text-sm text-gray-500")

        generate_btn = (
            ui.button(
                "Generate",
                on_click=lambda: asyncio.ensure_future(_generate()),
                icon="auto_awesome",
            )
            .props("unevaluated")
            .classes("w-full")
        )

        def _collection(
            anki_client: AnkiConnectClient,
            settings: Settings,
            *,
            with_image: bool,
            reasoning_effort: str | None,
        ) -> StemCollection:
            image_service = None
            if with_image:
                image_profile = (
                    settings.image_providers.get(image_profile_select.value)
                    or ProviderProfile()
                )
                image_service = LiteLLMImageService(
                    model=image_model_select.value or image_profile.model,
                    image_size=settings.image_size,
                    api_key=image_profile.api_key or None,
                    api_base=image_profile.base_url or None,
                    force_openai_route=image_profile.vendor == CUSTOM_VENDOR,
                )
            text_profile = (
                settings.text_providers.get(settings.active_text_provider)
                or ProviderProfile()
            )
            return StemCollection(
                anki_client,
                text_model=text_profile.model,
                text_service=_build_text_service(settings),
                image_service=image_service,
                reasoning_effort=reasoning_effort,
            )

        async def _save_edited(
            topic: str,
            model: StemModel,
            with_image: bool,
            reasoning_effort: str | None,
            fields: dict[str, ui.input | ui.textarea],
            save_btn: ui.button,
        ) -> None:
            tags = [
                t.strip() for t in (fields["tags"].value or "").split(",") if t.strip()
            ]
            edited = model.model_copy(
                update={
                    "front": (fields["front"].value or "").strip(),
                    "back_brief": (fields["back_brief"].value or "").strip(),
                    "back_detail": (fields["back_detail"].value or "").strip(),
                    "tags": tags,
                }
            )
            save_btn.props("loading")
            save_btn.update()
            try:
                settings = load_settings()
                apply_env(settings)
                async with Application():
                    anki = AnkiConnectClient()
                    async with _collection(
                        anki,
                        settings,
                        with_image=with_image,
                        reasoning_effort=reasoning_effort,
                    ) as collection:
                        await collection.add_note(edited, topic=topic)
                results_container.clear()
                status_label.text = f"✓ {edited.front} — saved to Anki"
                _notify("Card saved to Anki", "positive")
            except Exception as exc:
                message = format_error(exc)
                status_label.text = f"Error: {message}"
                _notify(f"Error: {message}", "negative")
            finally:
                save_btn.props(remove="loading")
                save_btn.update()

        def _render_preview(
            topic: str,
            model: StemModel,
            with_image: bool,
            reasoning_effort: str | None,
        ) -> None:
            results_container.clear()
            with results_container, ui.card().classes("w-full p-4 gap-3"):
                ui.label("Concept card — review and edit").classes(
                    "text-sm font-semibold"
                )
                front = ui.input(label="Front", value=model.front).classes("w-full")
                back_brief = (
                    ui.textarea(label="Back (brief)", value=model.back_brief)
                    .classes("w-full")
                    .props("autogrow")
                )
                back_detail = (
                    ui.textarea(label="Back (detail)", value=model.back_detail)
                    .classes("w-full")
                    .props("autogrow")
                )
                tags = ui.input(
                    label="Tags (comma-separated)",
                    value=", ".join(model.tags),
                ).classes("w-full")
                if model.image_description:
                    ui.label(
                        "A diagram will be generated on save."
                        if with_image
                        else "The model suggested a diagram; enable "
                        '"Generate diagram" to include one.'
                    ).classes("text-xs text-gray-500")

                fields: dict[str, ui.input | ui.textarea] = {
                    "front": front,
                    "back_brief": back_brief,
                    "back_detail": back_detail,
                    "tags": tags,
                }
                with ui.row().classes("w-full justify-end gap-2"):
                    ui.button(
                        "Discard", icon="close", on_click=results_container.clear
                    ).props("flat")
                    save_btn: ui.button = ui.button(
                        "Save to Anki",
                        icon="save",
                        on_click=lambda: asyncio.ensure_future(
                            _save_edited(
                                topic,
                                model,
                                with_image,
                                reasoning_effort,
                                fields,
                                save_btn,
                            )
                        ),
                    )

        async def _generate() -> None:
            settings = load_settings()
            apply_env(settings)

            topic = (topic_input.value or "").strip()
            if not topic:
                _notify("Enter a topic", "warning")
                return

            with_image = bool(generate_image_switch.value)
            reasoning_effort = resolve_thinking(thinking_select.value, unset=None)

            generate_btn.props("loading")
            generate_btn.update()
            results_container.clear()
            status_label.text = "Generating…"

            try:
                async with Application():
                    anki = AnkiConnectClient()
                    async with _collection(
                        anki,
                        settings,
                        with_image=with_image,
                        reasoning_effort=reasoning_effort,
                    ) as collection:
                        model = await collection.generate_model(topic)
                        if model.card_type == CardType.CONCEPT:
                            status_label.text = ""
                            _render_preview(topic, model, with_image, reasoning_effort)
                        else:
                            await collection.add_note(model, topic=topic)
                            status_label.text = (
                                f"✓ {model.front} — {model.card_type.value} card "
                                "added to Anki (no preview)"
                            )
                            _notify("Card added to Anki", "positive")
            except Exception as exc:
                message = format_error(exc)
                status_label.text = f"Error: {message}"
                _notify(f"Error: {message}", "negative")
            finally:
                generate_btn.props(remove="loading")
                generate_btn.update()
