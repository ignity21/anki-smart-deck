"""Tests for the STEM generation page helpers."""

from ankinote.services.ai import LiteLLMTextService
from ankinote.ui.config import CUSTOM_VENDOR, PROVIDERS, ProviderProfile, Settings
from ankinote.ui.pages.stem import _build_text_service


def test_build_text_service_passes_builtin_vendor_key_and_base_explicitly() -> None:
    """Every profile — not just custom ones — carries its own api_base/api_key
    explicitly now, so multiple accounts of the same vendor can coexist."""
    settings = Settings(
        text_providers={
            "OpenAI (work)": ProviderProfile(
                vendor="OpenAI",
                model="gpt-4o",
                base_url=PROVIDERS["OpenAI"]["api_base"],
                api_key="sk-work",
            )
        },
        active_text_provider="OpenAI (work)",
    )
    service = _build_text_service(settings)
    assert isinstance(service, LiteLLMTextService)
    assert service._api_base == PROVIDERS["OpenAI"]["api_base"]
    assert service._api_key == "sk-work"
    assert service._force_openai_route is False


def test_build_text_service_forces_openai_route_for_custom_vendor() -> None:
    settings = Settings(
        text_providers={
            "My LLM": ProviderProfile(
                vendor=CUSTOM_VENDOR,
                base_url="https://example.test/v1",
                model="llama-3.1-70b",
                api_key="sk-abc",
            )
        },
        active_text_provider="My LLM",
    )
    service = _build_text_service(settings)
    assert service._api_base == "https://example.test/v1"
    assert service._api_key == "sk-abc"
    assert service._force_openai_route is True


def test_build_text_service_falls_back_when_active_provider_is_missing() -> None:
    settings = Settings(text_providers={}, active_text_provider="missing")
    service = _build_text_service(settings)
    assert service._api_base is None
    assert service._api_key is None
    assert service._force_openai_route is False
