"""Phrase card generator using AI."""

import json
from dataclasses import dataclass, field
from importlib.resources import files
from typing import cast

from litellm import acompletion
from loguru import logger

from ankinote.consts import Language
from ankinote.services.tts import GoogleTTSService

from .models import PhraseModel


@dataclass
class PhraseMediaFiles:
    """Media files generated for a single PhraseModel.

    Attributes:
        phrase_audio: MP3 bytes of the phrase itself.
        example_audios: MP3 bytes for each example sentence, ordered to match
            PhraseModel.examples 1-to-1.
    """

    phrase_audio: bytes
    example_audios: list[bytes] = field(default_factory=list)


def _load_prompt_template(target_language: Language) -> str:
    """Load prompt template for the target language."""

    language_to_filename: dict[Language, str] = {
        Language.ENGLISH: "english_us.md",
        Language.JAPANESE: "japanese.md",
    }

    filename = language_to_filename.get(target_language)
    if filename is None:
        raise FileNotFoundError(
            f"No phrase prompt template found for language: {target_language.value}. "
            f"Available languages: {list(language_to_filename.keys())}"
        )

    return (
        files("ankinote.collections.phrase.prompts")
        .joinpath(filename)
        .read_text(encoding="utf-8")
    )


async def generate_phrase_data(
    phrase: str,
    target_language: Language,
    native_language: Language,
    model_id: str = "gemini/gemini-3.1-flash-lite-preview",
    temperature: float = 0.3,
) -> PhraseModel:
    """Generate phrase card data via LLM.

    Args:
        phrase: The phrase to generate data for.
        target_language: The language being learned.
        native_language: The user's native language.
        model_id: The LLM model ID to use.
        temperature: Sampling temperature for generation.

    Returns:
        A PhraseModel object describing the phrase.

    Raises:
        FileNotFoundError: If no prompt template exists for the target language.
        RuntimeError: If AI generation or JSON parsing fails.
    """

    system_prompt = _load_prompt_template(target_language)
    user_message = (
        f"Phrase: {phrase}\n"
        f"Target language: {target_language.value}\n"
        f"Native language: {native_language.value}"
    )

    logger.info(
        f"Generating phrase data for '{phrase}' "
        f"(target: {target_language.value}, native: {native_language.value})"
    )

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
            logger.error(f"Failed to parse JSON response: {e}")
            logger.debug(f"Response content: {content[:500]}...")
            raise RuntimeError(f"AI returned invalid JSON: {e}") from e

        phrase_model = PhraseModel.model_validate(data)
        logger.success(f"Generated phrase model for '{phrase}'")
        return phrase_model

    except Exception as e:
        logger.error(f"Failed to generate phrase data for '{phrase}': {e}")
        raise


class PhraseGenerator:
    """Generator for phrase text data and associated audio."""

    def __init__(
        self,
        tts_service: GoogleTTSService,
        llm_model_id: str = "gemini/gemini-3.1-flash-lite-preview",
    ) -> None:
        self._llm_model_id = llm_model_id
        self._tts_service = tts_service

    async def generate_phrase_data(
        self,
        phrase: str,
        target_lang: Language,
        native_lang: Language,
        temperature: float = 0.3,
    ) -> PhraseModel:
        """Generate structured phrase data via LLM."""
        return await generate_phrase_data(
            phrase=phrase,
            target_language=target_lang,
            native_language=native_lang,
            model_id=self._llm_model_id,
            temperature=temperature,
        )

    async def generate_media(
        self,
        phrase_model: PhraseModel,
    ) -> PhraseMediaFiles:
        """Generate all audio assets for a PhraseModel.

        Args:
            phrase_model: The phrase model to generate media for.
            target_lang: Target language, used to select the TTS voice.

        Returns:
            PhraseMediaFiles with phrase audio and example audios.
        """
        logger.info(f"Generating media for phrase '{phrase_model.phrase}'")

        phrase_audio = await self._tts_service.synthesize_with_random_voice(
            text=phrase_model.phrase
        )

        example_audios = [
            await self._tts_service.synthesize_with_random_voice(example.sentence)
            for example in phrase_model.examples
        ]

        logger.success(
            f"Media ready for '{phrase_model.phrase}': "
            f"1 phrase audio, {len(example_audios)} example audio(s)"
        )

        return PhraseMediaFiles(
            phrase_audio=phrase_audio,
            example_audios=example_audios,
        )
