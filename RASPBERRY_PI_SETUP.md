# Raspberry Pi 5 Setup Guide

This guide covers installing and running the AI Voice Assistant on Raspberry Pi 5 with a USB microphone and JBL speaker.

## Hardware Requirements

- **Raspberry Pi 5** (4GB+ RAM recommended)
- **USB Microphone** (same as your current setup)
- **JBL Speaker** (connected via USB, 3.5mm jack, or Bluetooth)
- **Internet Connection** (for OpenAI API calls)
- **MicroSD Card** (32GB+ recommended)

## Prerequisites

1. **Install Raspberry Pi OS** (64-bit recommended):
   - Use Raspberry Pi Imager to install Raspberry Pi OS (Bookworm or later)
   - Enable SSH if you want remote access
   - Complete initial setup and connect to internet

2. **Update System**:
   ```bash
   sudo apt update && sudo apt upgrade -y
   ```

## Installation Steps

### 1. Install System Dependencies

```bash
# Install audio libraries
sudo apt install -y \
    portaudio19-dev \
    python3-pyaudio \
    python3-dev \
    python3-pip \
    python3-venv \
    alsa-utils \
    pulseaudio \
    pulseaudio-utils
```

### 2. Identify Your Audio Devices

```bash
# List available audio devices
arecord -l  # Input devices
aplay -l    # Output devices

# Or use PulseAudio commands
pactl list sources short   # Input
pactl list sinks short     # Output
```

Take note of your:
- **Microphone device name/number**
- **JBL speaker device name/number**

### 3. Clone and Install the Project

```bash
# Clone the repository
cd ~
git clone https://github.com/tomer-alma/ai-assistant.git
cd ai-assistant

# Create virtual environment and install dependencies
make install
```

### 4. Configure OpenAI API Key

```bash
# Create .env file with your API key
echo "OPENAI_API_KEY=your_actual_api_key_here" > .env
```

Get your API key from: https://platform.openai.com/api-keys

### 5. Update Makefile for Raspberry Pi

The Makefile needs to be modified to remove the WSL2-specific PulseAudio server path:

```bash
# Edit the Makefile
nano Makefile
```

Change line 14 from:
```makefile
dev-run:
	. .venv/bin/activate && PULSE_SERVER=/mnt/wslg/PulseServer python -m src.main
```

To:
```makefile
dev-run:
	. .venv/bin/activate && python -m src.main
```

### 6. Configure Audio Devices

Edit `src/config/default.yaml` to set your audio devices:

```bash
nano src/config/default.yaml
```

Update the audio section:

```yaml
audio:
  sample_rate: 16000
  channels: 1
  device_input: null   # or specific device index/name
  device_output: null  # or specific device index/name
  vad_frame_ms: 20
  vad_aggressiveness: 2
```

**Device Configuration Options:**

- **Option 1 - Use default devices** (recommended for first try):
  ```yaml
  device_input: null
  device_output: null
  ```

- **Option 2 - Use PulseAudio (if available)**:
  ```yaml
  device_input: "pulse"
  device_output: "pulse"
  ```

- **Option 3 - Use specific device index** (find index using `arecord -l` / `aplay -l`):
  ```yaml
  device_input: 1  # Your microphone device index
  device_output: 0  # Your JBL speaker device index
  ```

### 7. Test the Installation

```bash
# Run the assistant
make dev-run
```

If you encounter audio device errors, try:

1. **List PyAudio devices**:
   ```bash
   .venv/bin/python -c "import pyaudio; pa = pyaudio.PyAudio(); [print(f'{i}: {pa.get_device_info_by_index(i)[\"name\"]}') for i in range(pa.get_device_count())]"
   ```

2. **Update device indices** in `default.yaml` based on the output above

3. **Test microphone**:
   ```bash
   # Record a test (press Ctrl+C after a few seconds)
   arecord -d 5 -f cd test.wav
   # Play it back
   aplay test.wav
   ```

## Running as a System Service (Auto-start on Boot)

### 1. Deploy to System Directory

```bash
# Copy project to /opt
sudo mkdir -p /opt/ai-assistant
sudo cp -r ~/ai-assistant/* /opt/ai-assistant/
sudo chown -R $USER:$USER /opt/ai-assistant

# Ensure .env file is present
sudo cp ~/ai-assistant/.env /opt/ai-assistant/.env
```

### 2. Install Systemd Service

```bash
# Copy service file
sudo cp /opt/ai-assistant/systemd/ai-assistant.service /etc/systemd/system/

# Reload systemd
sudo systemctl daemon-reload

# Enable and start the service
sudo systemctl enable ai-assistant
sudo systemctl start ai-assistant

# Check status
sudo systemctl status ai-assistant
```

### 3. View Logs

```bash
# Follow live logs
sudo journalctl -u ai-assistant -f

# View recent logs
sudo journalctl -u ai-assistant -n 100
```

## Troubleshooting

### Audio Device Not Found

```bash
# Check if PulseAudio is running
pulseaudio --check
echo $?  # Should output 0 if running

# If not running, start it
pulseaudio --start

# List devices again
pactl list sinks short
pactl list sources short
```

### Permission Issues

```bash
# Add user to audio group
sudo usermod -a -G audio $USER

# Reboot to apply
sudo reboot
```

### No Sound from JBL Speaker

```bash
# Set default output device
pactl set-default-sink <your-jbl-device-name>

# Or use alsamixer to adjust volume/settings
alsamixer
```

### High CPU Usage

If the Raspberry Pi 5 struggles with performance:

1. **Reduce audio sample rate** in `default.yaml`:
   ```yaml
   audio:
     sample_rate: 16000  # Already optimal
   ```

2. **Disable latency metrics**:
   ```yaml
   debugging:
     show_latency: false
   ```

3. **Use lighter models** (if needed, though gpt-4o-mini is already efficient)

### Microphone Not Sensitive Enough

```bash
# Use alsamixer to increase microphone gain
alsamixer
# Press F4 to select Capture device
# Use arrow keys to adjust levels
# Press Esc when done
```

Or adjust VAD aggressiveness in `default.yaml`:
```yaml
audio:
  vad_aggressiveness: 1  # Lower = more sensitive (0-3)
```

### First STT After Greeting Fails

Increase settling time in `default.yaml`:
```yaml
timeouts:
  post_greeting_settle_ms: 1500  # Give more time for echo to clear
```

## Performance Notes

- **Raspberry Pi 5** has excellent performance for this application
- Expected response time: 3-8 seconds (including network latency)
- CPU usage should be low (<20%) when idle, moderate during processing
- RAM usage: ~200-400MB

## Network Requirements

- Stable internet connection required for OpenAI API calls
- Bandwidth: ~50-100 KB/s per request
- Latency: Lower internet latency = faster responses

## Updating the Application

```bash
cd /opt/ai-assistant
git pull origin main
.venv/bin/pip install -r requirements.txt --upgrade
sudo systemctl restart ai-assistant
```

## Security Recommendations

1. **Protect your API key**:
   ```bash
   chmod 600 /opt/ai-assistant/.env
   ```

2. **Monitor API usage**: Check your OpenAI dashboard regularly

3. **Set spending limits**: Configure billing limits in OpenAI account

## Additional Features for Raspberry Pi

### Wake Word (Future Enhancement)

The project previously had wake word functionality (removed). If you want to add it back for always-on listening on your Pi, you could integrate:
- Porcupine Wake Word
- Snowboy (deprecated but still works)
- Custom wake word detection

### Physical Button Trigger

Add a physical button to trigger listening:

```python
# Example using GPIO (requires RPi.GPIO or gpiozero)
from gpiozero import Button

button = Button(2)  # GPIO pin 2
button.when_pressed = start_listening
```

## Support

For issues specific to Raspberry Pi deployment, check:
- System logs: `sudo journalctl -u ai-assistant`
- Audio system: `arecord -l`, `aplay -l`
- Audio server: `pulseaudio --check`

For general application issues, see the main [README.md](README.md).

