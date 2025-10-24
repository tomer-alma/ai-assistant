from __future__ import annotations

import io
import wave
from typing import AsyncIterator, Optional

from openai import OpenAI
import httpx


class OpenAIStreamingSTT:
    """Stub for streaming STT. Replace with actual OpenAI Realtime/Transcribe streaming."""

    def __init__(
        self,
        api_key: str,
        model: str,
        language: Optional[str],
        sample_rate: int,
        channels: int,
    ) -> None:
        # Configure with longer timeout for WSL2/network issues
        self._client = OpenAI(
            api_key=api_key,
            timeout=httpx.Timeout(60.0, connect=10.0),
            max_retries=2
        )
        self._model = model
        self._language = language
        self._sample_rate = sample_rate
        self._channels = channels

    async def transcribe_stream(self, audio_frames: AsyncIterator[bytes]) -> str:
        """Collects audio frames, creates in-memory WAV file, and transcribes."""
        full_audio = b"".join([frame async for frame in audio_frames])
        if not full_audio:
            return ""

        try:
            # Use in-memory buffer instead of temp file for faster processing
            wav_buffer = io.BytesIO()
            with wave.open(wav_buffer, "wb") as wf:
                wf.setnchannels(self._channels)
                wf.setsampwidth(2)  # 16-bit PCM
                wf.setframerate(self._sample_rate)
                wf.writeframes(full_audio)
            
            # Reset buffer position to beginning
            wav_buffer.seek(0)
            
            # OpenAI API needs a file-like object with a name attribute
            wav_buffer.name = "audio.wav"
            
            resp = self._client.audio.transcriptions.create(
                model=self._model,
                file=wav_buffer,
                language=self._language,
            )
            return resp.text or ""
        except Exception as e:
            print(f"STT Error: {e}")
            return ""

