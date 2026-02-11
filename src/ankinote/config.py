import os

from dotenv import load_dotenv

load_dotenv()


class EnvVars:
    GOOGLE_TTS_KEY: str = os.getenv("GOOGLE_TTS_KEY", "")
    ANKI_CONNECT_URL: str = os.getenv("ANKI_CONNECT_URL", "http://localhost:8765")


envs = EnvVars()
