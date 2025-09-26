from __future__ import annotations

from typing import AsyncIterator, Optional

import httpx


class OpenAIStreamingSTT:
    """Stub for streaming STT. Replace with actual OpenAI Realtime/Transcribe streaming."""

    def __init__(self, api_key: str, model: str, language: str) -> None:
        self._api_key = api_key
        self._model = model
        self._language = language

    async def transcribe_stream(self, audio_frames: AsyncIterator[bytes]) -> str:
        # TODO: Implement streaming transcription via OpenAI Audio API when available in SDK
        # For now, just return a placeholder
        _ = audio_frames
        return "שלום, זו דוגמת תמלול."

