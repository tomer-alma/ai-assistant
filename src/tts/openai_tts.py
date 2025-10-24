from __future__ import annotations

import asyncio
import io
from typing import AsyncIterator

import httpx
from pydub import AudioSegment


class OpenAIStreamingTTS:
    """OpenAI TTS with buffered streaming and audio format conversion."""

    def __init__(self, api_key: str, model: str, voice: str, language: str) -> None:
        self._api_key = api_key
        self._model = model
        self._voice = voice
        self._language = language

    async def synth_stream(self, text_stream: AsyncIterator[str]) -> AsyncIterator[bytes]:
        """
        Collect complete LLM response, then synthesize in ONE call for smooth flowing audio.
        
        Single TTS call = no gaps/breaks = natural flowing speech.
        """
        # Collect entire text response
        buffer = []
        async for chunk in text_stream:
            buffer.append(chunk)
        
        # Synthesize the complete text in one shot for smooth audio
        full_text = ''.join(buffer).strip()
        if full_text:
            async for audio_chunk in self._synthesize_text(full_text):
                yield audio_chunk

    async def _synthesize_text(self, text: str) -> AsyncIterator[bytes]:
        """
        Call OpenAI TTS API and convert MP3 to PCM16 16kHz mono chunks.
        """
        if not text:
            return
        
        url = "https://api.openai.com/v1/audio/speech"
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": "tts-1",  # Use tts-1 for faster streaming (tts-1-hd for quality)
            "input": text,
            "voice": self._voice if self._voice in ["alloy", "echo", "fable", "onyx", "nova", "shimmer"] else "alloy",
            "response_format": "mp3",
            "speed": 1.0,
        }
        
        try:
            # Longer timeout for WSL2/network issues
            timeout = httpx.Timeout(60.0, connect=10.0)
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                
                # Get complete MP3 audio
                mp3_data = response.content
                
                # Convert MP3 to PCM16 16kHz mono
                audio = AudioSegment.from_mp3(io.BytesIO(mp3_data))
                audio = audio.set_frame_rate(16000).set_channels(1).set_sample_width(2)  # 16kHz, mono, 16-bit
                
                # Yield in 20ms chunks for smooth playback
                pcm_data = audio.raw_data
                chunk_size = int(16000 * 0.020 * 2)  # 20ms at 16kHz, 16-bit (2 bytes per sample)
                
                for i in range(0, len(pcm_data), chunk_size):
                    chunk = pcm_data[i:i + chunk_size]
                    if chunk:
                        # Pad last chunk if needed
                        if len(chunk) < chunk_size:
                            chunk += b'\x00' * (chunk_size - len(chunk))
                        yield chunk
                        # Minimal delay for cooperative multitasking
                        await asyncio.sleep(0.001)
                        
        except httpx.HTTPError as e:
            print(f"[TTS ERROR] Failed to synthesize: {e}")
            # Yield silence on error so playback doesn't hang
            yield b"\x00" * 640  # 20ms of silence
        except Exception as e:
            print(f"[TTS ERROR] Unexpected error: {e}")
            yield b"\x00" * 640

