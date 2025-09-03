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

# Install uv if not already installed
if ! command -v uv &> /dev/null; then
    echo "Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    # Reload shell to get uv in PATH
    source ~/.bashrc 2>/dev/null || true
    source ~/.profile 2>/dev/null || true
fi

# Verify uv is available
if ! command -v uv &> /dev/null; then
    echo "Error: uv installation failed or not in PATH"
    echo "Please install uv manually: https://docs.astral.sh/uv/"
    exit 1
fi

UV_PATH=$(which uv)
echo "Found uv at: $UV_PATH"

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

# Create systemd service dynamically
echo "Creating systemd service..."
sudo tee /etc/systemd/system/cat-tv.service > /dev/null << EOF
[Unit]
Description=Cat TV - YouTube Entertainment System for Cats
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=$USER
Group=$USER
WorkingDirectory=$SCRIPT_DIR
Environment="PATH=/usr/bin:/usr/local/bin"
Environment="HOME=$HOME"
ExecStart=$UV_PATH run cat-tv
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

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
echo "To configure Raspberry Pi to boot to CLI mode:"
echo "  sudo raspi-config"
echo "  Select: 1 System Options > S5 Boot / Auto Login > B2 Console Autologin"
echo ""
echo "To start the service now:"
echo "  sudo systemctl start cat-tv"
echo ""
echo "Project installed in: $SCRIPT_DIR"
echo "Running as user: $USER"
echo ""
echo "Web interface will be available at:"
echo "  http://$(hostname -I | cut -d' ' -f1):8080"
echo ""
echo "To view logs:"
echo "  journalctl -u cat-tv -f"