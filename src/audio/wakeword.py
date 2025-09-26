from __future__ import annotations

import asyncio


class WakeWordDetector:
    """Placeholder wake-word detector; replace with openwakeword integration."""

    def __init__(self, start_phrase: str, stop_phrase: str) -> None:
        self.start_phrase = start_phrase
        self.stop_phrase = stop_phrase

    async def wait_for_wake(self) -> None:
        # TODO: integrate openwakeword; placeholder short sleep
        await asyncio.sleep(0.5)

    def is_stop(self, text: str) -> bool:
        return self.stop_phrase in (text or "")

