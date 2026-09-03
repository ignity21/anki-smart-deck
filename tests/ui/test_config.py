"""Tests for GUI configuration helpers."""

import pytest

from ankinote.ui.config import (
    DEFAULT_IMAGE_ENV_KEY,
    IMAGE_PROVIDERS,
    Settings,
    get_image_provider_models,
    image_env_key_for,
    image_provider_for,
    load_settings,
    save_settings,
)


@pytest.mark.parametrize(
    ("model", "expected"),
    [
        ("gemini/gemini-3.1-flash-lite-image", "GEMINI_API_KEY"),
        ("vertex_ai/imagen-3.0", "GEMINI_API_KEY"),
        ("gpt-image-1", "OPENAI_API_KEY"),
        ("dall-e-3", "OPENAI_API_KEY"),
        ("xai/grok-2-image", "XAI_API_KEY"),
    ],
)
def test_image_env_key_for_maps_known_providers(model: str, expected: str) -> None:
    assert image_env_key_for(model) == expected


def test_image_env_key_for_falls_back_for_unknown_model() -> None:
    assert image_env_key_for("no-such-provider/whatever") == DEFAULT_IMAGE_ENV_KEY
    assert image_env_key_for("") == DEFAULT_IMAGE_ENV_KEY


@pytest.mark.parametrize(
    ("model", "expected"),
    [
        ("gemini/gemini-3.1-flash-lite-image", "Google"),
        ("gpt-image-1", "OpenAI"),
        ("dall-e-3", "OpenAI"),
        ("xai/grok-2-image", "xAI"),
        ("no-such-provider/whatever", "Google"),
    ],
)
def test_image_provider_for(model: str, expected: str) -> None:
    assert image_provider_for(model) == expected


def test_get_image_provider_models_returns_non_empty_for_each_provider() -> None:
    for provider in IMAGE_PROVIDERS:
        models = get_image_provider_models(provider)
        assert models, provider
        prefix = IMAGE_PROVIDERS[provider]["model_prefix"]
        if prefix:
            assert all(m.startswith(prefix) for m in models)
        assert all("/" not in m.removeprefix(prefix or "") for m in models)


def test_openai_image_models_include_gpt_image_1() -> None:
    assert "gpt-image-1" in get_image_provider_models("OpenAI")


def test_settings_round_trip_preserves_image_provider(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    original = Settings(image_provider="xAI", image_model="xai/grok-2-image")
    save_settings(original)
    loaded = load_settings()
    assert loaded.image_provider == "xAI"
    assert loaded.image_model == "xai/grok-2-image"


def test_load_settings_migrates_missing_image_provider(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    config_dir = tmp_path / "ankinote"
    config_dir.mkdir()
    (config_dir / "settings.json").write_text(
        '{"provider": "OpenAI", "image_model": "gpt-image-1"}', encoding="utf-8"
    )
    assert load_settings().image_provider == "OpenAI"
