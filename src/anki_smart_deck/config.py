import os

from dotenv import load_dotenv
from pydantic import BaseModel, Field


class AppConfig(BaseModel):
    google_ai_key: str = Field(description="API key for Google AI services.")
    google_tts_key: str = Field(
        description="API key for Google Text-to-Speech services."
    )
    google_search_key: str = Field(description="API key for Google Search services.")
    google_cse_id: str = Field(description="Custom Search Engine ID for Google Search.")
    anki_connect_url: str = Field(
        description="URL for AnkiConnect API.", default="http://localhost:8765"
    )
    word_deck_name: str = Field(
        default="AI Words", description="Anki deck name for words."
    )
    word_model_name: str = Field(
        default="AI Word (R)", description="Anki note model name for words."
    )


_config: AppConfig | None = None


def get_config() -> AppConfig:
    global _config
    if _config is None:
        load_dotenv()
        _config = AppConfig(
            google_ai_key=os.getenv("GOOGLE_AI_API_KEY", ""),
            google_tts_key=os.getenv("GOOGLE_CLOUD_TTS_KEY", ""),
            google_search_key=os.getenv("GOOGLE_CUSTOM_SEARCH_KEY", ""),
            google_cse_id=os.getenv("GOOGLE_SEARCH_ENGINE_ID", ""),
            anki_connect_url=os.getenv("ANKI_CONNECT_URL", "http://localhost:8765"),
        )
    return _config
