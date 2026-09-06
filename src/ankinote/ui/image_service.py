"""Build image services from GUI provider profiles."""

from ankinote.services.ai import ImageGenerationService, LiteLLMImageService
from ankinote.services.fal import FalImageService
from ankinote.ui.config import CUSTOM_VENDOR, ProviderProfile


def build_image_service(
    profile: ProviderProfile, *, image_size: int, model: str | None = None
) -> ImageGenerationService:
    """Use the selected profile and optional page-specific model override."""
    selected_model = model or profile.model
    if profile.vendor == "Fal":
        return FalImageService(
            model=selected_model,
            image_size=image_size,
            api_key=profile.api_key or None,
            api_base=profile.base_url or None,
        )
    return LiteLLMImageService(
        model=selected_model,
        image_size=image_size,
        api_key=profile.api_key or None,
        api_base=profile.base_url or None,
        force_openai_route=profile.vendor == CUSTOM_VENDOR,
    )
