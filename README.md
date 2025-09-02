# Cat TV 2.0 - Raspberry Pi YouTube Entertainment System

An automated YouTube video player for Raspberry Pi that plays cat entertainment videos during specified times of day. Features a web interface for easy management of channels and schedules.

## Features

- **CLI-First Design**: Runs without desktop environment for maximum reliability
- **Web Interface**: Manage channels and schedules from any device on your network
- **Automatic Scheduling**: Play videos only during specified hours
- **Video Rotation**: Prevents screen burn-in by rotating between channels
- **Fallback Videos**: Automatically finds alternative videos if channels fail
- **Logging**: Comprehensive logging for debugging and monitoring
- **Auto-Recovery**: Automatically recovers from errors and network issues

## Requirements

- Raspberry Pi (any model with HDMI output)
- Raspberry Pi OS (Lite recommended)
- Internet connection
- HDMI display/TV
- Python 3.9+

## Quick Installation

1. **SSH into your Raspberry Pi** or open a terminal

2. **Clone the repository**:
```bash
git clone https://github.com/yourusername/cat_tv.git
cd cat_tv
```

3. **Run the installer**:
```bash
chmod +x install.sh
./install.sh
```

4. **Configure environment** (optional):
```bash
cp .env.example .env
nano .env  # Add YouTube API key for better search results
```

5. **Start the service**:
```bash
sudo systemctl start cat-tv
```

## Manual Installation

### 1. Install System Dependencies

```bash
sudo apt-get update
sudo apt-get install -y vlc python3-pip python3-venv git curl
```

### 2. Install UV Package Manager

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 3. Install Python Dependencies

```bash
uv sync
```

### 4. Configure Environment

```bash
cp .env.example .env
# Edit .env with your settings
```

### 5. Initialize Database

```bash
uv run python -c "from src.cat_tv.models import init_db; init_db()"
```

### 6. Install Systemd Service

```bash
sudo cp systemd/cat-tv.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable cat-tv
```

## Configuration

### Configure Raspberry Pi for CLI Boot

For best performance, configure your Pi to boot directly to CLI:

```bash
sudo raspi-config
```
Navigate to: `System Options > Boot / Auto Login > Console Autologin`

### Environment Variables

Edit `.env` file to configure:

- `YOUTUBE_API_KEY`: Optional, for better search results
- `PLAYER_BACKEND`: Choose between `vlc`, `omxplayer`, or `mpv`
- `AUDIO_OUTPUT`: Set to `hdmi`, `local`, or `both`
- `FLASK_PORT`: Web interface port (default: 5000)

## Usage

### Web Interface

Access the web interface at:
```
http://[raspberry-pi-ip]:5000
```

Features:
- **Dashboard**: View current status and control playback
- **Channels**: Add YouTube channels or search queries
- **Schedules**: Set when videos should play
- **History**: View playback history

### Command Line

Start the complete Cat TV application (includes scheduler + web interface):
```bash
uv run cat-tv
```

### Systemd Commands

```bash
# Start service
sudo systemctl start cat-tv

# Stop service
sudo systemctl stop cat-tv

# View logs
journalctl -u cat-tv -f

# Check status
sudo systemctl status cat-tv
```

## Default Schedule

By default, Cat TV plays videos:
- **Morning**: 7:00 AM - 11:00 AM
- **Evening**: 5:00 PM - 8:00 PM

Modify these times through the web interface.

## Default Channels

The system comes with pre-configured channels for cat entertainment:
1. Cat TV - Birds and Squirrels (4K)
2. Cat TV - Mice and Games
3. Paul Dinning Wildlife

Add your own channels through the web interface!

## Troubleshooting


### Videos won't play
- Check VLC is installed: `which cvlc`
- Verify internet connection: `ping youtube.com`
- Check logs: `journalctl -u cat-tv -n 50`

### Web interface not accessible
- Check firewall: `sudo ufw allow 5000`
- Verify service is running: `sudo systemctl status cat-tv`
- Check IP address: `hostname -I`

### No audio
- Check audio output setting in `.env`
- Test audio: `speaker-test -t wav -c 2`
- For HDMI: `sudo raspi-config` > Advanced Options > Audio > Force HDMI

## Development

### Project Structure
```
cat_tv/
├── src/cat_tv/
│   ├── __init__.py
│   ├── main.py           # Main scheduler entry point
│   ├── web.py            # Flask web interface
│   ├── config.py         # Configuration management
│   ├── player.py         # Video player control
│   ├── youtube.py        # YouTube integration
│   ├── scheduler.py      # Schedule management
│   ├── models/           # Database models
│   └── templates/        # Web interface templates
├── systemd/              # Service files
├── data/                 # Database and local data
├── logs/                 # Log files
└── pyproject.toml        # Project configuration
```

### Running Tests
```bash
uv run pytest
```

### Contributing

Pull requests welcome! Please ensure:
- Code follows existing style
- Tests pass
- Documentation is updated

## License

MIT License - See LICENSE file for details

## Acknowledgments

- Original Node.js version for inspiration
- yt-dlp for YouTube video extraction
- Flask for the web framework
- VLC for reliable video playback