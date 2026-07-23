"""Tests for unified AI service usage across generators."""

import pytest

from ankinote.collections.math.generator import MathGenerator
from ankinote.collections.math.models import Example as MathExample
from ankinote.collections.math.models import MathModel
from ankinote.collections.phrase.generator import PhraseGenerator
from ankinote.collections.sentence.generator import SentenceGenerator
from ankinote.collections.stem.generator import StemGenerator
from ankinote.collections.stem.models import CardType
from ankinote.collections.word.generator import WordGenerator
from ankinote.consts import Language


class FakeTextService:
    """Record text generation requests and return queued responses."""

    def __init__(self, responses: list[str]) -> None:
        self._responses = list(responses)
        self.calls: list[dict[str, object]] = []

    async def generate_text(
        self,
        *,
        model_id: str,
        messages: list[dict[str, str]],
        temperature: float,
    ) -> str:
        self.calls.append(
            {
                "model_id": model_id,
                "messages": messages,
                "temperature": temperature,
            }
        )
        return self._responses.pop(0)


class FakeImageService:
    """Record image prompts and return deterministic bytes."""

    def __init__(self) -> None:
        self.calls: list[str] = []

    async def generate_image(self, *, prompt: str) -> bytes:
        self.calls.append(prompt)
        return b"image-bytes"


class FakeSpeechSynthesizer:
    """Minimal synth fake for generator construction."""

    async def synthesize(self, text: str) -> bytes:  # pragma: no cover
        return text.encode()


@pytest.mark.asyncio
async def test_word_generator_uses_unified_text_service():
    text_service = FakeTextService(
        [
            """
            [
              {
                "word": "test",
                "part_of_speech": "n.",
                "pronunciation": null,
                "syllables": ["test"],
                "difficulty": "A1",
                "definitions": [{"target_lang": "test", "native_lang": "测试", "is_visualizable": false}],
                "synonyms": [],
                "examples": [{"sentence": "a test", "translation": "测试", "highlights": []}],
                "collocations": [],
                "notes": []
              }
            ]
            """
        ]
    )
    generator = WordGenerator(
        tts_service=FakeSpeechSynthesizer(),
        text_service=text_service,
        image_service=FakeImageService(),
        text_model_id="word-model",
    )

    models = await generator.generate_word_data(
        "test",
        Language.ENGLISH,
        Language.CHINESE_S,
    )

    assert models[0].word == "test"
    assert text_service.calls[0]["model_id"] == "word-model"


@pytest.mark.asyncio
async def test_phrase_generator_uses_unified_text_service():
    text_service = FakeTextService(
        [
            """
            {
              "phrase": "take off",
              "difficulty": "B1",
              "definitions": [{"target_lang": "起飞", "native_lang": "take off"}],
              "examples": [{"sentence": "The plane takes off.", "translation": "飞机起飞。", "highlight": "takes off"}],
              "notes": [],
              "associations": []
            }
            """
        ]
    )
    generator = PhraseGenerator(
        tts_service=FakeSpeechSynthesizer(),
        text_service=text_service,
        text_model_id="phrase-model",
    )

    model = await generator.generate_phrase_data(
        "take off",
        Language.ENGLISH,
        Language.CHINESE_S,
    )

    assert model.phrase == "take off"
    assert text_service.calls[0]["model_id"] == "phrase-model"


@pytest.mark.asyncio
async def test_sentence_generator_uses_unified_text_service():
    text_service = FakeTextService(
        [
            """
            {
              "target_sentence": "This is a test.",
              "native_sentence": "这是一个测试。",
              "notes": [],
              "phrases": []
            }
            """
        ]
    )
    generator = SentenceGenerator(
        tts_service=FakeSpeechSynthesizer(),
        text_service=text_service,
        text_model_id="sentence-model",
    )

    model = await generator.generate_sentence_data(
        "This is a test.",
        Language.ENGLISH,
        Language.CHINESE_S,
    )

    assert model.target_sentence == "This is a test."
    assert text_service.calls[0]["model_id"] == "sentence-model"


@pytest.mark.asyncio
async def test_math_generator_uses_unified_services():
    text_service = FakeTextService(
        [
            """
            {
              "front": "What is a derivative?",
              "explanation": "A derivative measures rate of change.",
              "key_points": ["rate of change"],
              "examples": [{"problem": "f(x)=x^2", "solution": "f'(x)=2x", "is_visualizable": true}],
              "related_concepts": ["limits"],
              "difficulty": "intermediate",
              "tags": ["calculus"]
            }
            """
        ]
    )
    image_service = FakeImageService()
    generator = MathGenerator(
        text_service=text_service,
        image_service=image_service,
        text_model_id="math-model",
    )

    model = await generator.generate_math_data("What is a derivative?")
    media = await generator.generate_media(
        MathModel(
            front=model.front,
            explanation="Use a graph to visualize the tangent line.",
            key_points=model.key_points,
            examples=[
                MathExample(
                    problem="f(x)=x^2",
                    solution="Plot the parabola and tangent.",
                    is_visualizable=True,
                )
            ],
            related_concepts=model.related_concepts,
            difficulty=model.difficulty,
            tags=model.tags,
        )
    )

    assert model.front == "What is a derivative?"
    assert text_service.calls[0]["model_id"] == "math-model"
    assert media.explanation_images == [b"image-bytes"]
    assert media.example_images == {0: b"image-bytes"}
    assert len(image_service.calls) == 2


@pytest.mark.asyncio
async def test_stem_generator_uses_unified_text_service():
    text_service = FakeTextService(
        [
            """
            {
              "card_type": "concept",
              "front": "What is a vector space?",
              "back_brief": "A set closed under vector addition and scalar multiplication.",
              "back_detail": "It satisfies the vector space axioms over a field."
            }
            """
        ]
    )
    generator = StemGenerator(
        text_service=text_service,
        text_model_id="stem-model",
    )

    model = await generator.generate("vector space", CardType.CONCEPT)

    assert model.card_type is CardType.CONCEPT
    assert text_service.calls[0]["model_id"] == "stem-model"
