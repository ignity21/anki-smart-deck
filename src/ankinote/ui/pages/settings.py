"""Settings page — LLM provider, TTS, and default language preferences."""

import os
from dataclasses import dataclass
from typing import Literal

import httpx
from nicegui import ui

from ankinote.consts import Language
from ankinote.ui.config import (
    IMAGE_PROVIDERS,
    PROVIDERS,
    CustomProvider,
    DefaultsConfig,
    Settings,
    apply_env,
    fetch_image_model_ids,
    fetch_model_ids,
    get_image_provider_models,
    get_provider_models,
    image_env_key_for,
    image_provider_for,
    load_settings,
    save_settings,
)
from ankinote.ui.pages.word import format_error

# Providers offered in the "Add provider" menu, in display order. Anything not
# on this list can still be reached through "Custom endpoint".
_ADDABLE_PROVIDERS: tuple[str, ...] = tuple(PROVIDERS.keys())

_PROVIDER_ENV_KEYS: frozenset[str] = frozenset(
    info["env_key"] for info in PROVIDERS.values()
)


@dataclass
class RouteDraft:
    """One provider profile shown on the settings page, edited in place."""

    kind: Literal["builtin", "custom"]
    name: str
    model: str = ""
    base_url: str = ""
    api_key: str = ""
    saved: bool = False


def _routes_from_settings(settings: Settings) -> list[RouteDraft]:
    """Build the editable route list: configured built-ins first, then customs.

    A built-in provider is only listed once it has an API key (or is the one
    currently in use), so unconfigured providers stay out of the way until the
    user adds them.
    """
    routes: list[RouteDraft] = []
    for name, info in PROVIDERS.items():
        key = settings.api_keys.get(info["env_key"], "")
        if not key and name != settings.provider:
            continue
        routes.append(
            RouteDraft(
                kind="builtin",
                name=name,
                model=settings.text_model
                if name == settings.provider
                else get_provider_models(name)[0],
                api_key=key,
                saved=bool(key),
            )
        )
    for name, profile in settings.custom_providers.items():
        routes.append(
            RouteDraft(
                kind="custom",
                name=name,
                model=profile.model,
                base_url=profile.base_url,
                api_key=profile.api_key,
                saved=True,
            )
        )
    if not routes:
        first = _ADDABLE_PROVIDERS[0]
        routes.append(
            RouteDraft(kind="builtin", name=first, model=get_provider_models(first)[0])
        )
    return routes


def _route_hint(route: RouteDraft) -> str:
    """One-line description shown under the route editor."""
    if route.kind == "custom":
        return route.base_url or "OpenAI-compatible endpoint"
    return f"Built-in route · {PROVIDERS[route.name]['litellm_provider']}"


def settings_page() -> None:
    """Render the settings page."""

    _settings_styles()

    settings: Settings = ui.context.client.storage.get("settings") or load_settings()

    routes = _routes_from_settings(settings)
    state = {
        "selected": next(
            (i for i, r in enumerate(routes) if r.name == settings.provider), 0
        )
    }

    def _select(index: int) -> None:
        state["selected"] = index
        _route_workspace.refresh()

    def _add_builtin(name: str) -> None:
        existing = next((i for i, r in enumerate(routes) if r.name == name), None)
        if existing is None:
            routes.append(
                RouteDraft(
                    kind="builtin", name=name, model=get_provider_models(name)[0]
                )
            )
            existing = len(routes) - 1
        _select(existing)

    def _add_custom() -> None:
        routes.append(RouteDraft(kind="custom", name=""))
        _select(len(routes) - 1)

    def _remove(index: int) -> None:
        route = routes[index]
        if not route.saved:
            routes.pop(index)
            state["selected"] = max(0, index - 1)
            _route_workspace.refresh()
            return
        _confirm_remove(route, index)

    def _confirm_remove(route: RouteDraft, index: int) -> None:
        with ui.dialog() as dialog, ui.card().classes("w-96 gap-2"):
            ui.label(f'Remove "{route.name}"?').classes("text-lg font-semibold")
            ui.label(
                "Its API key is cleared from this app."
                if route.kind == "builtin"
                else "Its endpoint, model, and API key are deleted from this app."
            ).classes("text-sm text-slate-600")

            def _confirm() -> None:
                routes.pop(index)
                state["selected"] = max(0, index - 1)
                new_settings = _build_settings()
                if new_settings is not None:
                    _persist(new_settings)
                dialog.close()
                _route_workspace.refresh()
                ui.notify(f'Removed "{route.name}"', type="positive")

            with ui.row().classes("w-full justify-end gap-2 mt-2"):
                ui.button("Cancel", on_click=dialog.close).props("flat")
                ui.button("Remove", on_click=_confirm, icon="delete").props(
                    "color=negative"
                )
        dialog.open()

    def _build_settings() -> Settings | None:
        """Collect every field into a Settings, or notify and return None."""
        active = routes[state["selected"]] if routes else None

        image_key = image_env_key_for(image_model_select.value or settings.image_model)
        api_keys = dict(settings.api_keys)
        present_env = {
            PROVIDERS[r.name]["env_key"] for r in routes if r.kind == "builtin"
        }
        for env in _PROVIDER_ENV_KEYS:
            if env not in present_env and env != image_key:
                api_keys.pop(env, None)

        custom_providers: dict[str, CustomProvider] = {}
        seen: set[str] = set()
        for route in routes:
            if route.kind == "custom" and not route.name:
                if route is active:
                    ui.notify("Name this custom endpoint first", type="warning")
                    return None
                continue  # unnamed draft the user left behind — skip it
            if route.kind == "custom" and route.name in PROVIDERS:
                ui.notify(f'"{route.name}" is a reserved provider name', type="warning")
                return None
            if route.name in seen:
                ui.notify(f'Two routes are both named "{route.name}"', type="warning")
                return None
            seen.add(route.name)
            if route.kind == "builtin":
                env = PROVIDERS[route.name]["env_key"]
                if route.api_key:
                    api_keys[env] = route.api_key
                elif env != image_key:
                    api_keys.pop(env, None)
            else:
                custom_providers[route.name] = CustomProvider(
                    base_url=route.base_url,
                    model=route.model,
                    api_key=route.api_key,
                )

        api_keys["GOOGLE_TTS_KEY"] = tts_key_input.value or ""
        if image_api_key_input.value:
            api_keys[image_key] = image_api_key_input.value

        if active is None:
            provider, text_model, base_url = "OpenAI", Settings().text_model, ""
        else:
            provider = active.name
            text_model = active.model
            base_url = active.base_url if active.kind == "custom" else ""

        return Settings(
            provider=provider,
            text_model=text_model,
            image_provider=image_provider_select.value
            or image_provider_for(image_model_select.value or ""),
            image_model=image_model_select.value or "",
            image_size=settings.image_size,
            custom_base_url=base_url,
            api_keys=api_keys,
            custom_providers=custom_providers,
            defaults=DefaultsConfig(
                native_language=native_select.value or "",
                target_language=target_select.value or "",
                generate_image=bool(generate_image_switch.value),
            ),
        )

    def _persist(new_settings: Settings) -> None:
        nonlocal settings
        for env in _PROVIDER_ENV_KEYS:
            if not new_settings.api_keys.get(env):
                os.environ.pop(env, None)
        save_settings(new_settings)
        apply_env(new_settings)
        ui.context.client.storage["settings"] = new_settings
        settings = new_settings

    def _save() -> None:
        new_settings = _build_settings()
        if new_settings is None:
            return
        _persist(new_settings)
        for route in routes:
            route.saved = route.kind == "custom" or bool(route.api_key)
        _route_workspace.refresh()
        ui.notify("Settings saved", type="positive")

    @ui.refreshable
    def _route_workspace() -> None:
        if not routes:  # user removed the last route — fall back to a default
            first = _ADDABLE_PROVIDERS[0]
            routes.append(
                RouteDraft(
                    kind="builtin", name=first, model=get_provider_models(first)[0]
                )
            )
        selected = max(0, min(state["selected"], len(routes) - 1))
        state["selected"] = selected
        route = routes[selected]

        with ui.row().classes("route-rack"):
            for index, item in enumerate(routes):
                classes = "route-pill"
                if index == selected:
                    classes += " route-pill--active"
                with (
                    ui.element("button")
                    .classes(classes)
                    .on("click", lambda *_, index=index: _select(index))
                ):
                    ui.icon("dns" if item.kind == "custom" else "hub").classes(
                        "text-sm"
                    )
                    ui.label(item.name or "New endpoint")
                    if not item.saved:
                        ui.label("draft").classes("route-pill__tag")

            with ui.button(icon="add").props("flat round dense").classes("route-add"):
                ui.tooltip("Add provider")
                with ui.menu():
                    remaining = [
                        n
                        for n in _ADDABLE_PROVIDERS
                        if all(r.name != n for r in routes)
                    ]
                    for name in remaining:
                        ui.menu_item(
                            name, on_click=lambda *_, name=name: _add_builtin(name)
                        )
                    if remaining:
                        ui.separator()
                    ui.menu_item("Custom endpoint…", on_click=_add_custom)

        with ui.column().classes("route-editor"):
            is_builtin = route.kind == "builtin"
            base_input: ui.input | None = None

            if not is_builtin:
                name_input = ui.input(
                    label="Name",
                    placeholder="e.g. Alibaba Cloud",
                    value=route.name,
                ).classes("w-full")
                name_input.on_value_change(
                    lambda e: setattr(route, "name", (e.value or "").strip())
                )
                base_input = ui.input(
                    label="Base URL",
                    placeholder="https://your-endpoint.example.com/v1",
                    value=route.base_url,
                ).classes("w-full")
                base_input.on_value_change(
                    lambda e: setattr(route, "base_url", (e.value or "").strip())
                )

            if is_builtin:
                model_options = get_provider_models(route.name)
            else:
                model_options = [route.model] if route.model else []
            if route.model and route.model not in model_options:
                model_options = [route.model, *model_options]

            with ui.row().classes("route-model-row w-full items-center gap-2"):
                model_select = ui.select(
                    label="Model",
                    options=model_options,
                    value=route.model or (model_options[0] if model_options else None),
                    with_input=True,
                    new_value_mode="add-unique",
                ).classes("flex-1 min-w-0")
                model_select.on_value_change(
                    lambda e: setattr(route, "model", e.value or "")
                )
                fetch_btn = (
                    ui.button(icon="sync")
                    .props("flat dense")
                    .classes("route-fetch-btn")
                )
                with fetch_btn:
                    ui.tooltip("Fetch the model list from the provider")

            key_input = ui.input(
                label=PROVIDERS[route.name]["env_key"] if is_builtin else "API key",
                placeholder="sk-…",
                password=True,
                password_toggle_button=True,
                value=route.api_key,
            ).classes("w-full")
            key_input.on_value_change(
                lambda e: setattr(route, "api_key", e.value or "")
            )

            async def _fetch_models(
                *, _route: RouteDraft = route, _base: ui.input | None = base_input
            ) -> None:
                key = (key_input.value or "").strip()
                if not key:
                    ui.notify("Enter the API key first", type="warning")
                    return
                if _route.kind == "builtin":
                    info = PROVIDERS[_route.name]
                    provider, prefix, api_base = (
                        info["litellm_provider"],
                        info["model_prefix"],
                        info["api_base"],
                    )
                else:
                    api_base = ((_base.value if _base else "") or "").strip()
                    if not api_base:
                        ui.notify("Enter the Base URL first", type="warning")
                        return
                    provider, prefix = "openai", None

                fetch_btn.props("loading")
                fetch_btn.update()
                try:
                    ids = await fetch_model_ids(
                        litellm_provider=provider,
                        api_base=api_base,
                        api_key=key,
                        model_prefix=prefix,
                    )
                except (httpx.HTTPError, ValueError) as exc:
                    ui.notify(
                        f"Couldn't fetch models: {format_error(exc)}", type="negative"
                    )
                    return
                finally:
                    fetch_btn.props(remove="loading")
                    fetch_btn.update()

                if not ids:
                    ui.notify("The provider returned no models", type="warning")
                    return
                current = model_select.value
                options = ids if not current or current in ids else [current, *ids]
                model_select.set_options(options, value=current or ids[0])
                _route.model = model_select.value or ""
                ui.notify(f"Loaded {len(ids)} models", type="positive")

            fetch_btn.on("click", _fetch_models)

            ui.label(_route_hint(route)).classes("text-xs text-slate-500 pt-1")
            with ui.row().classes("w-full justify-between items-center"):
                ui.button(
                    "Remove", icon="delete", on_click=lambda: _remove(selected)
                ).props("flat dense no-caps color=negative")
                ui.button("Save provider", icon="save", on_click=_save).props(
                    "unelevated no-caps"
                ).classes("route-save-btn")

    with ui.column().classes("w-full max-w-3xl mx-auto p-6 md:p-8 gap-7"):
        ui.label("Settings").classes("settings-title")

        with ui.column().classes("gap-1"):
            ui.label("Generation route").classes("settings-eyebrow")
            ui.label("Where card text is generated").classes("settings-h2")
            ui.label(
                "Pick the active provider. Add the ones you have a key for; "
                "everything else stays hidden."
            ).classes("text-sm text-slate-500")

        _route_workspace()

        # -- Image Model ------------------------------------------------------------
        _section("Image Generation")

        image_provider = (
            settings.image_provider
            if settings.image_provider in IMAGE_PROVIDERS
            else image_provider_for(settings.image_model)
        )

        image_provider_select = ui.select(
            label="Image Provider",
            options=list(IMAGE_PROVIDERS.keys()),
            value=image_provider,
        ).classes("w-full")

        def _image_model_options(provider: str) -> list[str]:
            models = get_image_provider_models(provider)
            if settings.image_model and settings.image_model not in models:
                models = [*models, settings.image_model]
            return models

        with ui.row().classes("route-model-row w-full items-center gap-2"):
            image_model_select = ui.select(
                label="Image Model",
                options=_image_model_options(image_provider),
                value=settings.image_model,
                new_value_mode="add-unique",
            ).classes("flex-1 min-w-0")
            image_fetch_btn = (
                ui.button(icon="sync").props("flat dense").classes("route-fetch-btn")
            )
            with image_fetch_btn:
                ui.tooltip("Fetch the model list from the provider")

        def _image_env_key() -> str:
            return image_env_key_for(image_model_select.value or settings.image_model)

        image_api_key_input = ui.input(
            label=_image_env_key(),
            placeholder="Leave blank to reuse a key from the generation route above",
            password=True,
            password_toggle_button=True,
            value=settings.api_keys.get(_image_env_key(), ""),
        ).classes("w-full")

        def _sync_image_key_field() -> None:
            key = _image_env_key()
            image_api_key_input.label = key
            image_api_key_input.value = settings.api_keys.get(key, "")
            image_api_key_input.update()

        async def _fetch_image_models() -> None:
            key = (image_api_key_input.value or "").strip()
            if not key:
                ui.notify("Enter the API key first", type="warning")
                return
            info = IMAGE_PROVIDERS[image_provider_select.value]

            image_fetch_btn.props("loading")
            image_fetch_btn.update()
            try:
                ids = await fetch_image_model_ids(
                    litellm_provider=info["litellm_provider"],
                    api_base=info["api_base"],
                    api_key=key,
                    model_prefix=info["model_prefix"],
                )
            except (httpx.HTTPError, ValueError) as exc:
                ui.notify(
                    f"Couldn't fetch models: {format_error(exc)}", type="negative"
                )
                return
            finally:
                image_fetch_btn.props(remove="loading")
                image_fetch_btn.update()

            if not ids:
                ui.notify("The provider returned no image models", type="warning")
                return
            current = image_model_select.value
            options = ids if not current or current in ids else [current, *ids]
            image_model_select.set_options(options, value=current or ids[0])
            ui.notify(f"Loaded {len(ids)} image models", type="positive")

        image_fetch_btn.on("click", _fetch_image_models)

        def _on_image_provider_change() -> None:
            models = _image_model_options(image_provider_select.value)
            current = image_model_select.value
            image_model_select.set_options(models)
            image_model_select.value = current if current in models else models[0]
            _sync_image_key_field()

        image_provider_select.on_value_change(lambda _: _on_image_provider_change())
        image_model_select.on_value_change(lambda _: _sync_image_key_field())

        # -- TTS (Google Cloud) -----------------------------------------------------
        _section("Text-to-Speech (Google Cloud)")

        tts_key_input = ui.input(
            label="Google TTS API Key",
            placeholder="Your Google Cloud API key for TTS",
            password=True,
            password_toggle_button=True,
            value=settings.api_keys.get("GOOGLE_TTS_KEY", ""),
        ).classes("w-full")

        # -- Defaults ---------------------------------------------------------------
        _section("Defaults")

        language_options = [lang.value for lang in Language]

        native_select = ui.select(
            label="Native Language",
            options=language_options,
            value=settings.defaults.native_language,
        ).classes("w-full")

        target_select = ui.select(
            label="Target Language",
            options=language_options,
            value=settings.defaults.target_language,
        ).classes("w-full")

        generate_image_switch = ui.switch(
            "Generate images by default",
            value=settings.defaults.generate_image,
        )

        # -- Save -----------------------------------------------------------------
        ui.separator()
        ui.button("Save settings", on_click=_save, icon="save").props(
            "unelevated"
        ).classes("w-full settings-save")


def _section(title: str) -> None:
    """Render a section heading."""
    ui.label(title).classes("text-lg font-semibold text-primary mt-2")


def _settings_styles() -> None:
    """Small design system for the settings page."""
    ui.add_css(
        """
        .settings-title {
            color: #0f172a;
            font-size: 1.75rem;
            font-weight: 800;
            letter-spacing: -.02em;
        }
        .settings-eyebrow {
            color: #64748b;
            font-size: .72rem;
            font-weight: 700;
            letter-spacing: .11em;
            text-transform: uppercase;
        }
        .settings-h2 {
            color: #0f172a;
            font-size: 1.15rem;
            font-weight: 600;
        }
        .route-rack {
            align-items: center;
            flex-wrap: wrap;
            gap: .4rem;
        }
        .route-pill {
            -webkit-appearance: none;
            appearance: none;
            align-items: center;
            background: #fff;
            font: inherit;
            border: 1px solid #cbd5e1;
            border-radius: 999px;
            color: #334155;
            cursor: pointer;
            display: inline-flex;
            font-size: .82rem;
            font-weight: 600;
            gap: .4rem;
            padding: .4rem .85rem;
        }
        .route-pill:hover {
            background: #eff6ff;
            border-color: #60a5fa;
        }
        .route-pill:focus-visible {
            outline: 2px solid #2563eb;
            outline-offset: 2px;
        }
        .route-pill--active,
        .route-pill--active:hover {
            background: #2563eb;
            border-color: #2563eb;
            color: #fff;
        }
        .route-pill__tag {
            background: rgba(148, 163, 184, .28);
            border-radius: 5px;
            font-size: .6rem;
            font-weight: 800;
            letter-spacing: .08em;
            padding: .05rem .3rem;
            text-transform: uppercase;
        }
        .route-add {
            border: 1px dashed #93c5fd !important;
            color: #2563eb !important;
        }
        .route-editor {
            background: #f8fafc;
            border: 1px solid #e2e8f0;
            border-radius: 14px;
            gap: .9rem;
            margin-top: .4rem;
            padding: 1.1rem;
            width: 100%;
        }
        .route-model-row {
            flex-wrap: nowrap;
        }
        .route-fetch-btn {
            flex: 0 0 auto;
        }
        .route-save-btn {
            border-radius: 8px;
        }
        .settings-save {
            border-radius: 10px;
            min-height: 2.7rem;
        }
        @media (prefers-reduced-motion: no-preference) {
            .route-pill { transition: background-color .16s ease, border-color .16s ease; }
        }
        .body--dark .settings-title,
        .body--dark .settings-h2 { color: #f1f5f9; }
        .body--dark .route-pill {
            background: #1e293b;
            border-color: #334155;
            color: #cbd5e1;
        }
        .body--dark .route-pill:hover { background: #1e3a5f; }
        .body--dark .route-editor {
            background: #0f172a;
            border-color: #1e293b;
        }
        """
    )
