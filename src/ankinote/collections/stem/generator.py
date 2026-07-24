"""STEM card generator using AI."""

import json
from importlib.resources import files
from typing import cast

from loguru import logger

from ankinote.services.ai import ImageGenerationService, TextGenerationService

from .models import StemModel


def _load_system_prompt() -> str:
    """Load the system prompt for STEM card generation."""
    return (
        files("ankinote.collections.stem.prompts")
        .joinpath("_system.md")
        .read_text(encoding="utf-8")
    )


def _load_prompt(prompt_name: str) -> str:
    """Load a specific prompt template."""
    return (
        files("ankinote.collections.stem.prompts")
        .joinpath(prompt_name)
        .read_text(encoding="utf-8")
    )


def _load_image_prompt() -> str:
    """Load the image generation prompt template."""
    return (
        files("ankinote.collections.stem.prompts")
        .joinpath("image.md")
        .read_text(encoding="utf-8")
    )



def _strip_json_fences(content: str) -> str:
    """Strip markdown code fences (```json ... ```) from AI response."""
    content = content.strip()
    if content.startswith("```"):
        # Remove opening fence
        first_newline = content.find("\n")
        if first_newline != -1:
            content = content[first_newline + 1:]
        # Remove closing fence
        if content.endswith("```"):
            content = content[:-3].rstrip()
        elif "\n```" in content:
            content = content[:content.rindex("\n```")]
    return content.strip()



async def generate_stem_data(
    topic: str,
    text_service: TextGenerationService,
    model_id: str,
    temperature: float = 0.3,
) -> StemModel:
    """Generate STEM card data via LLM.

    The *topic* is the user's natural language question or concept
    (e.g. "What is a derivative?", "请解释平行线的概念", "State Newton's second law").
    The AI automatically determines the card type (concept, formula, or procedure).
    """
    system_prompt = _load_system_prompt()
    user_message = (
        "Generate a STEM flashcard for the following topic. "
        "Determine the card type (concept, formula, or procedure) based on the topic itself.\n\n"
        f"Topic: {topic}"
    )

    logger.info(f"Generating STEM card for '{topic}'")

    try:
        content = await text_service.generate_text(
            model_id=model_id,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            temperature=temperature,
        )
        content = cast(str, content)
        content = _strip_json_fences(content)

        logger.debug(content)
        logger.info(f"Raw AI response length: {len(content)} characters")

        try:
            data = json.loads(content)
        except json.JSONDecodeError as e:
            logger.exception("Failed to parse JSON response")
            logger.debug(f"Response content: {content[:500]}...")
            raise RuntimeError(f"AI returned invalid JSON: {e}") from e

        stem_model = StemModel.model_validate(data)
        logger.success(
            f"Generated {stem_model.card_type} card for '{topic}'"
        )
        return stem_model

    except Exception as e:
        logger.error(f"Failed to generate STEM data for '{topic}': {e}")
        raise


class StemGenerator:
    """Generator for STEM card data, with optional image generation."""

    def __init__(
        self,
        text_service: TextGenerationService,
        text_model_id: str,
        image_service: ImageGenerationService | None = None,
    ) -> None:
        self._text_service = text_service
        self._text_model_id = text_model_id
        self._image_service = image_service

    async def generate(
        self,
        topic: str,
        temperature: float = 0.3,
    ) -> StemModel:
        """Generate structured STEM card data via LLM.

        The AI automatically determines the card type and decides
        whether a diagram is needed.
        """
        return await generate_stem_data(
            topic=topic,
            text_service=self._text_service,
            model_id=self._text_model_id,
            temperature=temperature,
        )

    async def generate_image(self, description: str) -> bytes:
        """Generate an image from a description.

        Args:
            description: The image_description from the StemModel.

        Returns:
            PNG image bytes.

        Raises:
            RuntimeError: If no image service is configured.
        """
        if self._image_service is None:
            raise RuntimeError(
                "Image generation requested but no image service configured"
            )

        system_prompt = _load_image_prompt()
        prompt = f"{system_prompt}\n\n{description}"

        return await self._image_service.generate_image(prompt=prompt)
