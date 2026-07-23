"""Math/Science knowledge card generator using AI."""

import asyncio
import json
from dataclasses import dataclass, field
from importlib.resources import files

from loguru import logger

from ankinote.services.ai import ImageGenerationService, TextGenerationService

from .models import MathModel

# ============================================================================
# Media Data Structure
# ============================================================================


@dataclass
class MathMediaFiles:
    """Media files generated for a single MathModel.

    Attributes:
        explanation_images: PNG bytes for diagrams that help explain the concept.
                           List can be empty if no visualization needed.
        example_images: PNG bytes keyed by example index (into MathModel.examples).
                       Only visualizable examples will have an entry.
    """

    explanation_images: list[bytes] = field(default_factory=list)
    example_images: dict[int, bytes] = field(default_factory=dict)


# ============================================================================
# Prompt Helpers
# ============================================================================


def _load_general_prompt() -> str:
    """Load the general prompt template for math content generation."""
    return (
        files("ankinote.collections.math.prompts")
        .joinpath("general.md")
        .read_text(encoding="utf-8")
    )


def _load_image_prompt() -> str:
    """Load the image generation prompt template."""
    return (
        files("ankinote.collections.math.prompts")
        .joinpath("image.md")
        .read_text(encoding="utf-8")
    )


def _build_image_user_prompt(context: str, description: str) -> str:
    """Build user prompt for image generation.

    Args:
        context: The broader context (e.g., the front question or example problem)
        description: What specifically to visualize
    """
    return f"Context: {context}\n\nVisualize: {description}"


# ============================================================================
# Module-level function
# ============================================================================


async def generate_math_data(
    front: str,
    text_service: TextGenerationService,
    model_id: str,
    temperature: float = 0.3,
) -> MathModel:
    """Generate math/science card data using AI.

    Args:
        front: The question or concept from the user
        model_id: The LLM model ID to use
        temperature: Sampling temperature for generation (default: 0.3)

    Returns:
        MathModel object with generated content

    Raises:
        RuntimeError: If AI generation or JSON parsing fails
    """
    system_prompt = _load_general_prompt()

    logger.info(f"Generating math card data for: {front[:50]}...")

    try:
        content = await text_service.generate_text(
            model_id=model_id,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": front},
            ],
            temperature=temperature,
        )

        logger.debug(content)
        logger.info(f"Raw AI response length: {len(content)} characters")

        try:
            data = json.loads(content)
        except json.JSONDecodeError as e:
            logger.exception("Failed to parse JSON response")
            logger.debug(f"Response content: {content[:500]}...")
            raise RuntimeError(f"AI returned invalid JSON: {e}") from e

        math_model = MathModel.model_validate(data)

        logger.success(
            f"Generated math card with {len(math_model.examples)} example(s), "
            f"difficulty: {math_model.difficulty}"
        )

        return math_model

    except Exception as e:
        logger.error(f"Failed to generate math data: {e}")
        raise


# ============================================================================
# MathGenerator Class
# ============================================================================


class MathGenerator:
    """Unified generator for math card text data and associated diagrams.

    Example::

        gen = MathGenerator()
        model = await gen.generate_math_data(front)
        media = await gen.generate_media(model)
    """

    def __init__(
        self,
        text_service: TextGenerationService,
        image_service: ImageGenerationService,
        text_model_id: str,
    ) -> None:
        self._text_service = text_service
        self._image_service = image_service
        self._text_model_id = text_model_id

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def generate_math_data(
        self,
        front: str,
        temperature: float = 0.3,
    ) -> MathModel:
        """Generate structured math card data via LLM.

        Delegates to the module-level ``generate_math_data`` function.
        """
        return await generate_math_data(
            front=front,
            text_service=self._text_service,
            model_id=self._text_model_id,
            temperature=temperature,
        )

    async def generate_media(
        self,
        math_model: MathModel,
    ) -> MathMediaFiles:
        """Generate all media assets (diagrams) for a MathModel.

        Args:
            math_model: The math model to generate media for.

        Returns:
            MathMediaFiles with explanation diagrams and example diagrams.
        """
        logger.info(f"Generating media for math card: {math_model.front[:50]}...")

        # Determine if we need diagrams for the main explanation
        # (heuristic: if explanation mentions visualization keywords)
        needs_explanation_diagram = self._needs_diagram(math_model.explanation)

        async with asyncio.TaskGroup() as tg:
            # Main explanation diagram (if needed)
            explanation_task = None
            if needs_explanation_diagram:
                explanation_task = tg.create_task(
                    self._generate_image(
                        context=math_model.front,
                        description=math_model.explanation,
                    )
                )

            # Example diagrams (only for visualizable examples)
            example_tasks = {
                idx: tg.create_task(
                    self._generate_image(
                        context=example.problem,
                        description=example.solution,
                    )
                )
                for idx, example in enumerate(math_model.examples)
                if example.is_visualizable
            }

        explanation_images: list[bytes] = []
        if explanation_task:
            try:
                explanation_images.append(explanation_task.result())
                logger.debug("Generated explanation diagram")
            except Exception as e:
                logger.warning(f"Explanation diagram generation failed: {e}")

        example_images: dict[int, bytes] = {}
        for idx, task in example_tasks.items():
            try:
                example_images[idx] = task.result()
                logger.debug(f"Generated diagram for example[{idx}]")
            except Exception as e:
                logger.warning(f"Example[{idx}] diagram generation failed: {e}")

        logger.success(
            f"Media ready: {len(explanation_images)} explanation diagram(s), "
            f"{len(example_images)} example diagram(s)"
        )

        return MathMediaFiles(
            explanation_images=explanation_images,
            example_images=example_images,
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _needs_diagram(self, text: str) -> bool:
        """Heuristic to determine if text would benefit from a diagram."""
        keywords = [
            "graph",
            "diagram",
            "figure",
            "plot",
            "curve",
            "shape",
            "geometry",
            "triangle",
            "circle",
            "vector",
            "coordinate",
            "axis",
            "visualize",
            "图",
            "图形",
            "图表",
            "曲线",
            "坐标",
        ]
        text_lower = text.lower()
        return any(keyword in text_lower for keyword in keywords)

    async def _generate_image(self, context: str, description: str) -> bytes:
        """Generate a diagram using AI image generation.

        Args:
            context: The broader context (question or problem)
            description: What to visualize

        Returns:
            PNG image bytes
        """
        system_prompt = _load_image_prompt()
        user_prompt = _build_image_user_prompt(context, description)

        return await self._image_service.generate_image(
            prompt=f"{system_prompt}\n\n{user_prompt}",
        )
