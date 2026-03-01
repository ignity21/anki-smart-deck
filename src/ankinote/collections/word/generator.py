"""Word vocabulary card generator using AI."""

import json
from importlib.resources import files
from typing import cast

from litellm import acompletion
from loguru import logger

from .models import Language, WordModel


def load_prompt_template(target_language: Language) -> str:
    """Load prompt template for the target language.

    Args:
        target_language: The language being learned

    Returns:
        The prompt template content as a string

    Raises:
        FileNotFoundError: If no prompt template exists for the language
    """
    # Map Language enum to prompt filename
    language_to_filename: dict[Language, str] = {
        Language.ENGLISH: "english_us.md",
        Language.JAPANESE: "japanese.md",
        # Add more mappings as prompts are created
    }

    filename = language_to_filename.get(target_language)
    if filename is None:
        raise FileNotFoundError(
            f"No prompt template found for language: {target_language.value}. "
            f"Available languages: {list(language_to_filename.keys())}"
        )

    prompt_path = files("ankinote.collections.word.prompts").joinpath(filename)
    return prompt_path.read_text(encoding="utf-8")


async def generate_word_data(
    word: str,
    target_language: Language,
    native_language: Language,
    model_id: str = "gemini-3-flash-preview",
    temperature=0.3,
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
    # Load the appropriate prompt template
    system_prompt = load_prompt_template(target_language)

    # Build user message
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
        # Call LLM API
        response = await acompletion(
            model=f"gemini/{model_id}",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            stream=False,
            temperature=temperature,
        )

        # Extract response content
        content = response.choices[0].message.content  # pyright: ignore[reportAttributeAccessIssue]
        content = cast(str, content)  # Ensure content is treated as a string
        logger.debug(f"Raw AI response length: {len(content)} characters")

        # Parse JSON response
        try:
            data = json.loads(content)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            logger.debug(f"Response content: {content[:500]}...")
            raise RuntimeError(f"AI returned invalid JSON: {e}") from e

        # Convert to WordModel objects
        word_models = [WordModel.model_validate(item) for item in data]

        logger.success(
            f"Generated {len(word_models)} word model(s) for '{word}' "
            f"with part(s) of speech: {[m.part_of_speech for m in word_models]}"
        )

        return word_models

    except Exception as e:
        logger.error(f"Failed to generate word data for '{word}': {e}")
        raise
