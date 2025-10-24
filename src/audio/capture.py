from __future__ import annotations

import asyncio
import threading
from typing import AsyncIterator, Optional

import pyaudio


class AudioCapture:
    """Asynchronous microphone capture yielding raw PCM16 frames.

    Produces frames of size frame_ms at sample_rate and channels.
    """

    def __init__(self, pa: pyaudio.PyAudio, sample_rate: int, channels: int, device: Optional[str], frame_ms: int = 20) -> None:
        self.sample_rate = sample_rate
        self.channels = channels
        self.device_name = device
        self.frame_ms = frame_ms

        self._pa = pa
        self._device_index = self._find_device_index(device)
        self._queue: asyncio.Queue[bytes] = asyncio.Queue(maxsize=50)
        self._running: bool = False
        self._thread: Optional[threading.Thread] = None
        self._loop = asyncio.get_running_loop()

    def _find_device_index(self, device_name: Optional[str]) -> Optional[int]:
        if not device_name or device_name == "default":
            return None
        for i in range(self._pa.get_device_count()):
            info = self._pa.get_device_info_by_index(i)
            if info.get("name") == device_name and info.get("maxInputChannels") > 0:
                return i
        # Fallback to default if not found
        return None

    def _capture_thread(self, loop: asyncio.AbstractEventLoop) -> None:
        blocksize = int(self.sample_rate * self.frame_ms / 1000)

        def _callback_wrapper(in_data):
            try:
                self._queue.put_nowait(in_data)
            except asyncio.QueueFull:
                pass

        def stream_callback(in_data, frame_count, time_info, status):
            if in_data:
                loop.call_soon_threadsafe(_callback_wrapper, in_data)
            return (None, pyaudio.paContinue)

        stream = self._pa.open(
            format=pyaudio.paInt16,
            channels=self.channels,
            rate=self.sample_rate,
            input=True,
            frames_per_buffer=blocksize,
            input_device_index=self._device_index,
            stream_callback=stream_callback,
        )

        stream.start_stream()
        while self._running and stream.is_active():
            future = asyncio.run_coroutine_threadsafe(asyncio.sleep(0.1), loop)
            try:
                future.result()
            except asyncio.CancelledError:
                break

        stream.stop_stream()
        stream.close()

    async def frames(self) -> AsyncIterator[bytes]:
        """Yield PCM16 frames as bytes (little-endian)."""
        self._running = True
        self._thread = threading.Thread(target=self._capture_thread, args=(self._loop,))
        self._thread.start()

        while self._running:
            try:
                chunk = await asyncio.wait_for(self._queue.get(), timeout=1.0)
                yield chunk
            except asyncio.TimeoutError:
                if not self._running:
                    break

    async def drain_queue(self) -> None:
        """Drain all pending frames from the queue without processing them."""
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
            except asyncio.QueueEmpty:
                break

    async def stop(self) -> None:
        self._running = False
        if self._thread:
            await self._loop.run_in_executor(None, self._thread.join)
            self._thread = None

