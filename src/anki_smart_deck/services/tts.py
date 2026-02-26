import asyncio
import random
from typing import List, Tuple
from anki_smart_deck.config import get_config

from google.cloud import texttospeech_v1
from rich import print as rprint


class GoogleTTSService:
    def __init__(self):
        app_config = get_config()
        self._tts_cli = texttospeech_v1.TextToSpeechClient(
            client_options={"api_key": app_config.google_tts_key}
        )
        # 缓存 Neural2 语音列表，避免重复调用 API
        self._neural_voices_cache = {}

    def list_all_voices(self, language_code="en-US"):
        """列出所有可用的 Neural2 语音"""
        voices = self._tts_cli.list_voices(language_code=language_code)

        neural_voices = []
        for voice in voices.voices:
            if "Neural2" in voice.name or "Neural2" in voice.name:
                neural_voices.append(voice.name)

        if neural_voices:
            rprint(
                f"\n[cyan]Neural2 语音[/cyan] [yellow]({len(neural_voices)} 个)[/yellow]:"
            )
            for name in sorted(neural_voices):
                rprint(f"  [green]✓[/green] {name}")

        return neural_voices

    def get_neural_voices(self, language_code="en-US") -> List:
        """
        获取 Neural2 语音列表（带缓存）

        Args:
            language_code: 语言代码，如 "en-US", "zh-CN" 等

        Returns:
            Neural2 语音对象列表
        """
        # 如果已缓存，直接返回
        if language_code in self._neural_voices_cache:
            return self._neural_voices_cache[language_code]

        # 获取所有语音
        voices = self._tts_cli.list_voices(language_code=language_code)

        # 筛选 Neural2 语音
        neural_voices = []
        for voice in voices.voices:
            if "Neural2" in voice.name or "Neural2" in voice.name:
                neural_voices.append(voice)

        # 缓存结果
        self._neural_voices_cache[language_code] = neural_voices
        rprint(
            f"[dim]💾 已缓存 {len(neural_voices)} 个 {language_code} Neural2 语音[/dim]"
        )

        return neural_voices

    def _synthesize_with_random_voice_sync(
        self,
        text: str,
        language_code: str = "en-US",
        audio_encoding: texttospeech_v1.AudioEncoding = texttospeech_v1.AudioEncoding.MP3,
        speaking_rate: float = 1.0,
        pitch: float = 0.0,
    ) -> Tuple[bytes, str]:
        """
        使用随机 Neural2 语音合成文本（同步版本）

        Args:
            text: 要合成的文本
            language_code: 语言代码
            audio_encoding: 音频编码格式（MP3, LINEAR16, OGG_OPUS 等）
            speaking_rate: 语速 (0.25 到 4.0，1.0 为正常)
            pitch: 音调 (-20.0 到 20.0，0.0 为正常)

        Returns:
            (音频内容, 使用的语音名称)
        """
        # 获取可用的 Neural2 语音
        available_voices = self.get_neural_voices(language_code)

        if not available_voices:
            raise ValueError(f"没有找到 {language_code} 的 Neural2 语音")

        # 随机选择一个语音
        selected_voice = random.choice(available_voices)

        # 配置合成输入
        synthesis_input = texttospeech_v1.SynthesisInput(text=text)

        # 使用选中的语音
        voice = texttospeech_v1.VoiceSelectionParams(
            language_code=language_code, name=selected_voice.name
        )

        # 配置音频输出
        audio_config = texttospeech_v1.AudioConfig(
            audio_encoding=audio_encoding, speaking_rate=speaking_rate, pitch=pitch
        )

        # 执行合成
        response = self._tts_cli.synthesize_speech(
            input=synthesis_input, voice=voice, audio_config=audio_config
        )

        return response.audio_content, selected_voice.name

    async def synthesize_with_random_voice(
        self,
        text: str,
        language_code: str = "en-US",
        audio_encoding: texttospeech_v1.AudioEncoding = texttospeech_v1.AudioEncoding.MP3,
        speaking_rate: float = 1.0,
        pitch: float = 0.0,
    ) -> Tuple[bytes, str]:
        """
        使用随机 Neural2 语音合成文本（异步版本）

        Args:
            text: 要合成的文本
            language_code: 语言代码
            audio_encoding: 音频编码格式（MP3, LINEAR16, OGG_OPUS 等）
            speaking_rate: 语速 (0.25 到 4.0，1.0 为正常)
            pitch: 音调 (-20.0 到 20.0，0.0 为正常)

        Returns:
            (音频内容, 使用的语音名称)
        """
        # Run synchronous TTS in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: self._synthesize_with_random_voice_sync(
                text, language_code, audio_encoding, speaking_rate, pitch
            ),
        )

    def _synthesize_with_specific_voice_sync(
        self,
        text: str,
        voice_name: str,
        language_code: str = "en-US",
        audio_encoding: texttospeech_v1.AudioEncoding = texttospeech_v1.AudioEncoding.MP3,
        speaking_rate: float = 1.0,
        pitch: float = 0.0,
    ) -> bytes:
        """
        使用指定语音合成文本（同步版本）

        Args:
            text: 要合成的文本
            voice_name: 语音名称，如 "en-US-Neural2-A"
            language_code: 语言代码
            audio_encoding: 音频编码格式
            speaking_rate: 语速
            pitch: 音调

        Returns:
            音频内容
        """
        synthesis_input = texttospeech_v1.SynthesisInput(text=text)

        voice = texttospeech_v1.VoiceSelectionParams(
            language_code=language_code, name=voice_name
        )

        audio_config = texttospeech_v1.AudioConfig(
            audio_encoding=audio_encoding, speaking_rate=speaking_rate, pitch=pitch
        )

        response = self._tts_cli.synthesize_speech(
            input=synthesis_input, voice=voice, audio_config=audio_config
        )

        return response.audio_content

    async def synthesize_with_specific_voice(
        self,
        text: str,
        voice_name: str,
        language_code: str = "en-US",
        audio_encoding: texttospeech_v1.AudioEncoding = texttospeech_v1.AudioEncoding.MP3,
        speaking_rate: float = 1.0,
        pitch: float = 0.0,
    ) -> bytes:
        """
        使用指定语音合成文本（异步版本）

        Args:
            text: 要合成的文本
            voice_name: 语音名称，如 "en-US-Neural2-A"
            language_code: 语言代码
            audio_encoding: 音频编码格式
            speaking_rate: 语速
            pitch: 音调

        Returns:
            音频内容
        """
        # Run synchronous TTS in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: self._synthesize_with_specific_voice_sync(
                text, voice_name, language_code, audio_encoding, speaking_rate, pitch
            ),
        )

    def clear_cache(self):
        """清除语音缓存"""
        self._neural_voices_cache.clear()
        rprint("[yellow] 已清除语音缓存[/yellow]")
