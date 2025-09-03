"""Video player management for Cat TV."""

import subprocess
import logging
import time
import os
import threading
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
        self.stderr_thread: Optional[threading.Thread] = None
        self.stdout_thread: Optional[threading.Thread] = None
        
    def test_vlc(self) -> bool:
        """Test if VLC is working with a simple test."""
        try:
            # Log environment for debugging service vs interactive differences
            import os
            import pwd
            logger.info("Testing VLC installation...")
            logger.info(f"Real UID: {os.getuid()}, Effective UID: {os.geteuid()}")
            logger.info(f"Real GID: {os.getgid()}, Effective GID: {os.getegid()}")
            try:
                logger.info(f"Username: {pwd.getpwuid(os.getuid()).pw_name}")
            except:
                logger.info("Could not get username")
            logger.info(f"USER: {os.getenv('USER', 'not-set')}")
            logger.info(f"HOME: {os.getenv('HOME', 'not-set')}")
            logger.info(f"XDG_RUNTIME_DIR: {os.getenv('XDG_RUNTIME_DIR', 'not-set')}")
            logger.info(f"PATH: {os.getenv('PATH', 'not-set')[:100]}...")
            
            # Try to run VLC with just version flag
            test_cmd = ["cvlc", "--version"]
            result = subprocess.run(test_cmd, capture_output=True, text=True, timeout=5)
            
            if result.returncode == 0:
                logger.info("VLC is installed and accessible")
                
                # Test basic playback capability
                logger.info("Testing VLC basic playback command...")
                basic_test_cmd = ["cvlc", "--intf", "dummy", "--play-and-exit", "--quiet", "/dev/null"]
                basic_result = subprocess.run(basic_test_cmd, capture_output=True, text=True, timeout=3)
                
                if basic_result.returncode == 0:
                    logger.info("VLC basic playback test passed")
                else:
                    logger.warning(f"VLC basic playback test failed with code: {basic_result.returncode}")
                    logger.warning(f"stderr: {basic_result.stderr}")
                
                return True
            else:
                logger.error(f"VLC test failed with code {result.returncode}")
                logger.error(f"stderr: {result.stderr}")
                return False
        except FileNotFoundError:
            logger.error("VLC (cvlc) not found in PATH")
            return False
        except Exception as e:
            logger.error(f"VLC test error: {e}")
            return False
    
    def _test_vlc_with_url(self, test_url: str) -> bool:
        """Test VLC with a specific URL."""
        try:
            cmd = ["cvlc", "--intf", "dummy", "--play-and-exit", "--run-time=2", test_url]
            logger.info(f"Testing VLC with command: {' '.join(cmd[:-1])} [test-url]")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                logger.info("VLC test URL playback successful")
                return True
            else:
                logger.error(f"VLC test URL failed with code: {result.returncode}")
                if result.stderr:
                    logger.error(f"VLC test stderr: {result.stderr}")
                if result.stdout:
                    logger.error(f"VLC test stdout: {result.stdout}")
                return False
        except Exception as e:
            logger.error(f"VLC URL test error: {e}")
            return False
        
    def play(self, url: str, title: str = "Video") -> bool:
        """Play a video URL."""
        try:
            self.stop()  # Stop any currently playing video
            
            logger.info(f"Playing: {title}")
            self.current_video = {"url": url, "title": title}
            
            # Test with a simple URL first to debug VLC
            if "googlevideo.com" in url or "youtube" in url.lower():
                logger.info("Testing VLC with a simple test URL first...")
                test_result = self._test_vlc_with_url("https://sample-videos.com/zip/10/mp4/SampleVideo_1280x720_1mb.mp4")
                if not test_result:
                    logger.warning("VLC failed with test URL - may be a VLC configuration issue")
            
            if self.backend == "vlc":
                cmd = self._get_vlc_command(url)
            elif self.backend == "omxplayer":
                cmd = self._get_omxplayer_command(url)
            elif self.backend == "mpv":
                cmd = self._get_mpv_command(url)
            else:
                raise ValueError(f"Unknown player backend: {self.backend}")
            
            # Log the full command for debugging
            logger.info(f"Running VLC command: {' '.join(cmd)}")
            logger.info(f"URL length: {len(url)} characters")
            
            self.current_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                bufsize=1,
                universal_newlines=True
            )
            
            # Start threads to monitor output
            self.stderr_thread = threading.Thread(
                target=self._monitor_stderr,
                args=(self.current_process,),
                daemon=True
            )
            self.stdout_thread = threading.Thread(
                target=self._monitor_stdout,
                args=(self.current_process,),
                daemon=True
            )
            self.stderr_thread.start()
            self.stdout_thread.start()
            
            # Wait a moment to check for immediate failures
            time.sleep(0.5)
            if self.current_process.poll() is not None:
                # Process exited immediately - try to capture any error output
                try:
                    # Use communicate to get any remaining output
                    stdout_output, stderr_output = self.current_process.communicate(timeout=1)
                    logger.error(f"Player process exited immediately with code: {self.current_process.returncode}")
                    if stderr_output and stderr_output.strip():
                        logger.error(f"VLC stderr: {stderr_output.strip()}")
                    if stdout_output and stdout_output.strip():
                        logger.error(f"VLC stdout: {stdout_output.strip()}")
                    if not stderr_output and not stdout_output:
                        logger.error("No output from VLC process")
                except subprocess.TimeoutExpired:
                    logger.error("Timeout waiting for VLC output")
                except Exception as e:
                    logger.error(f"Error capturing VLC output: {e}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to play video: {e}", exc_info=True)
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
        # Go back to using cvlc directly since wrapper has privilege issues
        cmd = ["cvlc"]  # Console VLC (no GUI)
        
        # Add options for service environment
        cmd.extend([
            "--intf", "dummy",  # No interface
            "--fullscreen",
        ])
        
        # For service mode, try framebuffer output instead of KMS
        if config.IS_RASPBERRY_PI:
            # Check if we're running in a service (no DISPLAY variable)
            import os
            if not os.getenv('DISPLAY'):
                # Service mode - use framebuffer
                cmd.extend([
                    "--vout", "fb",
                    "--fbdev", "/dev/fb0",
                ])
            else:
                # Interactive mode - use default video output
                pass
        
        # Add audio configuration  
        if config.AUDIO_OUTPUT == "hdmi":
            cmd.extend(["--aout", "alsa", "--alsa-audio-device", "hdmi"])
        elif config.AUDIO_OUTPUT == "local": 
            cmd.extend(["--aout", "alsa"])
            
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
    
    def _monitor_stderr(self, process: subprocess.Popen):
        """Monitor stderr output from the player process."""
        try:
            for line in process.stderr:
                if line.strip():
                    # Log VLC errors for debugging
                    if "error" in line.lower() or "failed" in line.lower():
                        logger.error(f"VLC Error: {line.strip()}")
                    elif "warning" in line.lower():
                        logger.warning(f"VLC Warning: {line.strip()}")
                    else:
                        logger.debug(f"VLC stderr: {line.strip()}")
        except Exception as e:
            logger.debug(f"Error monitoring stderr: {e}")
    
    def _monitor_stdout(self, process: subprocess.Popen):
        """Monitor stdout output from the player process."""
        try:
            for line in process.stdout:
                if line.strip():
                    logger.debug(f"VLC stdout: {line.strip()}")
        except Exception as e:
            logger.debug(f"Error monitoring stdout: {e}")