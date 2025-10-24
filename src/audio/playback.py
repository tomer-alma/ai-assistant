from __future__ import annotations

import asyncio
import queue
import threading
from typing import AsyncIterator, Optional

import numpy as np
import pyaudio


class AudioPlayback:
    """Asynchronous PCM16 playback with small jitter buffer and optional fade-out."""

    def __init__(self, pa: pyaudio.PyAudio, sample_rate: int, channels: int, device: Optional[str]) -> None:
        self.sample_rate = sample_rate
        self.channels = channels
        self.device_name = device

        self._pa = pa
        self._device_index = self._find_device_index(device)
        self._queue: queue.Queue[Optional[bytes]] = queue.Queue(maxsize=100)
        self._running: bool = False
        self._thread: Optional[threading.Thread] = None
        self._loop = asyncio.get_running_loop()

    def _find_device_index(self, device_name: Optional[str]) -> Optional[int]:
        if not device_name or device_name == "default":
            return None
        for i in range(self._pa.get_device_count()):
            info = self._pa.get_device_info_by_index(i)
            if info.get("name") == device_name and info.get("maxOutputChannels") > 0:
                return i
        return None

    def _playback_thread(self, loop: asyncio.AbstractEventLoop) -> None:
        blocksize = int(self.sample_rate * 20 / 1000)

        def stream_callback(in_data, frame_count, time_info, status):
            try:
                chunk = self._queue.get(timeout=0.5)
                if chunk is None:  # Sentinel for stream end
                    return (None, pyaudio.paComplete)
                if len(chunk) < frame_count * self.channels * 2:
                    needed = frame_count * self.channels * 2 - len(chunk)
                    chunk += b"\x00" * needed
                return (chunk, pyaudio.paContinue)
            except queue.Empty:
                return (b"\x00" * frame_count * self.channels * 2, pyaudio.paContinue)

        stream = self._pa.open(
            format=pyaudio.paInt16,
            channels=self.channels,
            rate=self.sample_rate,
            output=True,
            frames_per_buffer=blocksize,
            output_device_index=self._device_index,
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

    async def play_stream(self, source: AsyncIterator[bytes]) -> None:
        """Consume an async stream of PCM16 frames and play them."""
        self._running = True
        self._thread = threading.Thread(target=self._playback_thread, args=(self._loop,))
        self._thread.start()

        async for chunk in source:
            if not self._running:
                break
            await self._loop.run_in_executor(None, self._queue.put, chunk)
        
        await self._loop.run_in_executor(None, self._queue.put, None)  # Sentinel
        if self._thread:
            await self._loop.run_in_executor(None, self._thread.join)

    async def stop(self) -> None:
        self._running = False
        try:
            self._queue.put_nowait(None)
        except queue.Full:
            pass
        if self._thread:
            await self._loop.run_in_executor(None, self._thread.join)
            self._thread = None

    async def fade_out_and_stop(self, duration_ms: int = 150) -> None:
        """Fade out queued audio and stop playback."""
        self._running = False
        # Create a temporary list to hold faded audio
        faded_audio: queue.Queue[Optional[bytes]] = queue.Queue()

        # Drain the original queue
        buffered = []
        while not self._queue.empty():
            try:
                buffered.append(self._queue.get_nowait())
            except queue.Empty:
                break
        
        # Apply fade-out
        steps = max(1, duration_ms // 20)
        full_buffer = b"".join(filter(None, buffered))
        
        arr = np.frombuffer(full_buffer, dtype=np.int16)
        
        for i in range(steps, 0, -1):
            factor = i / steps
            faded_chunk = (arr.astype(np.float32) * factor).astype(np.int16)
            faded_audio.put(faded_chunk.tobytes())

        # Clear the original queue and add the faded audio
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
            except queue.Empty:
                break
        
        while not faded_audio.empty():
            chunk = faded_audio.get_nowait()
            await self._loop.run_in_executor(None, self._queue.put, chunk)

        await self._loop.run_in_executor(None, self._queue.put, None)
        await self.stop()

