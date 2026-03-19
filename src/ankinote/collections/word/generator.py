"""Word vocabulary card generator using AI."""

import base64
import json
from dataclasses import dataclass, field
from importlib.resources import files
from typing import Self, cast

from litellm import acompletion, aimage_generation
from loguru import logger

from ankinote.services.tts import GoogleTTSService
from ankinote.utils.img import scale

from .models import Language, WordModel

# ============================================================================
# Language Mappings
# ============================================================================

TTS_LANG_CODES: dict[Language, str] = {
    Language.ENGLISH: "en-US",
    Language.JAPANESE: "ja-JP",
    Language.CHINESE_S: "cmn-CN",
    Language.CHINESE_T: "cmn-TW",
    Language.FRENCH: "fr-FR",
    Language.SPANISH: "es-ES",
    Language.GERMAN: "de-DE",
    Language.KOREAN: "ko-KR",
}


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


def load_prompt_template(target_language: Language) -> str:
    """Load prompt template for the target language.

    Args:
        target_language: The language being learned

    Returns:
        The prompt template content as a string

    Raises:
        FileNotFoundError: If no prompt template exists for the language
    """
    language_to_filename: dict[Language, str] = {
        Language.ENGLISH: "english_us.md",
        Language.JAPANESE: "japanese.md",
    }

    filename = language_to_filename.get(target_language)
    if filename is None:
        raise FileNotFoundError(
            f"No prompt template found for language: {target_language.value}. "
            f"Available languages: {list(language_to_filename.keys())}"
        )

    prompt_path = files("ankinote.collections.word.prompts").joinpath(filename)
    return prompt_path.read_text(encoding="utf-8")


def _build_image_user_prompt(word: str, definition: str) -> str:
    return f"Word: {word}\nDefinition: {definition}"


# ============================================================================
# Module-level function (kept for backward compatibility)
# ============================================================================


async def generate_word_data(
    word: str,
    target_language: Language,
    native_language: Language,
    model_id: str = "gemini/gemini-3.1-flash-lite-preview",
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
    system_prompt = load_prompt_template(target_language)

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

        content = response.choices[0].message.content  # pyright: ignore[reportAttributeAccessIssue]
        content = cast(str, content)

        logger.debug(content)
        logger.info(f"Raw AI response length: {len(content)} characters")

        try:
            data = json.loads(content)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
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
            media  = await gen.generate_media(models[0])
    """

    def __init__(
        self,
        llm_model_id: str = "gemini/gemini-3.1-flash-lite-preview",
        image_model_id: str = "gemini/gemini-2.5-flash-image",
        image_size: int = 256,
    ) -> None:
        self._llm_model_id = llm_model_id
        self._image_model_id = image_model_id
        self._image_size = image_size
        self._tts_service: GoogleTTSService | None = None

    async def __aenter__(self) -> Self:
        # TTS service is language-specific; it is initialised lazily in
        # generate_media() because the language is not known at construction time.
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        if self._tts_service is not None:
            await self._tts_service.__aexit__(exc_type, exc_val, exc_tb)
            self._tts_service = None

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
            model_id=self._llm_model_id,
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
        lang_code = TTS_LANG_CODES.get(target_lang)
        if lang_code is None:
            raise ValueError(f"No TTS language code for language: {target_lang.value}")

        await self._ensure_tts_service(lang_code)

        logger.info(
            f"Generating media for '{word_model.word}' ({word_model.part_of_speech})"
        )

        pronunciation = await self._generate_audio(word_model.word)

        examples: list[bytes] = []
        for example in word_model.examples:
            audio = await self._generate_audio(example.sentence)
            examples.append(audio)
        logger.debug(f"Generated {len(examples)} example audio(s)")

        images: dict[int, bytes] = {}
        for idx, definition in enumerate(word_model.definitions):
            if definition.is_visualizable:
                try:
                    img = await self._generate_image(
                        word_model.word, definition.target_lang
                    )
                    images[idx] = img
                    logger.debug(f"Generated image for definition[{idx}]")
                except Exception as e:
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

    async def _ensure_tts_service(self, lang_code: str) -> None:
        """Initialise (or re-initialise) the TTS service for *lang_code*."""
        if self._tts_service is not None and self._tts_service._lang_code == lang_code:
            return  # already ready for the right language

        if self._tts_service is not None:
            await self._tts_service.__aexit__(None, None, None)

        svc = GoogleTTSService(language_code=lang_code)
        await svc.__aenter__()
        self._tts_service = svc

    async def _generate_audio(self, text: str) -> bytes:
        assert self._tts_service is not None
        return await self._tts_service.synthesize_with_random_voice(text)

    async def _generate_image(self, word: str, definition: str) -> bytes:
        system_prompt = (
            files("ankinote.collections.word.prompts")
            .joinpath("image.md")
            .read_text(encoding="utf-8")
        )
        user_prompt = _build_image_user_prompt(word, definition)
        response = await aimage_generation(
            model=self._image_model_id,
            prompt=f"{system_prompt}\n\n{user_prompt}",
        )
        b64: str = response.data[0].b64_json  # pyright: ignore[reportAssignmentType, reportOptionalSubscript]
        raw = base64.b64decode(b64)
        return scale(raw, self._image_size)
