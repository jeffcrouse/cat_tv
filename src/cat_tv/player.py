"""Video player management for Cat TV."""

import subprocess
import logging
import time
from typing import Optional, Dict, Any
from pathlib import Path

from .config import config

logger = logging.getLogger(__name__)

class VideoPlayer:
    """Manages video playback using various backends."""
    
    def __init__(self, backend: str = None):
        self.backend = backend or config.PLAYER_BACKEND
        self.current_process: Optional[subprocess.Popen] = None
        self.current_video: Optional[Dict[str, Any]] = None
        
    def play(self, url: str, title: str = "Video") -> bool:
        """Play a video URL."""
        try:
            self.stop()  # Stop any currently playing video
            
            logger.info(f"Playing: {title}")
            self.current_video = {"url": url, "title": title}
            
            if self.backend == "vlc":
                cmd = self._get_vlc_command(url)
            elif self.backend == "omxplayer":
                cmd = self._get_omxplayer_command(url)
            elif self.backend == "mpv":
                cmd = self._get_mpv_command(url)
            else:
                raise ValueError(f"Unknown player backend: {self.backend}")
            
            logger.debug(f"Running command: {' '.join(cmd)}")
            self.current_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to play video: {e}")
            self.current_video = None
            return False
    
    def stop(self) -> bool:
        """Stop the currently playing video."""
        if self.current_process:
            try:
                self.current_process.terminate()
                time.sleep(0.5)
                if self.current_process.poll() is None:
                    self.current_process.kill()
                self.current_process = None
                self.current_video = None
                logger.info("Stopped video playback")
                return True
            except Exception as e:
                logger.error(f"Failed to stop video: {e}")
                return False
        return True
    
    def is_playing(self) -> bool:
        """Check if a video is currently playing."""
        if self.current_process:
            return self.current_process.poll() is None
        return False
    
    def _get_vlc_command(self, url: str) -> list:
        """Get VLC command for CLI playback."""
        cmd = [
            "cvlc",  # Console VLC (no GUI)
            "--fullscreen",
            "--no-video-title-show",
            "--no-mouse-events",
            "--no-keyboard-events",
        ]
        
        if config.IS_RASPBERRY_PI:
            # Use framebuffer output on Raspberry Pi
            cmd.extend([
                "--vout", "fb",
                "--fbdev", "/dev/fb0"
            ])
        
        # Audio output configuration
        if config.AUDIO_OUTPUT == "hdmi":
            cmd.extend(["--alsa-audio-device", "hdmi"])
        elif config.AUDIO_OUTPUT == "local":
            cmd.extend(["--alsa-audio-device", "default"])
            
        cmd.append(url)
        return cmd
    
    def _get_omxplayer_command(self, url: str) -> list:
        """Get OMXPlayer command (Raspberry Pi specific)."""
        cmd = ["omxplayer", "--blank"]
        
        if config.AUDIO_OUTPUT == "hdmi":
            cmd.extend(["-o", "hdmi"])
        elif config.AUDIO_OUTPUT == "local":
            cmd.extend(["-o", "local"])
        elif config.AUDIO_OUTPUT == "both":
            cmd.extend(["-o", "both"])
            
        cmd.append(url)
        return cmd
    
    def _get_mpv_command(self, url: str) -> list:
        """Get MPV command for CLI playback."""
        cmd = [
            "mpv",
            "--fullscreen",
            "--no-input-default-bindings",
            "--no-osc",
            "--no-input-cursor",
        ]
        
        if config.IS_RASPBERRY_PI:
            # Use DRM/KMS for direct framebuffer access
            cmd.extend([
                "--vo=gpu",
                "--gpu-context=drm",
                "--drm-connector=HDMI-A-1"
            ])
        
        if config.AUDIO_OUTPUT == "hdmi":
            cmd.extend(["--audio-device", "alsa/hdmi"])
        elif config.AUDIO_OUTPUT == "local":
            cmd.extend(["--audio-device", "alsa/default"])
            
        cmd.append(url)
        return cmd