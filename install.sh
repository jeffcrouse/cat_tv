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

# Check if uv is installed (don't install it automatically)
if ! command -v uv &> /dev/null; then
    echo "Error: uv is not installed or not in PATH"
    echo ""
    echo "Please install uv first:"
    echo "  Visit: https://docs.astral.sh/uv/getting-started/installation/"
    echo "  Or run: curl -LsSf https://astral.sh/uv/install.sh | sh"
    echo ""
    echo "After installing uv, run this script again."
    exit 1
fi

# Get UV path for the actual user (not root)
if [ -n "$SUDO_USER" ]; then
    # Running with sudo, check user's UV installation
    UV_PATH=$(sudo -u "$ACTUAL_USER" which uv 2>/dev/null)
    if [ -z "$UV_PATH" ]; then
        # Try common user locations
        if [ -x "$ACTUAL_USER_HOME/.local/bin/uv" ]; then
            UV_PATH="$ACTUAL_USER_HOME/.local/bin/uv"
        elif [ -x "/usr/local/bin/uv" ]; then
            UV_PATH="/usr/local/bin/uv"
        fi
    fi
else
    UV_PATH=$(which uv)
fi

echo "Found uv at: $UV_PATH for user: $ACTUAL_USER"

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
AUDIO_OUTPUT=hdmi

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

# Get the actual non-root user (in case script is run with sudo)
ACTUAL_USER=${SUDO_USER:-$USER}
ACTUAL_USER_HOME=$(getent passwd "$ACTUAL_USER" | cut -d: -f6)
ACTUAL_USER_ID=$(id -u "$ACTUAL_USER")

echo "Installing for user: $ACTUAL_USER"
echo "User home directory: $ACTUAL_USER_HOME"

# Add user to required groups for hardware access
echo "Adding user to video, audio, and render groups..."
sudo usermod -a -G video,audio,render $ACTUAL_USER

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