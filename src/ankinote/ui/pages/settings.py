"""Settings page — LLM provider, TTS, and default language preferences."""

import os
from collections.abc import Awaitable, Callable
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
    image_provider_for,
    load_settings,
    save_settings,
)
from ankinote.ui.pages.word import format_error

# Providers offered in the "Add provider" menus, in display order. Anything
# not on these lists can still be reached through "Custom endpoint" (text
# generation only — image providers stay built-in-only for now).
_ADDABLE_PROVIDERS: tuple[str, ...] = tuple(PROVIDERS.keys())
_IMAGE_ADDABLE_PROVIDERS: tuple[str, ...] = tuple(IMAGE_PROVIDERS.keys())

_PROVIDER_ENV_KEYS: frozenset[str] = frozenset(
    info["env_key"] for info in PROVIDERS.values()
)
_IMAGE_ENV_KEYS: frozenset[str] = frozenset(
    info["env_key"] for info in IMAGE_PROVIDERS.values()
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
    """Build the editable text-route list: configured built-ins first, then customs.

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


def _image_routes_from_settings(settings: Settings) -> list[RouteDraft]:
    """Build the editable image-route list, mirroring ``_routes_from_settings``."""
    resolved_provider = (
        settings.image_provider
        if settings.image_provider in IMAGE_PROVIDERS
        else image_provider_for(settings.image_model)
    )
    routes: list[RouteDraft] = []
    for name, info in IMAGE_PROVIDERS.items():
        key = settings.api_keys.get(info["env_key"], "")
        if not key and name != resolved_provider:
            continue
        routes.append(
            RouteDraft(
                kind="builtin",
                name=name,
                model=settings.image_model
                if name == resolved_provider
                else get_image_provider_models(name)[0],
                api_key=key,
                saved=bool(key),
            )
        )
    if not routes:
        first = _IMAGE_ADDABLE_PROVIDERS[0]
        routes.append(
            RouteDraft(
                kind="builtin", name=first, model=get_image_provider_models(first)[0]
            )
        )
    return routes


def _route_hint(route: RouteDraft, builtin_providers: dict[str, dict]) -> str:
    """One-line description shown under a route editor."""
    if route.kind == "custom":
        return route.base_url or "OpenAI-compatible endpoint"
    return f"Built-in route · {builtin_providers[route.name]['litellm_provider']}"


class RouteRack:
    """A pill rack of saved provider routes plus an editor for the active one.

    Shared by the text- and image-generation sections so both offer the exact
    same add/select/fetch/remove/save interaction — only the provider catalog,
    model lookup, and whether custom endpoints are allowed differ.
    """

    def __init__(
        self,
        *,
        builtin_providers: dict[str, dict],
        get_model_options: Callable[[str], list[str]],
        fetch_ids: Callable[..., Awaitable[list[str]]],
        allow_custom: bool,
        routes: list[RouteDraft],
        selected: int,
        on_save: Callable[[], None],
        on_removed: Callable[[], None],
        fetched_noun: str = "models",
    ) -> None:
        self.builtin_providers = builtin_providers
        self.addable: tuple[str, ...] = tuple(builtin_providers.keys())
        self.get_model_options = get_model_options
        self.fetch_ids = fetch_ids
        self.allow_custom = allow_custom
        self.routes = routes
        self.state: dict = {"selected": selected}
        self.on_save = on_save
        self.on_removed = on_removed
        self.fetched_noun = fetched_noun

    def select(self, index: int) -> None:
        self.state["selected"] = index
        self.workspace.refresh()

    def add_builtin(self, name: str) -> None:
        existing = next((i for i, r in enumerate(self.routes) if r.name == name), None)
        if existing is None:
            self.routes.append(
                RouteDraft(
                    kind="builtin", name=name, model=self.get_model_options(name)[0]
                )
            )
            existing = len(self.routes) - 1
        self.select(existing)

    def add_custom(self) -> None:
        self.routes.append(RouteDraft(kind="custom", name=""))
        self.select(len(self.routes) - 1)

    def remove(self, index: int) -> None:
        route = self.routes[index]
        if not route.saved:
            self.routes.pop(index)
            self.state["selected"] = max(0, index - 1)
            self.workspace.refresh()
            return
        self._confirm_remove(route, index)

    def _confirm_remove(self, route: RouteDraft, index: int) -> None:
        with ui.dialog() as dialog, ui.card().classes("w-96 gap-2"):
            ui.label(f'Remove "{route.name}"?').classes("text-lg font-semibold")
            ui.label(
                "Its API key is cleared from this app."
                if route.kind == "builtin"
                else "Its endpoint, model, and API key are deleted from this app."
            ).classes("text-sm text-slate-600")

            def _confirm() -> None:
                self.routes.pop(index)
                self.state["selected"] = max(0, index - 1)
                self.on_removed()
                dialog.close()
                self.workspace.refresh()
                ui.notify(f'Removed "{route.name}"', type="positive")

            with ui.row().classes("w-full justify-end gap-2 mt-2"):
                ui.button("Cancel", on_click=dialog.close).props("flat")
                ui.button("Remove", on_click=_confirm, icon="delete").props(
                    "color=negative"
                )
        dialog.open()

    @ui.refreshable_method
    def workspace(self) -> None:
        if not self.routes:  # user removed the last route — fall back to a default
            first = self.addable[0]
            self.routes.append(
                RouteDraft(
                    kind="builtin", name=first, model=self.get_model_options(first)[0]
                )
            )
        selected = max(0, min(self.state["selected"], len(self.routes) - 1))
        self.state["selected"] = selected
        route = self.routes[selected]

        with ui.row().classes("route-rack"):
            for index, item in enumerate(self.routes):
                classes = "route-pill"
                if index == selected:
                    classes += " route-pill--active"
                with (
                    ui.element("button")
                    .classes(classes)
                    .on("click", lambda *_, index=index: self.select(index))
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
                        n for n in self.addable if all(r.name != n for r in self.routes)
                    ]
                    for name in remaining:
                        ui.menu_item(
                            name, on_click=lambda *_, name=name: self.add_builtin(name)
                        )
                    if self.allow_custom:
                        if remaining:
                            ui.separator()
                        ui.menu_item("Custom endpoint…", on_click=self.add_custom)

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
                model_options = self.get_model_options(route.name)
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
                label=self.builtin_providers[route.name]["env_key"]
                if is_builtin
                else "API key",
                placeholder="sk-…",
                password=True,
                password_toggle_button=True,
                value=route.api_key,
            ).classes("w-full")
            key_input.on_value_change(
                lambda e: setattr(route, "api_key", e.value or "")
            )

            async def _fetch(
                *, _route: RouteDraft = route, _base: ui.input | None = base_input
            ) -> None:
                key = (key_input.value or "").strip()
                if not key:
                    ui.notify("Enter the API key first", type="warning")
                    return
                if _route.kind == "builtin":
                    info = self.builtin_providers[_route.name]
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
                    ids = await self.fetch_ids(
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
                    ui.notify(
                        f"The provider returned no {self.fetched_noun}", type="warning"
                    )
                    return
                current = model_select.value
                options = ids if not current or current in ids else [current, *ids]
                model_select.set_options(options, value=current or ids[0])
                _route.model = model_select.value or ""
                ui.notify(f"Loaded {len(ids)} {self.fetched_noun}", type="positive")

            fetch_btn.on("click", _fetch)

            ui.label(_route_hint(route, self.builtin_providers)).classes(
                "text-xs text-slate-500 pt-1"
            )
            with ui.row().classes("w-full justify-between items-center"):
                ui.button(
                    "Remove", icon="delete", on_click=lambda: self.remove(selected)
                ).props("flat dense no-caps color=negative")
                ui.button("Save provider", icon="save", on_click=self.on_save).props(
                    "unelevated no-caps"
                ).classes("route-save-btn")


def settings_page() -> None:
    """Render the settings page."""

    _settings_styles()

    settings: Settings = ui.context.client.storage.get("settings") or load_settings()

    def _build_settings() -> Settings | None:
        """Collect every field into a Settings, or notify and return None."""
        active_text = (
            text_rack.routes[text_rack.state["selected"]] if text_rack.routes else None
        )
        active_image = (
            image_rack.routes[image_rack.state["selected"]]
            if image_rack.routes
            else None
        )

        builtin_routes: list[tuple[RouteDraft, str]] = [
            (r, PROVIDERS[r.name]["env_key"])
            for r in text_rack.routes
            if r.kind == "builtin"
        ] + [
            (r, IMAGE_PROVIDERS[r.name]["env_key"])
            for r in image_rack.routes
            if r.kind == "builtin"
        ]
        present_env = {env for _, env in builtin_routes}
        env_values = {env: r.api_key for r, env in builtin_routes if r.api_key}

        api_keys = dict(settings.api_keys)
        for env in _PROVIDER_ENV_KEYS | _IMAGE_ENV_KEYS:
            if env not in present_env:
                api_keys.pop(env, None)
        for env in present_env:
            if env in env_values:
                api_keys[env] = env_values[env]
            else:
                api_keys.pop(env, None)

        custom_providers: dict[str, CustomProvider] = {}
        seen: set[str] = set()
        for route in text_rack.routes:
            if route.kind == "custom" and not route.name:
                if route is active_text:
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
            if route.kind == "custom":
                custom_providers[route.name] = CustomProvider(
                    base_url=route.base_url,
                    model=route.model,
                    api_key=route.api_key,
                )

        api_keys["GOOGLE_TTS_KEY"] = tts_key_input.value or ""

        if active_text is None:
            provider, text_model, base_url = "OpenAI", Settings().text_model, ""
        else:
            provider = active_text.name
            text_model = active_text.model
            base_url = active_text.base_url if active_text.kind == "custom" else ""

        if active_image is None:
            image_provider, image_model = (
                Settings().image_provider,
                Settings().image_model,
            )
        else:
            image_provider = active_image.name
            image_model = active_image.model

        return Settings(
            provider=provider,
            text_model=text_model,
            image_provider=image_provider,
            image_model=image_model,
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
        for env in _PROVIDER_ENV_KEYS | _IMAGE_ENV_KEYS:
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
        for route in text_rack.routes:
            route.saved = route.kind == "custom" or bool(route.api_key)
        for route in image_rack.routes:
            route.saved = bool(route.api_key)
        text_rack.workspace.refresh()
        image_rack.workspace.refresh()
        ui.notify("Settings saved", type="positive")

    def _persist_after_removal() -> None:
        new_settings = _build_settings()
        if new_settings is not None:
            _persist(new_settings)

    text_routes = _routes_from_settings(settings)
    text_rack = RouteRack(
        builtin_providers=PROVIDERS,
        get_model_options=get_provider_models,
        fetch_ids=fetch_model_ids,
        allow_custom=True,
        routes=text_routes,
        selected=next(
            (i for i, r in enumerate(text_routes) if r.name == settings.provider), 0
        ),
        on_save=_save,
        on_removed=_persist_after_removal,
        fetched_noun="models",
    )

    image_routes = _image_routes_from_settings(settings)
    image_rack = RouteRack(
        builtin_providers=IMAGE_PROVIDERS,
        get_model_options=get_image_provider_models,
        fetch_ids=fetch_image_model_ids,
        allow_custom=False,
        routes=image_routes,
        selected=next(
            (i for i, r in enumerate(image_routes) if r.name == settings.image_provider),
            0,
        ),
        on_save=_save,
        on_removed=_persist_after_removal,
        fetched_noun="image models",
    )

    with ui.column().classes("w-full max-w-3xl mx-auto p-6 md:p-8 gap-7"):
        ui.label("Settings").classes("settings-title")

        with ui.column().classes("gap-1"):
            ui.label("Generation route").classes("settings-eyebrow")
            ui.label("Where card text is generated").classes("settings-h2")
            ui.label(
                "Pick the active provider. Add the ones you have a key for; "
                "everything else stays hidden."
            ).classes("text-sm text-slate-500")

        text_rack.workspace()

        # -- Image Model ------------------------------------------------------------
        with ui.column().classes("gap-1 mt-2"):
            ui.label("Image route").classes("settings-eyebrow")
            ui.label("Where card images are generated").classes("settings-h2")
            ui.label(
                "Pick the active provider. Add the ones you have a key for; "
                "everything else stays hidden."
            ).classes("text-sm text-slate-500")

        image_rack.workspace()

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
