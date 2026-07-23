"""CLI assembly helpers for application and collection wiring."""

from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Protocol, TypeVar

from ankinote.app import Application
from ankinote.collections.math import MathCollection
from ankinote.collections.phrase import PhraseCollection
from ankinote.collections.sentence import SentenceCollection
from ankinote.collections.word import WordCollection
from ankinote.consts import Language
from ankinote.services.anki import AnkiCollectionClient, AnkiConnectClient
from ankinote.services.ai import (
    AIServiceConfigOverrides,
    DEFAULT_AI_SERVICE_CONFIG,
    LiteLLMGeminiImageService,
    LiteLLMTextService,
)

TCollection = TypeVar("TCollection", covariant=True)
TOptions = TypeVar("TOptions")


class AsyncContextManagerLike(Protocol[TCollection]):
    """Structural type for async context managers."""

    async def __aenter__(self) -> TCollection:
        """Enter the async context manager."""
        ...

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit the async context manager."""
        ...


@dataclass(frozen=True, slots=True)
class LanguageCollectionOptions:
    """Shared CLI options for language-learning collections."""

    native_language: Language
    target_language: Language
    llm_model_id: str | None = None


@dataclass(frozen=True, slots=True)
class WordCollectionOptions(LanguageCollectionOptions):
    """CLI options for the word collection."""

    image_model_id: str | None = None
    image_size: int | None = None


@dataclass(frozen=True, slots=True)
class MathCollectionOptions:
    """CLI options for the math collection."""

    llm_model_id: str | None = None
    image_model_id: str | None = None
    image_size: int | None = None


def build_word_collection(
    client: AnkiCollectionClient,
    options: WordCollectionOptions,
) -> WordCollection:
    """Build a word collection from typed CLI options."""
    config = AIServiceConfigOverrides(
        text_model_id=options.llm_model_id,
        image_model_id=options.image_model_id,
        image_size=options.image_size,
    ).resolve(DEFAULT_AI_SERVICE_CONFIG)
    return WordCollection(
        client,
        native_language=options.native_language,
        target_language=options.target_language,
        text_model_id=config.text_model_id,
        text_service=LiteLLMTextService(),
        image_service=LiteLLMGeminiImageService(
            model_id=config.image_model_id,
            image_size=config.image_size,
        ),
    )


def build_phrase_collection(
    client: AnkiCollectionClient,
    options: LanguageCollectionOptions,
) -> PhraseCollection:
    """Build a phrase collection from typed CLI options."""
    config = AIServiceConfigOverrides(
        text_model_id=options.llm_model_id,
    ).resolve(DEFAULT_AI_SERVICE_CONFIG)
    return PhraseCollection(
        client,
        native_language=options.native_language,
        target_language=options.target_language,
        text_model_id=config.text_model_id,
        text_service=LiteLLMTextService(),
    )


def build_sentence_collection(
    client: AnkiCollectionClient,
    options: LanguageCollectionOptions,
) -> SentenceCollection:
    """Build a sentence collection from typed CLI options."""
    config = AIServiceConfigOverrides(
        text_model_id=options.llm_model_id,
    ).resolve(DEFAULT_AI_SERVICE_CONFIG)
    return SentenceCollection(
        client,
        native_language=options.native_language,
        target_language=options.target_language,
        text_model_id=config.text_model_id,
        text_service=LiteLLMTextService(),
    )


def build_math_collection(
    client: AnkiCollectionClient,
    options: MathCollectionOptions,
) -> MathCollection:
    """Build a math collection from typed CLI options."""
    config = AIServiceConfigOverrides(
        text_model_id=options.llm_model_id,
        image_model_id=options.image_model_id,
        image_size=options.image_size,
    ).resolve(DEFAULT_AI_SERVICE_CONFIG)
    return MathCollection(
        client,
        text_model_id=config.text_model_id,
        text_service=LiteLLMTextService(),
        image_service=LiteLLMGeminiImageService(
            model_id=config.image_model_id,
            image_size=config.image_size,
        ),
    )


@asynccontextmanager
async def collection_context(
    builder: Callable[[AnkiCollectionClient, TOptions], AsyncContextManagerLike[TCollection]],
    options: TOptions,
) -> AsyncIterator[TCollection]:
    """Create application, transport client, and collection in one place."""
    async with Application():
        client = AnkiConnectClient()
        async with builder(client, options) as collection:
            yield collection
