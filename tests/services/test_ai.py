"""Tests for the shared AI service layer."""

from types import SimpleNamespace

import pytest
from pytest_mock import MockerFixture

from ankinote.services.ai import LiteLLMGeminiImageService, LiteLLMTextService


@pytest.mark.asyncio
async def test_litellm_text_service_forwards_completion_args(
    mocker: MockerFixture,
):
    completion = mocker.patch(
        "ankinote.services.ai.acompletion",
        return_value=SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(content='{"ok": true}'),
                )
            ]
        ),
    )

    service = LiteLLMTextService()
    result = await service.generate_text(
        model_id="deepseek/deepseek-v4-flash",
        messages=[{"role": "user", "content": "hello"}],
        temperature=0.2,
    )

    assert result == '{"ok": true}'
    completion.assert_awaited_once_with(
        model="deepseek/deepseek-v4-flash",
        messages=[{"role": "user", "content": "hello"}],
        stream=False,
        temperature=0.2,
        drop_params=True,
    )


@pytest.mark.asyncio
async def test_litellm_text_service_rejects_non_string_content(
    mocker: MockerFixture,
):
    mocker.patch(
        "ankinote.services.ai.acompletion",
        return_value=SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=None))]
        ),
    )

    service = LiteLLMTextService()

    with pytest.raises(RuntimeError, match="non-string"):
        await service.generate_text(
            model_id="deepseek/deepseek-v4-flash",
            messages=[{"role": "user", "content": "hello"}],
            temperature=0.2,
        )


@pytest.mark.asyncio
async def test_litellm_gemini_image_service_decodes_and_resizes(
    mocker: MockerFixture,
):
    image_generation = mocker.patch(
        "ankinote.services.ai.aimage_generation",
        return_value=SimpleNamespace(data=[SimpleNamespace(b64_json="aW1hZ2UtYnl0ZXM=")]),
    )
    resize = mocker.patch(
        "ankinote.services.ai.resize_to_square",
        return_value=b"resized-image",
    )

    service = LiteLLMGeminiImageService(model_id="gemini/gemini-2.5-flash-image", image_size=128)
    result = await service.generate_image(prompt="draw a cat")

    assert result == b"resized-image"
    image_generation.assert_awaited_once_with(
        model="gemini/gemini-2.5-flash-image",
        prompt="draw a cat",
    )
    resize.assert_called_once_with(b"image-bytes", 128)
