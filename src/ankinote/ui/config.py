"""Configuration persistence for the GUI."""

import functools
import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path

# Built-in LLM provider definitions — the ones the GUI manages directly (model
# picker + a labelled key field). Anything else (DeepSeek, Qwen, a local server,
# …) is reached through a "Custom endpoint" route instead.
#
# Model lists here are only a fallback: `get_provider_models` first pulls the
# provider's chat models from litellm's bundled catalog and uses these curated
# ids only when that lookup fails or turns up empty.
PROVIDERS: dict[str, dict] = {
    "OpenAI": {
        "models": ["gpt-4o", "gpt-4o-mini", "o3-mini", "gpt-4.1"],
        "env_key": "OPENAI_API_KEY",
        "litellm_provider": "openai",
        "model_prefix": None,
        "api_base": "https://api.openai.com/v1",
    },
    "Anthropic": {
        "models": [
            "claude-sonnet-4-20250514",
            "claude-haiku-4-20250514",
        ],
        "env_key": "ANTHROPIC_API_KEY",
        "litellm_provider": "anthropic",
        "model_prefix": None,
        "api_base": "https://api.anthropic.com/v1",
    },
    "Google": {
        "models": [
            "gemini/gemini-2.0-flash",
            "gemini/gemini-2.5-pro-exp-03-25",
        ],
        "env_key": "GEMINI_API_KEY",
        "litellm_provider": "gemini",
        "model_prefix": "gemini/",
        "api_base": "https://generativelanguage.googleapis.com/v1beta",
    },
    "xAI": {
        "models": ["xai/grok-4", "xai/grok-3"],
        "env_key": "XAI_API_KEY",
        "litellm_provider": "xai",
        "model_prefix": "xai/",
        "api_base": "https://api.x.ai/v1",
    },
}

# Sentinel provider name for a user-supplied OpenAI-compatible endpoint
# (custom base URL + arbitrary model id), e.g. a local vLLM/Ollama/LM Studio
# server or a third-party OpenAI-compatible API.
CUSTOM_PROVIDER = "Custom (OpenAI-compatible)"
CUSTOM_API_KEY_STORAGE_KEY = "CUSTOM_API_KEY"
NEW_CUSTOM_PROVIDER = "＋ Add custom provider"

# Substrings that disqualify an otherwise "chat" mode model from the
# picker — these variants require request shapes our generators don't send.
_EXCLUDED_NAME_SUBSTRINGS = ("-audio-", "-search-", "/container")


@functools.cache
def _discover_chat_models(
    litellm_provider: str, model_prefix: str | None
) -> tuple[str, ...]:
    """Pull the current chat-capable model ids for a provider from litellm's catalog."""
    try:
        import litellm
    except ImportError:
        return ()

    models: list[str] = []
    for name, info in litellm.model_cost.items():
        if not isinstance(info, dict):
            continue
        if info.get("litellm_provider") != litellm_provider:
            continue
        if info.get("mode") != "chat":
            continue
        if name.startswith("ft:"):
            continue
        if any(sub in name for sub in _EXCLUDED_NAME_SUBSTRINGS):
            continue
        if model_prefix is not None and not name.startswith(model_prefix):
            continue
        models.append(name)
    return tuple(sorted(models))


def get_provider_models(provider: str) -> list[str]:
    """Return the current list of selectable chat model ids for a provider."""
    info = PROVIDERS[provider]
    models = list(_discover_chat_models(info["litellm_provider"], info["model_prefix"]))
    return models or list(info["models"])


async def fetch_model_ids(
    *,
    litellm_provider: str,
    api_base: str,
    api_key: str,
    model_prefix: str | None = None,
) -> list[str]:
    """Ask a provider's HTTP API for the model ids it currently serves.

    Handles the OpenAI-compatible ``GET /models`` shape (OpenAI, xAI, DeepSeek,
    vLLM, LM Studio, …), Anthropic's ``/v1/models``, and Gemini's
    ``/v1beta/models``. Ids come back prefixed the way litellm expects them
    (e.g. ``gemini/…``). Raises ``httpx`` errors when the request fails.
    """
    import httpx

    url = f"{api_base.rstrip('/')}/models"
    headers: dict[str, str] = {}
    params: dict[str, str] = {}
    if litellm_provider == "anthropic":
        headers = {"x-api-key": api_key, "anthropic-version": "2023-06-01"}
        params = {"limit": "1000"}
    elif litellm_provider in {"gemini", "vertex_ai"}:
        params = {"key": api_key, "pageSize": "1000"}
    else:
        headers = {"Authorization": f"Bearer {api_key}"}

    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.get(url, headers=headers, params=params or None)
        response.raise_for_status()
        payload = response.json()

    if litellm_provider in {"gemini", "vertex_ai"}:
        names = [
            entry.get("name", "").removeprefix("models/")
            for entry in payload.get("models", [])
            if "generateContent" in entry.get("supportedGenerationMethods", [])
        ]
    else:
        names = [
            entry["id"]
            for entry in payload.get("data", [])
            if isinstance(entry, dict) and entry.get("id")
        ]

    prefix = model_prefix or ""
    return sorted(
        {name if name.startswith(prefix) else prefix + name for name in names if name}
    )


DEFAULT_IMAGE_MODELS: list[str] = [
    "gemini/gemini-3.1-flash-lite-image",
    "gemini/gemini-2.0-flash-exp-image",
    "gpt-image-1",
    "xai/grok-2-image",
]

# Built-in image provider definitions, mirroring ``PROVIDERS``. Model lists are
# discovered live from litellm's catalog (see ``get_image_provider_models``);
# these are only the fallback when that lookup fails or turns up empty.
IMAGE_PROVIDERS: dict[str, dict] = {
    "OpenAI": {
        "models": ["gpt-image-1", "dall-e-3"],
        "env_key": "OPENAI_API_KEY",
        "litellm_provider": "openai",
        "model_prefix": None,
    },
    "Google": {
        "models": [
            "gemini/gemini-3.1-flash-lite-image",
            "gemini/gemini-2.5-flash-image",
            "gemini/imagen-3.0-generate-002",
        ],
        "env_key": "GEMINI_API_KEY",
        "litellm_provider": "gemini",
        "model_prefix": "gemini/",
    },
    "xAI": {
        "models": ["xai/grok-2-image"],
        "env_key": "XAI_API_KEY",
        "litellm_provider": "xai",
        "model_prefix": "xai/",
    },
}

# litellm image providers → the environment variable holding their API key.
# Covers the chat providers in ``PROVIDERS`` plus image-only providers.
_IMAGE_PROVIDER_ENV_KEYS: dict[str, str] = {
    "gemini": "GEMINI_API_KEY",
    "vertex_ai": "GEMINI_API_KEY",
    "openai": "OPENAI_API_KEY",
    "azure": "AZURE_API_KEY",
    "xai": "XAI_API_KEY",
    "recraft": "RECRAFT_API_KEY",
}
DEFAULT_IMAGE_ENV_KEY = "GEMINI_API_KEY"
DEFAULT_IMAGE_PROVIDER = "Google"


@functools.cache
def _discover_image_models(
    litellm_provider: str, model_prefix: str | None
) -> tuple[str, ...]:
    """Pull the current image-generation model ids for a provider from litellm."""
    try:
        import litellm
    except ImportError:
        return ()

    prefix = model_prefix or ""
    models: list[str] = []
    for name, info in litellm.model_cost.items():
        if not isinstance(info, dict):
            continue
        if info.get("litellm_provider") != litellm_provider:
            continue
        if info.get("mode") != "image_generation":
            continue
        if model_prefix is not None and not name.startswith(model_prefix):
            continue
        # Drop litellm's size-/step-prefixed catalog variants
        # (e.g. "1024-x-1024/dall-e-2", "fal-ai/.../text-to-image").
        if "/" in name.removeprefix(prefix):
            continue
        models.append(name)
    return tuple(sorted(models))


def get_image_provider_models(provider: str) -> list[str]:
    """Return the selectable image model ids for a provider.

    Curated defaults come first (they stay valid even if litellm's catalog
    lags), followed by any additional ids discovered in the catalog.
    """
    info = IMAGE_PROVIDERS[provider]
    discovered = _discover_image_models(info["litellm_provider"], info["model_prefix"])
    return list(dict.fromkeys([*info["models"], *discovered]))


def image_provider_for(model: str) -> str:
    """Return the :data:`IMAGE_PROVIDERS` key that owns an image model id.

    Matches by ``model_prefix`` first, then falls back to litellm's provider
    lookup, and finally to :data:`DEFAULT_IMAGE_PROVIDER` for unknown ids.
    """
    for name, info in IMAGE_PROVIDERS.items():
        prefix = info["model_prefix"]
        if prefix and model.startswith(prefix):
            return name
    try:
        import litellm
    except ImportError:
        return DEFAULT_IMAGE_PROVIDER
    try:
        _, provider, _, _ = litellm.get_llm_provider(model)
    except litellm.exceptions.BadRequestError:
        return DEFAULT_IMAGE_PROVIDER
    for name, info in IMAGE_PROVIDERS.items():
        if info["litellm_provider"] == provider:
            return name
    return DEFAULT_IMAGE_PROVIDER


def image_env_key_for(model: str) -> str:
    """Return the env var name holding the API key for an image model.

    Args:
        model: An image model id, e.g. ``"gemini/gemini-3.1-flash-lite-image"``
            or ``"gpt-image-1"``.

    Returns:
        The environment variable litellm reads that provider's key from,
        falling back to :data:`DEFAULT_IMAGE_ENV_KEY` for unknown providers.
    """
    try:
        import litellm
    except ImportError:
        return DEFAULT_IMAGE_ENV_KEY
    try:
        _, provider, _, _ = litellm.get_llm_provider(model)
    except litellm.exceptions.BadRequestError:
        return DEFAULT_IMAGE_ENV_KEY
    return _IMAGE_PROVIDER_ENV_KEYS.get(provider, DEFAULT_IMAGE_ENV_KEY)


@dataclass
class DefaultsConfig:
    native_language: str = "Chinese(Simplified)"
    target_language: str = "English"
    generate_image: bool = True


@dataclass
class CustomProvider:
    """A named OpenAI-compatible endpoint configured by the user."""

    base_url: str = ""
    model: str = ""
    api_key: str = ""


@dataclass
class Settings:
    provider: str = "OpenAI"
    text_model: str = "gpt-4o"
    image_provider: str = "Google"
    image_model: str = "gemini/gemini-3.1-flash-lite-image"
    image_size: int = 512
    custom_base_url: str = ""
    api_keys: dict[str, str] = field(default_factory=dict)
    custom_providers: dict[str, CustomProvider] = field(default_factory=dict)
    defaults: DefaultsConfig = field(default_factory=DefaultsConfig)


def _get_config_dir() -> Path:
    xdg_config = os.environ.get("XDG_CONFIG_HOME")
    if xdg_config:
        base = Path(xdg_config)
    else:
        base = Path.home() / ".config"
    return base / "ankinote"


def _get_config_path() -> Path:
    return _get_config_dir() / "settings.json"


def load_settings() -> Settings:
    """Load settings from ~/.config/ankinote/settings.json."""
    path = _get_config_path()
    if not path.exists():
        return Settings()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        defaults_data = data.get("defaults", {})
        defaults = DefaultsConfig(**defaults_data)
        custom_providers = {
            name: CustomProvider(
                base_url=value.get("base_url", ""),
                model=value.get("model", ""),
                api_key=value.get("api_key", ""),
            )
            for name, value in data.get("custom_providers", {}).items()
            if isinstance(name, str) and isinstance(value, dict)
        }
        # Migrate the original single custom provider into a named profile.
        # Keep the old fields in Settings as well so older callers/configs
        # remain readable during the transition.
        legacy_provider = data.get("provider") == CUSTOM_PROVIDER
        if legacy_provider and CUSTOM_PROVIDER not in custom_providers:
            custom_providers[CUSTOM_PROVIDER] = CustomProvider(
                base_url=data.get("custom_base_url", ""),
                model=data.get("text_model", ""),
                api_key=data.get("api_keys", {}).get(CUSTOM_API_KEY_STORAGE_KEY, ""),
            )

        image_model = data.get("image_model", "gemini/gemini-3.1-flash-lite-image")
        return Settings(
            provider=data.get("provider", "OpenAI"),
            text_model=data.get("text_model", "gpt-4o"),
            image_provider=data.get("image_provider", image_provider_for(image_model)),
            image_model=image_model,
            image_size=data.get("image_size", 512),
            custom_base_url=data.get("custom_base_url", ""),
            api_keys=data.get("api_keys", {}),
            custom_providers=custom_providers,
            defaults=defaults,
        )
    except (json.JSONDecodeError, KeyError, TypeError):
        return Settings()


def save_settings(settings: Settings) -> None:
    """Save settings to ~/.config/ankinote/settings.json."""
    config_dir = _get_config_dir()
    config_dir.mkdir(parents=True, exist_ok=True)
    data = {
        "provider": settings.provider,
        "text_model": settings.text_model,
        "image_provider": settings.image_provider,
        "image_model": settings.image_model,
        "image_size": settings.image_size,
        "custom_base_url": settings.custom_base_url,
        "api_keys": settings.api_keys,
        "custom_providers": {
            name: asdict(provider)
            for name, provider in settings.custom_providers.items()
        },
        "defaults": asdict(settings.defaults),
    }
    path = _get_config_path()
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def apply_env(settings: Settings) -> None:
    """Set API keys from settings into os.environ (for litellm / Google TTS)."""
    for key, value in settings.api_keys.items():
        if value:
            os.environ[key] = value
