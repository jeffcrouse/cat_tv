"""Video player management for Cat TV."""

import subprocess
import logging
import time
import os
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
            
            # Try primary method first
            if self._try_play_primary(url, title):
                return True
            
            # If primary fails on Raspberry Pi, try fallback methods
            if config.IS_RASPBERRY_PI:
                logger.warning("Primary video method failed, trying fallback...")
                if self._try_play_fallback(url, title):
                    return True
            
            logger.error("All video playback methods failed")
            self.current_video = None
            return False
            
        except Exception as e:
            logger.error(f"Failed to play video: {e}")
            self.current_video = None
            return False
    
    def _try_play_primary(self, url: str, title: str) -> bool:
        """Try primary video playback method."""
        try:
            if self.backend == "vlc":
                cmd = self._get_vlc_command(url)
            elif self.backend == "omxplayer":
                cmd = self._get_omxplayer_command(url)
            elif self.backend == "mpv":
                cmd = self._get_mpv_command(url)
            else:
                raise ValueError(f"Unknown player backend: {self.backend}")
            
            logger.debug(f"Primary method - Running command: {' '.join(cmd)}")
            
            # Set up environment for SSH and Raspberry Pi Connect compatibility
            env = os.environ.copy()
            if config.IS_RASPBERRY_PI:
                # Force output to physical display even from remote sessions
                env.pop('DISPLAY', None)  # Remove DISPLAY if set
                env.pop('WAYLAND_DISPLAY', None)  # Remove Wayland display if set
                env['HOME'] = os.path.expanduser('~')  # Ensure HOME is set
                env['VT_NUM'] = '7'  # Force specific virtual terminal
                # Ensure we have proper GPU access
                env['GPU_ENABLE_HIGH_PERFORMANCE'] = '1'
                
                # Log environment state
                logger.debug(f"Environment - DISPLAY removed: {'DISPLAY' not in env}")
                logger.debug(f"Environment - WAYLAND_DISPLAY removed: {'WAYLAND_DISPLAY' not in env}")
            
            self.current_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env
            )
            
            # Give process a moment to start
            time.sleep(2)
            if self.current_process.poll() is None:
                logger.info(f"Primary playback method started successfully")
                return True
            else:
                logger.warning("Primary playback process terminated immediately")
                return False
            
        except Exception as e:
            logger.error(f"Primary playback method failed: {e}")
            return False
    
    def _try_play_fallback(self, url: str, title: str) -> bool:
        """Try fallback video playback method for Raspberry Pi Connect."""
        try:
            # Force VLC with even more aggressive framebuffer targeting
            cmd = [
                "cvlc",
                "--fullscreen",
                "--vout", "fb",
                "--fbdev", "/dev/fb0",
                "--intf", "dummy",
                "--no-xlib",
                "--no-audio-display", 
                "--no-video-title-show",
                "--quiet",
                "--play-and-exit",  # Exit when done
                url
            ]
            
            logger.debug(f"Fallback method - Running command: {' '.join(cmd)}")
            
            # Even more aggressive environment cleanup
            env = {
                'PATH': os.environ.get('PATH', ''),
                'HOME': os.path.expanduser('~'),
                'USER': os.environ.get('USER', 'pi'),
                'TERM': 'linux',
                'FRAMEBUFFER': '/dev/fb0',
            }
            
            # Try to switch to console before playing
            try:
                subprocess.run(['sudo', 'chvt', '1'], check=False, timeout=5)
                time.sleep(1)
            except:
                pass  # Ignore if we can't switch VT
            
            self.current_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env
            )
            
            # Give process a moment to start
            time.sleep(3)
            if self.current_process.poll() is None:
                logger.info("Fallback playback method started successfully")
                return True
            else:
                logger.warning("Fallback playback process terminated immediately")
                return False
                
        except Exception as e:
            logger.error(f"Fallback playback method failed: {e}")
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
            "--intf", "dummy",  # No interface
            "--quiet",  # Reduce verbose output
        ]
        
        if config.IS_RASPBERRY_PI:
            # Force framebuffer output on Raspberry Pi - bypass virtual displays
            cmd.extend([
                "--vout", "fb",
                "--fbdev", "/dev/fb0",
                "--no-xlib",  # Don't try to use X11
                "--no-video-on-top",  # Prevent overlay issues
                "--video-on-top",  # But ensure video is visible
                "--no-embedded-video",  # Don't embed in interface
                "--no-qt-privacy-ask",  # Skip privacy dialog
                "--no-qt-system-tray",  # Don't use system tray
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