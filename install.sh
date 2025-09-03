#!/bin/bash
set -e

echo "Cat TV Installation Script"
echo "=========================="

# Check if running on Raspberry Pi
if [ ! -f /proc/device-tree/model ]; then
    echo "Warning: This doesn't appear to be a Raspberry Pi"
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Update system
echo "Updating system packages..."
sudo apt-get update
sudo apt-get upgrade -y

# Install required system packages
echo "Installing system dependencies..."
sudo apt-get install -y \
    vlc \
    python3-pip \
    python3-venv \
    git \
    curl

# Get the actual non-root user first
ACTUAL_USER=${SUDO_USER:-$USER}
ACTUAL_USER_HOME=$(getent passwd "$ACTUAL_USER" | cut -d: -f6)

# Check if uv is installed (check common locations)
UV_FOUND=0
UV_PATH=""

# Check if uv is in PATH
if command -v uv &> /dev/null; then
    UV_PATH=$(which uv)
    UV_FOUND=1
# Check common installation locations
elif [ -x "$ACTUAL_USER_HOME/.local/bin/uv" ]; then
    UV_PATH="$ACTUAL_USER_HOME/.local/bin/uv"
    UV_FOUND=1
elif [ -x "/usr/local/bin/uv" ]; then
    UV_PATH="/usr/local/bin/uv"
    UV_FOUND=1
fi

if [ $UV_FOUND -eq 0 ]; then
    echo "Error: uv is not installed"
    echo ""
    echo "Please install uv first:"
    echo "  Visit: https://docs.astral.sh/uv/getting-started/installation/"
    echo "  Or run: curl -LsSf https://astral.sh/uv/install.sh | sh"
    echo ""
    echo "After installing uv, run this script again."
    exit 1
fi

echo "Found uv at: $UV_PATH"

# Validate UV path is accessible by the target user
if [ -n "$SUDO_USER" ]; then
    if ! sudo -u "$ACTUAL_USER" test -x "$UV_PATH"; then
        echo "Error: UV at $UV_PATH is not accessible by user $ACTUAL_USER"
        echo "Please install UV as user $ACTUAL_USER (not as root)"
        exit 1
    fi
else
    if ! test -x "$UV_PATH"; then
        echo "Error: UV at $UV_PATH is not accessible"
        exit 1
    fi
fi

echo "UV validated for user: $ACTUAL_USER"

# Get the current directory (where the script is located)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_NAME="$(basename "$SCRIPT_DIR")"

echo "Installing Cat TV from: $SCRIPT_DIR"

# Ensure we're in the project directory
cd "$SCRIPT_DIR"

# Install Python dependencies with uv
echo "Installing Python dependencies..."
uv sync

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "Creating .env file..."
    cat > .env << EOF
# YouTube API Key (optional, for better search results)
YOUTUBE_API_KEY=

# Flask settings
FLASK_HOST=0.0.0.0
FLASK_PORT=8080
SECRET_KEY=$(openssl rand -hex 32)

# Player settings
PLAYER_BACKEND=vlc
AUDIO_OUTPUT=all

# Debug mode
DEBUG=False
EOF
    echo "Please edit .env file to add your YouTube API key (optional)"
fi

# Create required directories
mkdir -p data logs

# Initialize database
echo "Initializing database..."
uv run python -c "from src.cat_tv.models import init_db; init_db()"

# Get user ID for runtime directory
ACTUAL_USER_ID=$(id -u "$ACTUAL_USER")

echo "Installing for user: $ACTUAL_USER"
echo "User home directory: $ACTUAL_USER_HOME"

# Add user to required groups for hardware access
echo "Adding user to video, audio, and render groups..."
sudo usermod -a -G video,audio,render $ACTUAL_USER

# Enable PipeWire for the user (modern audio system)
echo "Enabling PipeWire audio system for user $ACTUAL_USER..."
# Use loginctl to ensure user session exists before managing user services
sudo loginctl enable-linger $ACTUAL_USER
# Set up proper environment for user systemctl commands
sudo -u $ACTUAL_USER XDG_RUNTIME_DIR=/run/user/$ACTUAL_USER_ID systemctl --user enable pipewire pipewire-pulse
sudo -u $ACTUAL_USER XDG_RUNTIME_DIR=/run/user/$ACTUAL_USER_ID systemctl --user start pipewire pipewire-pulse

# Create PipeWire configuration for multiple audio outputs
echo "Setting up multi-output audio configuration..."
sudo -u $ACTUAL_USER mkdir -p "$ACTUAL_USER_HOME/.config/pipewire/pipewire.conf.d"
sudo -u $ACTUAL_USER tee "$ACTUAL_USER_HOME/.config/pipewire/pipewire.conf.d/99-cat-tv.conf" > /dev/null << 'EOF'
# Cat TV multi-output audio configuration
context.modules = [
    {
        name = libpipewire-module-combine-stream
        args = {
            combine.mode = sink
            node.name = "cat_tv_combined"
            node.description = "Cat TV All Audio Outputs"
            combine.latency-compensate = false
            combine.props = {
                audio.position = [ FL FR ]
            }
            stream.props = {
            }
            stream.rules = [
                {
                    matches = [
                        {
                            node.name = "~alsa_output.*"
                        }
                    ]
                    actions = {
                        create-stream = {
                            combine.audio.position = [ FL FR ]
                            audio.position = [ FL FR ]
                        }
                    }
                }
            ]
        }
    }
]
EOF

# Restart PipeWire to load the new configuration
echo "Restarting PipeWire to load multi-output configuration..."
sudo -u $ACTUAL_USER XDG_RUNTIME_DIR=/run/user/$ACTUAL_USER_ID systemctl --user restart pipewire pipewire-pulse

# Wait a moment for PipeWire to stabilize
sleep 3

# Verify the combined sink was created
echo "Verifying combined sink creation..."
sudo -u $ACTUAL_USER XDG_RUNTIME_DIR=/run/user/$ACTUAL_USER_ID pactl list sinks short | grep cat_tv_combined || echo "Combined sink not found - will be created on first PipeWire restart"

# Create systemd service with simpler configuration
echo "Creating systemd service..."
sudo tee /etc/systemd/system/cat-tv.service > /dev/null << EOF
[Unit]
Description=Cat TV - YouTube Entertainment System for Cats
After=network.target
Wants=network.target

[Service]
Type=simple
User=$ACTUAL_USER
Group=$ACTUAL_USER
WorkingDirectory=$SCRIPT_DIR
ExecStart=$UV_PATH run cat-tv
Restart=always
RestartSec=10

# Environment variables
Environment=HOME=$ACTUAL_USER_HOME
Environment=USER=$ACTUAL_USER
Environment=XDG_RUNTIME_DIR=/run/user/$ACTUAL_USER_ID
Environment=DISPLAY=:0

# Standard output/error logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=cat-tv

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd and enable service
sudo systemctl daemon-reload
sudo systemctl enable cat-tv.service

echo ""
echo "Installation complete!"
echo "====================="
echo ""
echo "IMPORTANT: You may need to log out and back in for group changes to take effect!"
echo ""
echo "Audio is configured to output to ALL available interfaces simultaneously."
echo "To change audio output, edit .env and set AUDIO_OUTPUT to:"
echo "  - hdmi: HDMI audio only"
echo "  - local: Headphone jack only"
echo "  - all: All audio interfaces simultaneously"
echo ""
echo "To configure Raspberry Pi to boot to CLI mode:"
echo "  sudo raspi-config"
echo "  Select: 1 System Options > S5 Boot / Auto Login > B2 Console Autologin"
echo ""
echo "To start the service now:"
echo "  sudo systemctl start cat-tv"
echo ""
echo "Project installed in: $SCRIPT_DIR"
echo "Service will run as user: $ACTUAL_USER"
echo "User groups: $(groups $ACTUAL_USER)"
echo ""
echo "Web interface will be available at:"
echo "  http://$(hostname -I | cut -d' ' -f1):8080"
echo ""
echo "To view logs:"
echo "  journalctl -u cat-tv -f"