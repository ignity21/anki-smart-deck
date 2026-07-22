"""STEM card generator using AI."""

import json
from importlib.resources import files
from typing import cast

from litellm import acompletion
from loguru import logger

from ankinote.collections.common import create_prompt_loader

from .models import CardType, StemModel

_load_prompt_template = create_prompt_loader(
    "ankinote.collections.stem",
    {
        CardType.CONCEPT: "concept.md",
        CardType.FORMULA: "formula.md",
        CardType.PROCEDURE: "procedure.md",
    },
)


def _load_system_prompt() -> str:
    """Load the system prompt for STEM card generation."""
    return (
        files("ankinote.collections.stem.prompts")
        .joinpath("_system.md")
        .read_text(encoding="utf-8")
    )


async def generate_stem_data(
    topic: str,
    card_type: CardType,
    model_id: str = "gemini/gemini-2.5-flash-lite-preview",
    temperature: float = 0.3,
) -> StemModel:
    """Generate STEM card data via LLM.

    The *topic* is a short description of the concept, formula, or procedure
    to generate a card for (e.g. "eigenvalues", "Fourier transform", "Newton's second law").
    """
    system_prompt = _load_system_prompt()
    user_message = _load_prompt_template(card_type) + f"\n\nTopic: {topic}"

    logger.info(f"Generating {card_type} card for '{topic}'")

    try:
        response = await acompletion(
            model=model_id,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            stream=False,
            temperature=temperature,
            drop_params=True,
        )

        content = cast(
            str,
            response.choices[0].message.content,  # pyright: ignore[reportAttributeAccessIssue]
        )

        logger.debug(content)
        logger.info(f"Raw AI response length: {len(content)} characters")

        try:
            data = json.loads(content)
        except json.JSONDecodeError as e:
            logger.exception("Failed to parse JSON response")
            logger.debug(f"Response content: {content[:500]}...")
            raise RuntimeError(f"AI returned invalid JSON: {e}") from e

        stem_model = StemModel.model_validate(data)
        logger.success(f"Generated {card_type} card for '{topic}'")
        return stem_model

    except Exception as e:
        logger.error(f"Failed to generate STEM data for '{topic}': {e}")
        raise


class StemGenerator:
    """Generator for STEM card data."""

    def __init__(
        self,
        llm_model_id: str = "gemini/gemini-2.5-flash-lite-preview",
    ) -> None:
        self._llm_model_id = llm_model_id

    async def generate(
        self,
        topic: str,
        card_type: CardType,
        temperature: float = 0.3,
    ) -> StemModel:
        """Generate structured STEM card data via LLM."""
        return await generate_stem_data(
            topic=topic,
            card_type=card_type,
            model_id=self._llm_model_id,
            temperature=temperature,
        )
