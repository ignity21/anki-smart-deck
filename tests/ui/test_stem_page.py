"""Tests for the STEM generation page helpers."""

from ankinote.services.ai import LiteLLMTextService
from ankinote.ui.config import CUSTOM_API_KEY_STORAGE_KEY, CUSTOM_PROVIDER, Settings
from ankinote.ui.pages.stem import _build_text_service


def test_build_text_service_plain_for_builtin_provider() -> None:
    service = _build_text_service(Settings(provider="OpenAI", text_model="gpt-4o"))
    assert isinstance(service, LiteLLMTextService)
    assert service._api_base is None


def test_build_text_service_uses_named_custom_profile() -> None:
    from ankinote.ui.config import CustomProvider

    settings = Settings(
        provider="My LLM",
        custom_providers={
            "My LLM": CustomProvider(
                base_url="https://example.test/v1",
                model="llama-3.1-70b",
                api_key="sk-abc",
            )
        },
    )
    service = _build_text_service(settings)
    assert service._api_base == "https://example.test/v1"
    assert service._api_key == "sk-abc"


def test_build_text_service_falls_back_to_legacy_custom_fields() -> None:
    settings = Settings(
        provider=CUSTOM_PROVIDER,
        text_model="local-model",
        custom_base_url="http://localhost:1234/v1",
        api_keys={CUSTOM_API_KEY_STORAGE_KEY: "sk-legacy"},
    )
    service = _build_text_service(settings)
    assert service._api_base == "http://localhost:1234/v1"
    assert service._api_key == "sk-legacy"
