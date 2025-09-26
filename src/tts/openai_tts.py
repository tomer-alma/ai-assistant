from __future__ import annotations

from typing import AsyncIterator

import httpx


class OpenAIStreamingTTS:
    """Stub streaming TTS; replace with OpenAI TTS streaming when available in SDK."""

    def __init__(self, api_key: str, model: str, voice: str, language: str) -> None:
        self._api_key = api_key
        self._model = model
        self._voice = voice
        self._language = language

    async def synth_stream(self, text_stream: AsyncIterator[str]) -> AsyncIterator[bytes]:
        # TODO: Implement streaming TTS. For now, this yields silence frames as placeholder.
        _ = self
        async for _chunk in text_stream:
            yield b"\x00" * 640  # 20ms of silence at 16kHz mono 16-bit

