"""Configuration management for Cat TV."""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Application configuration."""
    
    # Base paths
    BASE_DIR = Path(__file__).resolve().parent.parent.parent
    DATA_DIR = BASE_DIR / "data"
    LOG_DIR = BASE_DIR / "logs"
    
    # Database
    DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DATA_DIR}/cat_tv.db")
    
    # Flask settings
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
    FLASK_HOST = os.getenv("FLASK_HOST", "0.0.0.0")
    FLASK_PORT = int(os.getenv("FLASK_PORT", "5000"))
    DEBUG = os.getenv("DEBUG", "False").lower() == "true"
    
    # YouTube settings
    YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "")
    
    # Video player settings
    PLAYER_BACKEND = os.getenv("PLAYER_BACKEND", "vlc")  # vlc, omxplayer, or mpv
    FULLSCREEN = True
    AUDIO_OUTPUT = os.getenv("AUDIO_OUTPUT", "hdmi")  # hdmi, local, or both
    
    # Display settings
    DISPLAY_TIMEOUT = int(os.getenv("DISPLAY_TIMEOUT", "30"))  # seconds between videos
    ROTATION_INTERVAL = int(os.getenv("ROTATION_INTERVAL", "3600"))  # seconds
    
    # Raspberry Pi specific
    IS_RASPBERRY_PI = os.path.exists("/proc/device-tree/model")
    USE_VCGENCMD = IS_RASPBERRY_PI and os.path.exists("/usr/bin/vcgencmd")
    
    # Logging
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE = LOG_DIR / "cat_tv.log"
    
    @classmethod
    def ensure_directories(cls):
        """Create necessary directories if they don't exist."""
        cls.DATA_DIR.mkdir(parents=True, exist_ok=True)
        cls.LOG_DIR.mkdir(parents=True, exist_ok=True)

config = Config()