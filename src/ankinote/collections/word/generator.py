"""Word vocabulary card generator using AI."""

import asyncio
import json
from dataclasses import dataclass, field
from importlib.resources import files
from typing import cast

from loguru import logger

from ankinote.collections.common import create_prompt_loader, strip_phonetic_annotations
from ankinote.consts import RUBY_ANNOTATION_LANGUAGES, Language
from ankinote.services.ai import ImageGenerationService, TextGenerationService
from ankinote.services.tts import SpeechSynthesizer

from .models import WordModel

# ============================================================================
# Media Data Structure
# ============================================================================


@dataclass
class WordMediaFiles:
    """Media files generated for a single WordModel.

    Attributes:
        pronunciation: MP3 bytes of the word's pronunciation audio.
        examples: MP3 bytes for each example sentence, ordered to match
                  WordModel.examples 1-to-1.
        images: PNG bytes keyed by definition index (into WordModel.definitions).
                Only visualizable definitions will have an entry.
    """

    pronunciation: bytes
    examples: list[bytes] = field(default_factory=list)
    images: dict[int, bytes] = field(default_factory=dict)


# ============================================================================
# Prompt Helpers
# ============================================================================

_LANGUAGE_TO_FILENAME: dict[Language, str] = {
    Language.ENGLISH: "english_us.md",
    Language.JAPANESE: "japanese.md",
}

_load_prompt_template = create_prompt_loader(
    "ankinote.collections.word",
    _LANGUAGE_TO_FILENAME,
)


def _build_image_user_prompt(word: str, definition: str) -> str:
    return f"Word: {word}\nDefinition: {definition}"


# ============================================================================
# Module-level function (kept for backward compatibility)
# ============================================================================


async def generate_word_data(
    word: str,
    target_language: Language,
    native_language: Language,
    text_service: TextGenerationService,
    model_id: str,
    temperature: float = 0.3,
) -> list[WordModel]:
    """Generate vocabulary card data for a word using AI.

    Args:
        word: The word to generate data for
        target_language: The language being learned
        native_language: The user's native language for translations
        model_id: The LLM model ID to use
        temperature: Sampling temperature for generation (default: 0.3)

    Returns:
        List of WordModel objects (one per part of speech)

    Raises:
        FileNotFoundError: If no prompt template exists for the target language
        RuntimeError: If AI generation or JSON parsing fails
    """
    system_prompt = _load_prompt_template(target_language)

    user_message = (
        f"Word: {word}\n"
        f"Target language: {target_language.value}\n"
        f"Native language: {native_language.value}"
    )

    logger.info(
        f"Generating word data for '{word}' "
        f"(target: {target_language.value}, native: {native_language.value})"
    )

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

        logger.debug(content)
        logger.info(f"Raw AI response length: {len(content)} characters")

        try:
            data = json.loads(content)
        except json.JSONDecodeError as e:
            logger.exception("Failed to parse JSON response")
            logger.debug(f"Response content: {content[:500]}...")
            raise RuntimeError(f"AI returned invalid JSON: {e}") from e

        word_models = [WordModel.model_validate(item) for item in data]

        logger.success(
            f"Generated {len(word_models)} word model(s) for '{word}' "
            f"with part(s) of speech: {[m.part_of_speech for m in word_models]}"
        )

        return word_models

    except Exception as e:
        logger.error(f"Failed to generate word data for '{word}': {e}")
        raise


# ============================================================================
# WordGenerator Class
# ============================================================================


class WordGenerator:
    """Unified generator for word text data and associated media.

    Intended to be used as an async context manager so that the underlying
    TTS service can pre-fetch its voice list once and reuse it across calls.

    Example::

        async with WordGenerator() as gen:
            models = await gen.generate_word_data(word, target, native)
            media  = await gen.generate_media(models[0], target)
    """

    def __init__(
        self,
        tts_service: SpeechSynthesizer,
        text_service: TextGenerationService,
        image_service: ImageGenerationService,
        text_model_id: str,
    ) -> None:
        self._text_service = text_service
        self._image_service = image_service
        self._text_model_id = text_model_id
        self._tts_service = tts_service

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def generate_word_data(
        self,
        word: str,
        target_lang: Language,
        native_lang: Language,
        temperature: float = 0.3,
    ) -> list[WordModel]:
        """Generate structured word data via LLM.

        Delegates to the module-level ``generate_word_data`` function.
        """
        return await generate_word_data(
            word=word,
            target_language=target_lang,
            native_language=native_lang,
            text_service=self._text_service,
            model_id=self._text_model_id,
            temperature=temperature,
        )

    async def generate_media(
        self,
        word_model: WordModel,
        target_lang: Language,
    ) -> WordMediaFiles:
        """Generate all media assets for a WordModel.

        Args:
            word_model: The word model to generate media for.
            target_lang: Target language, used to select the TTS voice.

        Returns:
            WordMediaFiles with pronunciation audio, example audios, and
            images keyed by definition index.
        """
        logger.info(
            f"Generating media for '{word_model.word}' ({word_model.part_of_speech})"
        )

        pronunciation = await self._generate_audio(word_model.word, target_lang)

        try:
            async with asyncio.TaskGroup() as tg:
                example_tasks = [
                    tg.create_task(self._generate_audio(example.sentence, target_lang))
                    for example in word_model.examples
                ]
                image_tasks = {
                    idx: tg.create_task(
                        self._generate_image(word_model.word, definition.target_lang)
                    )
                    for idx, definition in enumerate(word_model.definitions)
                    if definition.is_visualizable
                }
        except* Exception as e:
            for sub_exc in e.exceptions:
                logger.error(
                    f"Error during media generation for '{word_model.word}': {sub_exc}",
                    exc_info=sub_exc,
                )
            raise RuntimeError(f"Media generation failed: {e}") from e

        examples = [task.result() for task in example_tasks]
        logger.debug(f"Generated {len(examples)} example audio(s)")

        images: dict[int, bytes] = {}
        for idx, task in image_tasks.items():
            try:
                images[idx] = task.result()
                logger.debug(f"Generated image for definition[{idx}]")
            except Exception as e:
                definition = word_model.definitions[idx]
                logger.warning(
                    f"Image generation failed for definition[{idx}] "
                    f"('{definition.target_lang[:40]}'): {e}"
                )

        logger.success(
            f"Media ready for '{word_model.word}': "
            f"1 pronunciation, {len(examples)} example(s), {len(images)} image(s)"
        )

        return WordMediaFiles(
            pronunciation=pronunciation,
            examples=examples,
            images=images,
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    async def _generate_audio(self, text: str, target_lang: Language) -> bytes:
        if target_lang in RUBY_ANNOTATION_LANGUAGES:
            text = strip_phonetic_annotations(text)
        return await self._tts_service.synthesize(text)

    async def _generate_image(self, word: str, definition: str) -> bytes:
        system_prompt = (
            files("ankinote.collections.word.prompts")
            .joinpath("image.md")
            .read_text(encoding="utf-8")
        )
        user_prompt = _build_image_user_prompt(word, definition)
        return await self._image_service.generate_image(
            prompt=f"{system_prompt}\n\n{user_prompt}",
        )
