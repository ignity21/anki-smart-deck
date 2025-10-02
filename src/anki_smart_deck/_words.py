import json
from anki_smart_deck.config import get_config
from anki_smart_deck import models
from google import genai


class AIWordDeck:
    def __init__(self):
        self._app_config = get_config()
        self._ai_model = "gemini-2.5-flash"
        self._client: genai.Client = genai.Client(
            api_key=self._app_config.google_ai_key
        )

    async def add_word(self, word: str):
        pass

    async def _gen_prons(self, word: str) -> models.Pronunciation:
        async with self._client.aio as aclient:
            prompt = (
                f"Generate pronunciations for word '{word}', "
                "respond in JSON format `{'us': '/KK/', 'uk': '/IPA/'}`."
                "Do not include any markdown text."
            )
            resp = await aclient.models.generate_content(
                model=self._ai_model,
                contents=prompt,
            )
        resp_json = json.loads(resp.text)
        models.Pronunciation(us=resp_json["us"], uk=resp_json["uk"])
        return models.Pronunciation(us=resp_json["us"], uk=resp_json["uk"])


if __name__ == "__main__":
    import asyncio
    from rich import print as rprint

    deck = AIWordDeck()
    prons = asyncio.run(deck._gen_prons("example"))
    rprint(prons)
