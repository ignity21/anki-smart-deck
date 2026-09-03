"""Shared AI configuration and provider-backed generation services."""

import asyncio
import base64
from collections.abc import Sequence
from dataclasses import dataclass, replace
from typing import Protocol, cast

from litellm import acompletion, aimage_generation

from ankinote.utils.img import resize_to_max_edge

TextMessage = dict[str, str]
REQUEST_TIMEOUT_SECONDS = 60

# Sentinel ``reasoning_effort`` value that turns a model's extended "thinking"
# pass off.  Language card types produce short, tightly-specified JSON where
# that pass adds little but costs tokens and latency (and DeepSeek, our default
# provider, silently ignores ``temperature`` while it is on).  DeepSeek enables
# thinking by default; it is disabled through the OpenAI-format ``thinking``
# field rather than ``reasoning_effort``, which LiteLLM's DeepSeek routing drops.
# https://api-docs.deepseek.com/guides/thinking_mode
DISABLE_REASONING = "none"

# Values accepted by callers that expose a "thinking" choice (the ``--thinking``
# CLI option and the STEM generation page).  ``off`` disables the model's
# extended-thinking pass, ``default`` uses the provider default, and the named
# levels are forwarded as ``reasoning_effort``.
THINKING_CHOICES = ("off", "low", "medium", "high", "default")


def resolve_thinking(choice: str | None, *, unset: str | None) -> str | None:
    """Map a "thinking" choice to a ``reasoning_effort`` value.

    ``choice is None`` means no choice was made; the caller's built-in default
    (*unset*) applies. ``"off"`` disables extended thinking, ``"default"``
    requests the provider default, and any other value passes straight through.
    """
    if choice is None:
        return unset
    if choice == "off":
        return DISABLE_REASONING
    if choice == "default":
        return None
    return choice


@dataclass(frozen=True, slots=True)
class AIServiceConfig:
    """Centralized default AI configuration."""

    text_model: str = "deepseek/deepseek-v4-flash"
    image_model: str = "gemini/gemini-3.1-flash-lite-image"
    image_size: int = 512


@dataclass(frozen=True, slots=True)
class AIServiceConfigOverrides:
    """Optional AI configuration overrides from the CLI layer."""

    text_model: str | None = None
    image_model: str | None = None
    image_size: int | None = None

    def resolve(self, defaults: AIServiceConfig) -> AIServiceConfig:
        """Merge overrides onto the provided defaults."""
        config = defaults
        if self.text_model is not None:
            config = replace(config, text_model=self.text_model)
        if self.image_model is not None:
            config = replace(config, image_model=self.image_model)
        if self.image_size is not None:
            config = replace(config, image_size=self.image_size)
        return config


DEFAULT_AI_SERVICE_CONFIG = AIServiceConfig()


class TextGenerationService(Protocol):
    """Text generation service abstraction."""

    async def generate_text(
        self,
        *,
        model: str,
        messages: Sequence[TextMessage],
        temperature: float,
        reasoning_effort: str | None = None,
    ) -> str:
        """Generate a text response from chat messages.

        ``reasoning_effort`` is forwarded to the provider when set; use
        :data:`DISABLE_REASONING` to turn extended thinking off.
        """
        ...


class ImageGenerationService(Protocol):
    """Image generation service abstraction."""

    async def generate_image(self, *, prompt: str) -> bytes:
        """Generate image bytes from a prompt."""
        ...


class LiteLLMTextService:
    """LiteLLM-backed text generation service."""

    def __init__(
        self, *, api_base: str | None = None, api_key: str | None = None
    ) -> None:
        self._api_base = api_base
        self._api_key = api_key

    def _resolve_model(self, model: str) -> str:
        """Tell LiteLLM which provider owns models on a custom endpoint.

        LiteLLM infers a provider from an unqualified model id.  For model
        names such as ``Qwen/...`` that inference can select Hugging Face even
        when ``api_base`` points at an OpenAI-compatible server.  The
        ``openai/`` prefix makes the intended routing explicit.  An existing
        ``openai/`` prefix is left unchanged.
        """
        if self._api_base is not None and not model.startswith("openai/"):
            return f"openai/{model}"
        return model

    async def generate_text(
        self,
        *,
        model: str,
        messages: Sequence[TextMessage],
        temperature: float,
        reasoning_effort: str | None = None,
    ) -> str:
        """Generate text content using LiteLLM chat completion."""
        completion_kwargs: dict[str, object] = {
            "model": self._resolve_model(model),
            "messages": list(messages),
            "stream": False,
            "temperature": temperature,
            "drop_params": True,
            "timeout": REQUEST_TIMEOUT_SECONDS,
            "num_retries": 0,
        }
        if reasoning_effort == DISABLE_REASONING:
            # DeepSeek honours the OpenAI-format ``thinking`` field, not
            # ``reasoning_effort`` (which its LiteLLM routing discards).  Other
            # OpenAI-compatible servers ignore the unknown field.
            completion_kwargs["extra_body"] = {"thinking": {"type": "disabled"}}
        elif reasoning_effort is not None:
            completion_kwargs["reasoning_effort"] = reasoning_effort
        if self._api_base is not None:
            completion_kwargs["api_base"] = self._api_base
        if self._api_key is not None:
            completion_kwargs["api_key"] = self._api_key

        try:
            async with asyncio.timeout(REQUEST_TIMEOUT_SECONDS):
                response = await acompletion(**completion_kwargs)
        except TimeoutError as exc:
            raise RuntimeError(
                f"Text generation timed out after {REQUEST_TIMEOUT_SECONDS} seconds"
            ) from exc
        content = response.choices[0].message.content  # pyright: ignore[reportAttributeAccessIssue]
        if not isinstance(content, str):
            raise RuntimeError("AI returned non-string content")
        return content


class LiteLLMImageService:
    """LiteLLM-backed image generation service.

    Works with any provider LiteLLM routes through its OpenAI-compatible
    ``image_generation`` surface (Gemini, OpenAI, xAI, Vertex, Bedrock, …);
    the provider is selected by ``model``.
    """

    def __init__(
        self, *, model: str, image_size: int, api_key: str | None = None
    ) -> None:
        self._model = model
        self._image_size = image_size
        self._api_key = api_key

    async def generate_image(self, *, prompt: str) -> bytes:
        """Generate resized image bytes from a prompt."""
        image_kwargs: dict[str, object] = {
            "model": self._model,
            "prompt": prompt,
            "timeout": REQUEST_TIMEOUT_SECONDS,
            "num_retries": 0,
        }
        if self._api_key is not None:
            image_kwargs["api_key"] = self._api_key
        try:
            async with asyncio.timeout(REQUEST_TIMEOUT_SECONDS):
                response = await aimage_generation(**image_kwargs)
        except TimeoutError as exc:
            raise RuntimeError(
                f"Image generation timed out after {REQUEST_TIMEOUT_SECONDS} seconds"
            ) from exc
        data = cast(object, response.data[0])  # pyright: ignore[reportOptionalSubscript]
        b64 = getattr(data, "b64_json", None)
        if not isinstance(b64, str):
            raise RuntimeError("Image generation returned no base64 payload")
        raw = base64.b64decode(b64)
        return resize_to_max_edge(raw, self._image_size)


__all__ = [
    "DEFAULT_AI_SERVICE_CONFIG",
    "DISABLE_REASONING",
    "THINKING_CHOICES",
    "AIServiceConfig",
    "AIServiceConfigOverrides",
    "ImageGenerationService",
    "LiteLLMImageService",
    "LiteLLMTextService",
    "TextGenerationService",
    "TextMessage",
    "resolve_thinking",
]
