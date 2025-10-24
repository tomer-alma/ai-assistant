# AI Assistant Configuration

## Opening Greeting

The assistant can now greet you when it starts! Configure this in `src/config/default.yaml`:

```yaml
language:
  greeting: "שלום! אני כאן לעזור לך. במה אוכל לסייע?"
```

Change this to any greeting you like. The assistant will speak it once when starting, then begin listening.

**Important:** After the greeting, you'll see "✅ Ready! You can speak now." followed by "🎤 Listening...". 
Wait for both messages before speaking to ensure the greeting echo has fully cleared.

## Closing Greeting & Exit Keywords

The assistant will gracefully exit when you say any of the configured exit keywords:

```yaml
language:
  closing: "להתראות! היה נעים לדבר איתך."
  exit_keywords:
    - "להתראות"
    - "ביי"
    - "bye"
    - "תפסיק"
    - "סיום"
    - "עצור"
    - "יציאה"
```

**How to exit:**
1. Say any exit keyword (e.g., "להתראות" or "bye")
2. The assistant will speak the closing message
3. The application will shut down gracefully

You can customize both the closing message and the exit keywords to your preference.

### If First STT After Greeting Still Has Issues:

If the first speech recognition is still problematic, increase the settling time in `default.yaml`:

```yaml
timeouts:
  post_greeting_settle_ms: 1500  # Increase from 1000 to 1500 or 2000
```

Or use a shorter greeting to reduce echo duration.

---

# Echo Prevention Fixes

## Problem
The AI assistant was picking up its own TTS voice output as new user input, causing it to respond to itself.

## Solutions Applied

### 1. Extended Echo Cancellation (main.py)
- **Increased settling time**: 150ms → 500ms after TTS playback
- **Triple audio drain**: Drain audio queue 3 times with 100ms pauses between each
- **Endpointer reset**: Force reset VAD state after playback to clear lingering detections

### 2. Stricter Utterance Filtering (main.py)
- **Minimum utterance length**: 300ms → 600ms (30 frames @ 20ms each)
- This rejects short echo fragments that slip through

### 3. Reduced VAD Sensitivity (default.yaml)
- **Aggressiveness**: 3 → 2 (less likely to detect echo as speech)
- **Finalization timeout**: 600ms → 800ms (more patience before ending speech)

### 4. Better User Feedback
- Added emoji indicators: 🎤 Listening, 🤔 Thinking
- Clear message when utterances are filtered out

## Testing Tips

1. **Watch for the filter message**: When you see "⚠️ No speech detected (or filtered as echo)", the system is working correctly

2. **Speak clearly and fully**: The 600ms minimum means you need to speak at least that long

3. **Wait for "Listening"**: Don't speak while the assistant is responding

4. **If echo still occurs**:
   - Lower your speaker volume
   - Move microphone further from speakers
   - Consider using headphones

## Configuration Tuning

If you need to adjust sensitivity, edit `src/config/default.yaml`:

```yaml
audio:
  vad_aggressiveness: 2  # 0-3: lower = less sensitive, higher = more sensitive

timeouts:
  stt_finalize_ms: 800  # How long to wait for end of speech
```

Or edit `src/main.py`:

```python
min_frames = 30  # Minimum utterance length (frames × 20ms = duration)
```

