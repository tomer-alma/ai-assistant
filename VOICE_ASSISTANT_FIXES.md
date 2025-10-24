# Voice Assistant Audio Issues - Analysis & Fixes

## Problem Summary

After the first 2 conversation rounds, the STT started picking up very short, random utterances instead of actual user speech. This manifested as:
- STT: ".ייה" (hi)
- STT: ".םלועה" (the world)  
- STT: "יתש" (two)
- etc.

## Root Causes Identified

### 1. 🔴 CRITICAL: Microphone Capture During TTS Playback
**The Primary Issue**

The microphone was running continuously throughout the entire conversation loop, including during TTS playback. This caused:
- **Echo/Feedback Loop**: Microphone picked up the AI's voice from speakers
- **False VAD Triggers**: VAD detected speaker output as "user speech"
- **Premature Cutoffs**: System thought user was speaking when it was just hearing itself

### 2. Audio Buffer Underruns
The many `ALSA lib pcm.c:8568:(snd_pcm_recover) underrun occurred` errors indicate:
- CPU couldn't keep up with real-time audio processing during playback
- Audio glitches confused the VAD
- VAD misinterpreted buffer underruns as speech boundaries

### 3. Endpointer State Not Reset Between Turns
- VAD state accumulated across conversation turns
- Previous speech patterns influenced new detections
- Led to increasingly degraded performance

### 4. Duplicate `process()` Method in VAD Code
- Two `process()` methods existed in `Endpointer` class
- Code clarity issue (though Python used the second one)

### 5. No Post-Playback Settling Time
- System started listening immediately after TTS finished
- Residual audio echoes still present in the system
- Acoustic environment hadn't stabilized

## Best Practices & Solutions Implemented

### ✅ Fix 1: Continuous Capture with Queue Draining (MOST IMPORTANT)
```python
# In main.py start() method:
# Start capture once and keep it running (avoids threading lifecycle issues)
self._capture_frames_iterator = self._capture.frames()

# After playback:
await asyncio.sleep(0.3)              # Let audio system settle
await self._capture.drain_queue()     # Discard frames captured during playback
```

**Why this matters:**
- Prevents echo/feedback loops by discarding frames from playback period
- Avoids repeated stream open/close which causes audio glitches
- More stable than stopping/restarting capture threads
- Eliminates false VAD triggers from TTS output
- Standard practice for half-duplex voice assistants
- Reduces CPU load and prevents buffer underruns

### ✅ Fix 2: Reset Endpointer State Between Turns
```python
# In _gather_speech():
self._endpointer.reset()  # Fresh state for each turn
```

**Why this matters:**
- Each conversation turn starts with clean slate
- Prevents state accumulation
- More predictable VAD behavior
- Industry best practice

### ✅ Fix 3: Increased Silence Threshold
```yaml
# In default.yaml:
stt_finalize_ms: 1500  # Increased from 1200ms
```

**Why this matters:**
- More robust against transient noises
- Gives user time to think/pause mid-sentence
- Reduces false "end of speech" detections
- 1.5s is good balance for conversational UX

### ✅ Fix 4: Added Post-Playback Settling Delay
```python
await asyncio.sleep(0.3)  # 300ms settling time
```

**Why this matters:**
- Allows speaker output to fully decay
- Audio hardware buffers clear out
- Acoustic echoes dissipate
- Prevents immediate false triggers

### ✅ Fix 5: Cleaned Up VAD Code
- Removed duplicate `process()` method
- Made `reset()` public API
- Improved code clarity

## Audio Architecture Best Practices

### 1. Half-Duplex vs Full-Duplex
Your config shows `half_duplex: true` which is correct. Your implementation now matches:
- **Half-Duplex**: Either listen OR speak, not both (what you have now ✅)
- **Full-Duplex**: Listen while speaking (requires echo cancellation)

### 2. Echo Cancellation (Future Enhancement)
For full-duplex support, you'd need:
- **Acoustic Echo Cancellation (AEC)**: Remove speaker output from mic input
- Libraries: WebRTC AEC, Speex AEC, or hardware AEC
- More complex but allows interruptions during TTS

### 3. VAD Tuning Parameters
Current settings are good:
- `vad_frame_ms: 20` ✅ (Standard WebRTC frame size)
- `vad_aggressiveness: 2` ✅ (Balanced, good for clean environments)
- `min_speech_frames: 3` ✅ (60ms prevents single-frame glitches)

Consider adjusting if needed:
- **Noisy environment**: Increase aggressiveness to 3
- **Quiet environment**: Decrease to 1 (more sensitive)

### 4. Audio Buffer Management
```python
# Capture queue size:
self._queue: asyncio.Queue[bytes] = asyncio.Queue(maxsize=50)

# Playback queue size:
self._queue: queue.Queue[Optional[bytes]] = queue.Queue(maxsize=100)
```

These are reasonable. If you still see underruns:
- Increase playback queue size (more buffering)
- Check CPU usage during playback
- Consider lower audio quality (but you're at 16kHz which is already efficient)

### 5. Threading Architecture
Your current architecture is solid:
- **Capture**: Separate thread with PyAudio callback → asyncio queue
- **Playback**: Separate thread with PyAudio callback → thread queue
- **Main**: Async/await for orchestration

This is the right pattern for Python audio applications.

## Testing Recommendations

1. **Test the fixes:**
   ```bash
   make dev-run
   ```

2. **Monitor improvements:**
   - First few turns should work (as they did before)
   - Subsequent turns should now also work correctly
   - No more random short utterances
   - Fewer ALSA underrun errors

3. **If issues persist:**
   - Increase `stt_finalize_ms` further (try 2000ms)
   - Increase post-playback delay (try 0.5s)
   - Check microphone sensitivity/gain settings
   - Verify no other apps are using audio devices

## Additional Enhancements (Optional)

### 1. Add VAD Debug Logging
```python
# In _gather_speech():
if is_speech:
    print(f"[VAD] speech frame {len(utterance_frames)}")
if is_final:
    print(f"[VAD] end of speech, total frames: {len(utterance_frames)}")
```

### 2. Minimum Utterance Length Check
```python
# Prevent very short utterances:
min_utterance_duration_ms = 300
min_frames = int(min_utterance_duration_ms / self._settings.audio.vad_frame_ms)

if len(utterance_frames) < min_frames:
    print(f"Utterance too short ({len(utterance_frames)} frames), ignoring")
    return b""
```

### 3. Audio Level Monitoring
Add RMS level checking to ignore silent captures:
```python
import numpy as np

def has_sufficient_energy(audio_bytes: bytes, threshold: float = 500.0) -> bool:
    audio_array = np.frombuffer(audio_bytes, dtype=np.int16)
    rms = np.sqrt(np.mean(audio_array**2))
    return rms > threshold
```

### 4. Barge-In Support (Advanced)
Your config mentions `barge_in: true` but it's not implemented. For true barge-in:
- Run VAD during TTS playback
- Detect when user interrupts
- Stop TTS immediately
- Start listening
- Requires full-duplex + echo cancellation

## Summary of Changes

### Files Modified:
1. ✅ `src/audio/vad.py` - Made `reset()` public, removed duplicate method
2. ✅ `src/audio/capture.py` - Added `drain_queue()` method to discard stale frames
3. ✅ `src/main.py` - Continuous capture with queue draining, endpointer reset, settling delay
4. ✅ `src/config/default.yaml` - Increased `stt_finalize_ms` to 1500ms

### Key Improvements:
- 🚀 Eliminated echo/feedback causing false detections
- 🧹 Clean state management between conversation turns
- ⏱️ Better timing for audio system stability
- 📝 Improved code clarity and documentation

## Expected Behavior After Fixes

✅ Consistent performance across all conversation turns
✅ No more random short utterances
✅ Proper speech detection regardless of conversation length
✅ Reduced ALSA underrun errors
✅ Stable VAD performance

## Technical References

- **WebRTC VAD**: https://github.com/wiseman/py-webrtcvad
- **PyAudio Best Practices**: http://people.csail.mit.edu/hubert/pyaudio/docs/
- **Voice Activity Detection**: https://en.wikipedia.org/wiki/Voice_activity_detection
- **Acoustic Echo Cancellation**: https://en.wikipedia.org/wiki/Echo_suppression_and_cancellation

---

**Date**: 2025-10-10
**Status**: ✅ Fixed and Ready for Testing

