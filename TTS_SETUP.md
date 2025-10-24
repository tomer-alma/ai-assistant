# TTS Setup Instructions

## Issue Found
The TTS was just a stub outputting **silence** - it wasn't actually calling OpenAI's API!

## What Was Fixed
✅ Implemented real OpenAI TTS API integration  
✅ Buffered sentence-by-sentence synthesis for natural flow  
✅ MP3 to PCM16 audio conversion (16kHz mono)  
✅ Proper error handling with fallback to silence  
✅ Changed voice from invalid "kids_friendly_1" to "nova"  

## Installation Steps

### 1. Install pydub
```bash
make install
```

### 2. Install ffmpeg (Required for MP3 decoding)

**For WSL/Ubuntu:**
```bash
sudo apt-get update
sudo apt-get install -y ffmpeg
```

**Verify installation:**
```bash
ffmpeg -version
```

### 3. Verify OpenAI API Key
Make sure your `.env` file has:
```bash
OPENAI_API_KEY=sk-...your-key-here...
```

### 4. Run the Assistant
```bash
make dev-run
```

## Available Voices

You can change the voice in `src/config/default.yaml`:

```yaml
tts_voice: "nova"  # Current: warm and friendly
```

**OpenAI TTS Voices:**
- `alloy` - Neutral, balanced
- `echo` - Male, clear
- `fable` - British accent, expressive
- `onyx` - Deep male voice
- `nova` - Warm, friendly (good for kids) ✅ **Current**
- `shimmer` - Soft, gentle

## How It Works

### Text Buffering
- Collects tokens from LLM stream
- Synthesizes complete sentences for natural pacing
- Triggers on sentence endings (`.!?`) or 100+ characters

### Audio Pipeline
1. **Text** → OpenAI TTS API (HTTP request)
2. **MP3** response → pydub decoding
3. **WAV** → PCM16 16kHz mono conversion
4. **PCM16** → 20ms chunks → AudioPlayback queue
5. **Speakers** 🔊

### Performance Notes
- Uses `tts-1` model for speed (latency ~1-2s per sentence)
- For higher quality: change to `tts-1-hd` in code (line 61)
- Sentence buffering prevents word-by-word API calls
- 10ms delay between chunks prevents buffer issues

## Testing

You should now hear:
✅ **Actual Hebrew TTS output** on your speakers
✅ Clear, natural speech synthesis
✅ No more silence/underruns

## Troubleshooting

### No audio output?
```bash
# Check ffmpeg
ffmpeg -version

# Check audio devices
pactl list short sinks

# Check environment variable
echo $PULSE_SERVER
```

### "ffmpeg not found" error?
```bash
# Install ffmpeg
sudo apt-get install -y ffmpeg libavcodec-extra
```

### Poor audio quality?
```python
# In src/tts/openai_tts.py line 61, change:
"model": "tts-1-hd",  # Higher quality, slightly slower
```

### TTS too slow?
```python
# In src/tts/openai_tts.py line 65, change:
"speed": 1.1,  # Speed up by 10%
```

### Different voice needed?
Edit `src/config/default.yaml`:
```yaml
tts_voice: "shimmer"  # Try different voices
```

## Cost Considerations

OpenAI TTS pricing (as of 2024):
- **tts-1**: $0.015 per 1,000 characters (~$0.001 per response)
- **tts-1-hd**: $0.030 per 1,000 characters (~$0.002 per response)

Very affordable for a kids' assistant! 🎉

