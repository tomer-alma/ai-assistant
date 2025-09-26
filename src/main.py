from __future__ import annotations

import asyncio
import os
import signal
from typing import Optional, AsyncIterator

from dotenv import load_dotenv

from src.config.settings import load_settings
from src.utils.logging import configure_logging
from src.audio.capture import AudioCapture
from src.audio.vad import Endpointer
from src.audio.playback import AudioPlayback
from src.audio.wakeword import WakeWordDetector
from src.stt.openai_stt import OpenAIStreamingSTT
from src.llm.openai_llm import OpenAILLM
from src.tts.openai_tts import OpenAIStreamingTTS


async def _run() -> None:
    settings = load_settings()
    configure_logging(os.getenv("LOG_LEVEL", "INFO"))

    print("AI Assistant starting…")
    print(f"Language: STT={settings.language.stt_lang}, TTS={settings.language.tts_lang}")
    print(f"Models: STT={settings.models.stt}, LLM={settings.models.llm}, TTS={settings.models.tts}")

    # Components
    wake = WakeWordDetector(settings.wake.start_phrase, settings.wake.stop_phrase)
    capture = AudioCapture(
        sample_rate=settings.audio.sample_rate,
        channels=settings.audio.channels,
        device=settings.audio.device_input,
        frame_ms=settings.audio.vad_frame_ms,
    )
    endpointer = Endpointer(
        frame_ms=settings.audio.vad_frame_ms,
        sample_rate=settings.audio.sample_rate,
        finalize_silence_ms=settings.timeouts.stt_finalize_ms,
        aggressiveness=settings.audio.vad_aggressiveness,
    )
    stt = OpenAIStreamingSTT(
        api_key=os.environ.get("OPENAI_API_KEY", ""),
        model=settings.models.stt,
        language=settings.language.stt_lang,
    )
    llm = OpenAILLM(
        api_key=os.environ.get("OPENAI_API_KEY", ""),
        model=settings.models.llm,
        system_prompt=settings.language.style_prompt,
    )
    tts = OpenAIStreamingTTS(
        api_key=os.environ.get("OPENAI_API_KEY", ""),
        model=settings.models.tts,
        voice=settings.models.tts_voice,
        language=settings.language.tts_lang,
    )
    playback = AudioPlayback(
        sample_rate=settings.audio.sample_rate,
        channels=settings.audio.channels,
        device=settings.audio.device_output,
    )

    async def listen_once() -> bytes:
        # Gather one utterance worth of audio based on VAD endpointer
        collected: list[bytes] = []
        async for frame in capture.frames():
            is_speech, is_final = endpointer.process(frame)
            if is_speech:
                collected.append(frame)
            if is_final:
                break
        return b"".join(collected)

    while True:
        await wake.wait_for_wake()
        audio_bytes = await listen_once()

        async def one_shot_frames() -> AsyncIterator[bytes]:
            yield audio_bytes

        transcript = await stt.transcribe_stream(one_shot_frames())
        text_stream = llm.stream_reply(transcript)
        audio_stream = tts.synth_stream(text_stream)
        await playback.play_stream(audio_stream)


def main() -> None:
    load_dotenv()
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    stop: Optional[asyncio.Future[None]] = loop.create_future()

    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, lambda: (not stop.done()) and stop.set_result(None))

    async def runner() -> None:
        task = asyncio.create_task(_run())
        await stop
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    try:
        loop.run_until_complete(runner())
    finally:
        loop.close()


if __name__ == "__main__":
    main()

