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
                
                # Test basic playback capability with default audio
                logger.info("Testing VLC with default audio...")
                basic_test_cmd = ["cvlc", "--intf", "dummy", "--play-and-exit", "--quiet", "--aout", "pulse", "/dev/null"]
                basic_result = subprocess.run(basic_test_cmd, capture_output=True, text=True, timeout=5)
                
                if basic_result.returncode == 0:
                    logger.info("✅ VLC basic playback test with default audio passed")
                else:
                    logger.warning(f"❌ VLC basic playback test failed with code: {basic_result.returncode}")
                    if basic_result.stderr:
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
            
            # Set PulseAudio sink via environment variable and configure volume
            env = os.environ.copy()
            sink_name = None
            
            # Get list of available sinks first
            try:
                result = subprocess.run(["pactl", "list", "sinks", "short"], 
                                      capture_output=True, text=True, timeout=5)
                available_sinks = result.stdout if result.returncode == 0 else ""
            except Exception:
                available_sinks = ""
            
            if config.AUDIO_OUTPUT == "hdmi":
                # Dynamically find HDMI sink
                for line in available_sinks.split('\n'):
                    if 'hdmi' in line.lower():
                        parts = line.split()
                        if len(parts) >= 2:
                            sink_name = parts[1]
                            env["PULSE_SINK"] = sink_name
                            logger.info(f"Setting PULSE_SINK to HDMI audio: {sink_name}")
                            break
            elif config.AUDIO_OUTPUT == "local":
                # Dynamically find local/analog sink
                for line in available_sinks.split('\n'):
                    if 'fallback' in line.lower() or 'analog' in line.lower():
                        parts = line.split()
                        if len(parts) >= 2:
                            sink_name = parts[1]
                            env["PULSE_SINK"] = sink_name
                            logger.info(f"Setting PULSE_SINK to local audio: {sink_name}")
                            break
            elif config.AUDIO_OUTPUT == "all":
                # Try combined sink first
                if "cat_tv_combined" in available_sinks:
                    sink_name = "cat_tv_combined"
                    env["PULSE_SINK"] = sink_name
                    logger.info("Setting PULSE_SINK to combined audio")
                else:
                    # Fallback to HDMI
                    for line in available_sinks.split('\n'):
                        if 'hdmi' in line.lower():
                            parts = line.split()
                            if len(parts) >= 2:
                                sink_name = parts[1]
                                env["PULSE_SINK"] = sink_name
                                logger.info(f"Combined sink not found, using HDMI: {sink_name}")
                                break
            
            # Set volume using PulseAudio from config
            if sink_name:
                volume_percent = min(max(config.VOLUME, 0), 500)  # Cap between 0-500% for safety
                try:
                    subprocess.run(["pactl", "set-sink-volume", sink_name, f"{volume_percent}%"], 
                                 timeout=3, check=False)
                    logger.info(f"Set audio volume to {volume_percent}% on {sink_name} (from config)")
                except Exception as e:
                    logger.warning(f"Failed to set volume: {e}")
            
            
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
                universal_newlines=True,
                env=env
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
                logger.error(f"❌ VLC process exited immediately with code: {self.current_process.returncode}")
                logger.error(f"Command was: {' '.join(cmd)}")
                try:
                    # Use communicate to get any remaining output
                    stdout_output, stderr_output = self.current_process.communicate(timeout=1)
                    if stderr_output and stderr_output.strip():
                        logger.error(f"VLC stderr: {stderr_output.strip()}")
                        # Log each line separately for better visibility
                        for line in stderr_output.strip().split('\n'):
                            if line.strip():
                                logger.error(f"  stderr: {line.strip()}")
                    if stdout_output and stdout_output.strip():
                        logger.error(f"VLC stdout: {stdout_output.strip()}")
                        for line in stdout_output.strip().split('\n'):
                            if line.strip():
                                logger.error(f"  stdout: {line.strip()}")
                    if not stderr_output and not stdout_output:
                        logger.error("❌ No output from VLC process - this suggests VLC failed before it could output anything")
                        logger.error("This usually means:")
                        logger.error("  - VLC binary not found")
                        logger.error("  - Permissions issue")
                        logger.error("  - Invalid command line arguments")
                        logger.error("  - Audio/video system not accessible")
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
    
    def set_volume(self, volume: int) -> bool:
        """Set volume for the current audio sink."""
        try:
            # First, get list of available sinks
            result = subprocess.run(["pactl", "list", "sinks", "short"], 
                                  capture_output=True, text=True, timeout=5)
            available_sinks = result.stdout if result.returncode == 0 else ""
            
            # Determine current sink
            sink_name = None
            if config.AUDIO_OUTPUT == "hdmi":
                # Always dynamically find HDMI sink instead of hardcoding
                for line in available_sinks.split('\n'):
                    if 'hdmi' in line.lower():
                        parts = line.split()
                        if len(parts) >= 2:
                            sink_name = parts[1]
                            logger.debug(f"Found HDMI sink: {sink_name}")
                            break
            elif config.AUDIO_OUTPUT == "local":
                sink_name = "alsa_output.platform-fe00b840.mailbox.stereo-fallback"
                # Check if sink exists
                if sink_name not in available_sinks:
                    for line in available_sinks.split('\n'):
                        if 'fallback' in line.lower() or 'analog' in line.lower():
                            sink_name = line.split()[1] if line else None
                            break
            elif config.AUDIO_OUTPUT == "all":
                if "cat_tv_combined" in available_sinks:
                    sink_name = "cat_tv_combined"
                else:
                    # Try to find any available sink
                    lines = available_sinks.split('\n')
                    if lines and lines[0]:
                        sink_name = lines[0].split()[1]
            
            # If no sink found, try to get the default sink
            if not sink_name and available_sinks:
                lines = available_sinks.split('\n')
                for line in lines:
                    if line and not line.startswith('#'):
                        parts = line.split()
                        if len(parts) >= 2:
                            sink_name = parts[1]
                            break
            
            if sink_name:
                volume_percent = min(max(volume, 0), 500)  # Clamp between 0-500%
                subprocess.run(["pactl", "set-sink-volume", sink_name, f"{volume_percent}%"], 
                             timeout=3, check=True)
                logger.info(f"Set volume to {volume_percent}% on {sink_name}")
                return True
            else:
                logger.error("No audio sink available for volume control")
                return False
        except Exception as e:
            logger.error(f"Failed to set volume: {e}")
            return False
    
    def get_volume(self) -> int:
        """Get current volume of the audio sink."""
        try:
            # First, get list of available sinks
            result = subprocess.run(["pactl", "list", "sinks", "short"], 
                                  capture_output=True, text=True, timeout=5)
            available_sinks = result.stdout if result.returncode == 0 else ""
            
            # Determine current sink
            sink_name = None
            if config.AUDIO_OUTPUT == "hdmi":
                # Always dynamically find HDMI sink instead of hardcoding
                for line in available_sinks.split('\n'):
                    if 'hdmi' in line.lower():
                        parts = line.split()
                        if len(parts) >= 2:
                            sink_name = parts[1]
                            logger.debug(f"Found HDMI sink: {sink_name}")
                            break
            elif config.AUDIO_OUTPUT == "local":
                sink_name = "alsa_output.platform-fe00b840.mailbox.stereo-fallback"
                # Check if sink exists
                if sink_name not in available_sinks:
                    for line in available_sinks.split('\n'):
                        if 'fallback' in line.lower() or 'analog' in line.lower():
                            sink_name = line.split()[1] if line else None
                            break
            elif config.AUDIO_OUTPUT == "all":
                if "cat_tv_combined" in available_sinks:
                    sink_name = "cat_tv_combined"
                else:
                    # Try to find any available sink
                    lines = available_sinks.split('\n')
                    if lines and lines[0]:
                        sink_name = lines[0].split()[1]
            
            # If no sink found, try to get the default sink
            if not sink_name and available_sinks:
                lines = available_sinks.split('\n')
                for line in lines:
                    if line and not line.startswith('#'):
                        parts = line.split()
                        if len(parts) >= 2:
                            sink_name = parts[1]
                            break
            
            if sink_name:
                result = subprocess.run(["pactl", "get-sink-volume", sink_name], 
                                      capture_output=True, text=True, timeout=3)
                if result.returncode == 0:
                    # Parse volume from output like "Volume: front-left: 98304 /  150% / -3.52 dB"
                    for line in result.stdout.split('\n'):
                        if 'Volume:' in line and '%' in line:
                            # Extract percentage
                            parts = line.split('/')
                            for part in parts:
                                if '%' in part:
                                    volume_str = part.strip().replace('%', '')
                                    try:
                                        return int(volume_str)
                                    except ValueError:
                                        logger.warning(f"Could not parse volume value: {volume_str}")
                    
                    # Log the actual output if parsing failed (limit to first 200 chars)
                    if result.stdout:
                        logger.warning(f"Could not parse volume from pactl output: {result.stdout[:200]}")
                    else:
                        logger.warning("pactl returned empty output")
                    return config.VOLUME  # Return config default
                else:
                    # Log error if pactl command failed
                    logger.warning(f"pactl get-sink-volume failed for sink {sink_name}: {result.stderr}")
                    return config.VOLUME
            else:
                return config.VOLUME
        except Exception as e:
            logger.error(f"Failed to get volume: {e}")
            return config.VOLUME
    
    def _get_vlc_command(self, url: str) -> list:
        """Get VLC command for CLI playback."""
        # Go back to using cvlc directly since wrapper has privilege issues
        cmd = ["cvlc"]  # Console VLC (no GUI)
        
        # Add minimal options for service environment  
        cmd.extend([
            "--intf", "dummy",  # No interface
            "--no-video-title-show",
            "--quiet",  # Reduce verbose output
            "--fullscreen",  # Full screen display
        ])
        
        # Let VLC auto-detect the best video output for the system
        # Remove specific video output to let VLC choose
        
        # Use PulseAudio output (sink is set via PULSE_SINK environment variable)
        cmd.extend(["--aout", "pulse"])
            
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