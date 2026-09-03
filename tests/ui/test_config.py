"""Tests for GUI configuration helpers."""

import pytest

from ankinote.ui.config import DEFAULT_IMAGE_ENV_KEY, image_env_key_for


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
