from __future__ import annotations

import asyncio
import os
import signal
from typing import Optional

from dotenv import load_dotenv

from src.config.settings import load_settings
from src.utils.logging import configure_logging


async def _run() -> None:
    settings = load_settings()
    configure_logging(os.getenv("LOG_LEVEL", "INFO"))

    print("AI Assistant starting…")
    print(f"Language: STT={settings.language.stt_lang}, TTS={settings.language.tts_lang}")
    print(f"Models: STT={settings.models.stt}, LLM={settings.models.llm}, TTS={settings.models.tts}")

    # Placeholder: main loop will be implemented in next steps
    while True:
        await asyncio.sleep(1.0)


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

