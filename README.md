# AI Voice Assistant

A voice-powered AI assistant with Hebrew language support, built with OpenAI's APIs for speech-to-text (STT), language model (LLM), and text-to-speech (TTS).

## Features

- 🎤 **Voice Input**: Real-time speech recognition with voice activity detection (VAD)
- 🤖 **AI Conversations**: Natural conversations powered by GPT models
- 🔊 **Voice Output**: Text-to-speech with natural-sounding voices
- 🇮🇱 **Hebrew Support**: Full bidirectional text support for Hebrew
- 🎯 **Echo Cancellation**: Advanced echo prevention to avoid self-responses
- 👋 **Configurable Greetings**: Customizable opening and closing messages
- 🚪 **Voice Exit**: Say goodbye to exit gracefully
- ⚡ **Optimized Latency**: ~3-8 second response time (15-20% faster than baseline)

## Quick Start

### Prerequisites

- Python 3.10+
- OpenAI API key
- WSL2 with PulseAudio (for Linux/WSL users) or native audio support
- **For Raspberry Pi**: See [RASPBERRY_PI_SETUP.md](RASPBERRY_PI_SETUP.md) for detailed Pi 5 installation guide

### Installation

1. Clone the repository:
```bash
cd ~/ai-assistant
```

2. Create a virtual environment and install dependencies:
```bash
make install
```

3. Set up your OpenAI API key:
```bash
# Create a .env file
echo "OPENAI_API_KEY=your_api_key_here" > .env
```

Get your API key from: https://platform.openai.com/api-keys

### Running

```bash
make dev-run
```

The assistant will:
1. Greet you with a welcome message
2. Show "✅ Ready! You can speak now."
3. Listen for your voice input
4. Respond naturally in Hebrew

### Exiting

Say any of these words to exit:
- "להתראות" (goodbye)
- "ביי" (bye)
- "bye"
- "תפסיק" (stop)
- "סיום" (end)
- "עצור" (stop)
- "יציאה" (exit)

Or press `Ctrl+C` to interrupt.

## Configuration

All settings are in `src/config/default.yaml`. 

- See [CONFIGURATION.md](CONFIGURATION.md) for greeting/exit settings and echo tuning
- See [LATENCY_IMPROVEMENTS.md](LATENCY_IMPROVEMENTS.md) for performance optimization details

### Key Settings

```yaml
language:
  greeting: "שלום! אני כאן לעזור לך. במה אוכל לסייע?"
  closing: "להתראות! היה נעים לדבר איתך."
  style_prompt: "ענה בעברית קצר וברור, עד 4 משפטים."

models:
  stt: "gpt-4o-mini-transcribe"
  llm: "gpt-4o-mini"
  tts: "gpt-4o-mini-tts"
  tts_voice: "nova"

audio:
  vad_aggressiveness: 2  # 0-3: lower = less sensitive

timeouts:
  stt_finalize_ms: 600  # Silence duration before ending speech (lower = faster)
  post_greeting_settle_ms: 1000  # Echo prevention after greeting
  post_response_settle_ms: 300  # Echo prevention after each response (lower = faster)

debugging:
  show_latency: true  # Display performance metrics
```

## Troubleshooting

### ALSA Warnings

The ALSA warnings you see in WSL2 are normal and harmless:
```
ALSA lib confmisc.c:855:(parse_card) cannot find card '0'
```

Audio works through PulseAudio (`PULSE_SERVER=/mnt/wslg/PulseServer`), so you can safely ignore these messages.

### Echo Issues

If the assistant responds to itself:
- Wait for "🎤 Listening..." before speaking
- Lower your speaker volume
- Use headphones
- See [CONFIGURATION.md](CONFIGURATION.md) for advanced tuning

### First STT After Greeting

If the first speech recognition doesn't work well:
- Wait for both "✅ Ready!" and "🎤 Listening..." messages
- Increase `post_greeting_settle_ms` in `default.yaml` to 1500-2000

### API Timeouts

If you get connection timeouts:
- Check your internet connection
- Verify your OpenAI API key is valid
- The app has 60s timeout and 2 retries configured

## Project Structure

```
ai-assistant/
├── src/
│   ├── main.py              # Main conversation loop
│   ├── config/
│   │   ├── default.yaml     # Configuration file
│   │   └── settings.py      # Settings models
│   ├── audio/
│   │   ├── capture.py       # Audio input capture
│   │   ├── playback.py      # Audio output playback
│   │   └── vad.py           # Voice activity detection
│   ├── stt/
│   │   └── openai_stt.py    # Speech-to-text
│   ├── llm/
│   │   └── openai_llm.py    # Language model
│   └── tts/
│       └── openai_tts.py    # Text-to-speech
├── Makefile                 # Build commands
├── requirements.txt         # Python dependencies
└── README.md               # This file
```

## Development

### Available Make Commands

- `make venv` - Create virtual environment
- `make install` - Install all dependencies
- `make dev-run` - Run the assistant (WSL2/Linux with PulseAudio)
- `make pi-run` - Run the assistant (Raspberry Pi / native audio)
- `make clean` - Remove virtual environment

## License

MIT

## Credits

Built with OpenAI APIs, PyAudio, and WebRTC VAD.

