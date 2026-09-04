"""Tests for the settings page route-list helpers."""

from ankinote.ui.config import IMAGE_PROVIDERS, PROVIDERS, CustomProvider, Settings
from ankinote.ui.pages.settings import (
    _ADDABLE_PROVIDERS,
    _IMAGE_ADDABLE_PROVIDERS,
    _image_routes_from_settings,
    _route_hint,
    _routes_from_settings,
)


def test_addable_providers_are_the_gui_managed_ones() -> None:
    # DeepSeek and other litellm providers go through "Custom endpoint" instead.
    assert "DeepSeek" not in _ADDABLE_PROVIDERS
    assert {"OpenAI", "Anthropic", "Google", "xAI"} <= set(_ADDABLE_PROVIDERS)


def test_routes_from_fresh_settings_shows_only_the_active_provider() -> None:
    routes = _routes_from_settings(Settings())
    assert [(r.name, r.kind, r.saved) for r in routes] == [("OpenAI", "builtin", False)]


def test_routes_hide_builtins_without_a_key() -> None:
    settings = Settings(
        provider="Anthropic",
        text_model="claude-x",
        api_keys={"ANTHROPIC_API_KEY": "sk-a", "GOOGLE_TTS_KEY": "t"},
    )
    routes = _routes_from_settings(settings)
    assert [r.name for r in routes] == ["Anthropic"]
    assert routes[0].saved and routes[0].model == "claude-x"


def test_routes_include_keyed_builtins_and_custom_profiles() -> None:
    settings = Settings(
        provider="OpenAI",
        api_keys={"OPENAI_API_KEY": "sk-o", "ANTHROPIC_API_KEY": "sk-a"},
        custom_providers={
            "Local vLLM": CustomProvider(base_url="http://x/v1", model="m", api_key="k")
        },
    )
    routes = _routes_from_settings(settings)
    names = [r.name for r in routes]
    assert names == ["OpenAI", "Anthropic", "Local vLLM"]
    assert all(r.saved for r in routes)
    assert routes[-1].kind == "custom"


def test_route_hint_describes_kind() -> None:
    (builtin,) = _routes_from_settings(Settings())
    assert _route_hint(builtin, PROVIDERS) == "Built-in route · openai"

    custom = _routes_from_settings(
        Settings(custom_providers={"X": CustomProvider(base_url="http://h/v1")})
    )[-1]
    assert _route_hint(custom, PROVIDERS) == "http://h/v1"


def test_image_addable_providers_are_the_gui_managed_ones() -> None:
    assert set(_IMAGE_ADDABLE_PROVIDERS) == {"OpenAI", "Google", "xAI"}


def test_image_routes_from_fresh_settings_shows_only_the_active_provider() -> None:
    routes = _image_routes_from_settings(Settings())
    assert [(r.name, r.kind, r.saved) for r in routes] == [("Google", "builtin", False)]


def test_image_routes_hide_builtins_without_a_key() -> None:
    settings = Settings(
        image_provider="xAI",
        image_model="xai/grok-2-image",
        api_keys={"XAI_API_KEY": "sk-x"},
    )
    routes = _image_routes_from_settings(settings)
    assert [r.name for r in routes] == ["xAI"]
    assert routes[0].saved and routes[0].model == "xai/grok-2-image"


def test_image_routes_include_every_keyed_builtin() -> None:
    settings = Settings(
        image_provider="OpenAI",
        api_keys={"OPENAI_API_KEY": "sk-o", "GEMINI_API_KEY": "sk-g"},
    )
    routes = _image_routes_from_settings(settings)
    assert [r.name for r in routes] == ["OpenAI", "Google"]
    assert all(r.saved for r in routes)
    assert all(r.kind == "builtin" for r in routes)


def test_image_route_hint_matches_builtin_provider() -> None:
    (builtin,) = _image_routes_from_settings(Settings())
    assert _route_hint(builtin, IMAGE_PROVIDERS) == "Built-in route · gemini"
