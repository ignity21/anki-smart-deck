"""Sentence card generator using AI."""

import json
from importlib.resources import files
from typing import cast

from litellm import acompletion
from loguru import logger

from ankinote.collections.word.generator import TTS_LANG_CODES
from ankinote.collections.word.models import Language
from ankinote.services.tts import GoogleTTSService

from .models import SentenceModel


def _load_prompt_template(target_language: Language) -> str:
    """Load prompt template for the target language."""

    language_to_filename: dict[Language, str] = {
        Language.ENGLISH: "english_us.md",
    }

    filename = language_to_filename.get(target_language)
    if filename is None:
        raise FileNotFoundError(
            f"No sentence prompt template found for language: {target_language.value}. "
            f"Available languages: {list(language_to_filename.keys())}"
        )

    return (
        files("ankinote.collections.sentence.prompts")
        .joinpath(filename)
        .read_text(encoding="utf-8")
    )


async def generate_sentence_data(
    target_sentence: str,
    target_language: Language,
    native_language: Language,
    model_id: str = "gemini/gemini-3.1-flash-lite-preview",
    temperature: float = 0.3,
) -> SentenceModel:
    """Generate sentence card data via LLM.

    The *target_sentence* is provided in the target language; the model
    generates the corresponding native sentence and any useful notes.
    """

    system_prompt = _load_prompt_template(target_language)
    user_message = (
        f"Target sentence: {target_sentence}\n"
        f"Target language: {target_language.value}\n"
        f"Native language: {native_language.value}"
    )

    logger.info(
        f"Generating sentence data for '{target_sentence}' "
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

        sentence_model = SentenceModel.model_validate(data)
        logger.success(f"Generated sentence model for '{target_sentence}'")
        return sentence_model

    except Exception as e:
        logger.error(f"Failed to generate sentence data for '{target_sentence}': {e}")
        raise


class SentenceGenerator:
    """Generator for sentence text data and associated audio."""

    def __init__(
        self,
        llm_model_id: str = "gemini/gemini-3.1-flash-lite-preview",
    ) -> None:
        self._llm_model_id = llm_model_id
        self._tts_service: GoogleTTSService | None = None

    async def generate_sentence_data(
        self,
        target_sentence: str,
        target_lang: Language,
        native_lang: Language,
        temperature: float = 0.3,
    ) -> SentenceModel:
        """Generate structured sentence data via LLM."""
        return await generate_sentence_data(
            target_sentence=target_sentence,
            target_language=target_lang,
            native_language=native_lang,
            model_id=self._llm_model_id,
            temperature=temperature,
        )

    async def _ensure_tts_service(self, lang_code: str) -> None:
        """Initialise (or re-initialise) the TTS service for *lang_code*."""
        if self._tts_service is not None and self._tts_service._lang_code == lang_code:
            return

        if self._tts_service is not None:
            await self._tts_service.__aexit__(None, None, None)

        svc = GoogleTTSService(language_code=lang_code)
        await svc.__aenter__()
        self._tts_service = svc

    async def generate_audio(
        self,
        text: str,
        target_lang: Language,
    ) -> bytes:
        """Generate audio for the given text in the target language."""
        lang_code = TTS_LANG_CODES.get(target_lang)
        if lang_code is None:
            raise ValueError(f"No TTS language code for language: {target_lang.value}")

        await self._ensure_tts_service(lang_code)

        assert self._tts_service is not None
        return await self._tts_service.synthesize_with_random_voice(text)
