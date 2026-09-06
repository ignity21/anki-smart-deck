"""Tests for the STEM generation page helpers."""

import pytest
from pydantic import ValidationError

from ankinote.collections.stem.models import ExampleModel, FormulaModel
from ankinote.services.ai import LiteLLMTextService
from ankinote.ui.config import CUSTOM_VENDOR, PROVIDERS, ProviderProfile, Settings
from ankinote.ui.pages.stem import _build_text_service, _edited_card


def test_formula_editor_validates_and_rebuilds_variable_rows():
    model = FormulaModel(
        front="Law?",
        latex="F=ma",
        meaning="Force",
        variables=[],
        conditions="",
        derivation="",
        tags=["Physics"],
    )
    edited = _edited_card(
        model,
        {
            "latex": " E=mc^2 ",
            "variable_2_symbol": "E",
            "variable_2_description": "Energy",
            "tags": "Physics, Relativity",
            "image_description": " mass and energy ",
        },
    )
    assert edited.latex == "E=mc^2"
    assert edited.variables[0].description == "Energy"
    assert edited.tags == ["Physics", "Relativity"]
    assert edited.image_description == "mass and energy"
    assert model.variables == []


def test_example_editor_preserves_steps_and_rejects_empty_answer():
    model = ExampleModel(
        front="Solve x+1=2",
        answer="1",
        steps=["Subtract one."],
        explanation="",
        tags=["Math"],
    )
    edited = _edited_card(model, {"steps": "Subtract one.\nCheck x=1."})
    assert edited.steps == ["Subtract one.", "Check x=1."]
    with pytest.raises(ValidationError):
        _edited_card(model, {"answer": "  "})
    with pytest.raises(ValidationError):
        _edited_card(model, {"steps": "  "})


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
