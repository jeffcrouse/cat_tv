#!/usr/bin/env python3
"""Debug script to test VLC functionality on Raspberry Pi."""

import subprocess
import os
import pwd
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def check_environment():
    """Check current environment."""
    logger.info("=== Environment Check ===")
    logger.info(f"Real UID: {os.getuid()}, Effective UID: {os.geteuid()}")
    logger.info(f"Real GID: {os.getgid()}, Effective GID: {os.getegid()}")
    try:
        logger.info(f"Username: {pwd.getpwuid(os.getuid()).pw_name}")
    except:
        logger.info("Could not get username")
    logger.info(f"USER: {os.getenv('USER', 'not-set')}")
    logger.info(f"HOME: {os.getenv('HOME', 'not-set')}")
    logger.info(f"DISPLAY: {os.getenv('DISPLAY', 'not-set')}")
    logger.info(f"XDG_RUNTIME_DIR: {os.getenv('XDG_RUNTIME_DIR', 'not-set')}")
    
def test_vlc_basic():
    """Test basic VLC functionality."""
    logger.info("\n=== Basic VLC Test ===")
    try:
        cmd = ["cvlc", "--version"]
        logger.info(f"Running: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        logger.info(f"Exit code: {result.returncode}")
        if result.stdout:
            logger.info(f"STDOUT: {result.stdout[:200]}...")
        if result.stderr:
            logger.info(f"STDERR: {result.stderr[:200]}...")
    except Exception as e:
        logger.error(f"VLC basic test failed: {e}")

def test_audio_sinks():
    """Test available audio sinks."""
    logger.info("\n=== Audio Sinks ===")
    try:
        cmd = ["pactl", "list", "sinks", "short"]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        logger.info(f"Exit code: {result.returncode}")
        if result.stdout:
            logger.info("Available sinks:")
            for line in result.stdout.strip().split('\n'):
                logger.info(f"  {line}")
        if result.stderr:
            logger.info(f"STDERR: {result.stderr}")
    except Exception as e:
        logger.error(f"Audio sink test failed: {e}")

def test_vlc_with_simple_url():
    """Test VLC with a simple, reliable test URL."""
    logger.info("\n=== VLC Simple URL Test ===")
    test_url = "https://sample-videos.com/zip/10/mp4/SampleVideo_1280x720_1mb.mp4"
    
    # Test with default audio
    cmd = ["cvlc", "--intf", "dummy", "--play-and-exit", "--run-time=3", test_url]
    logger.info(f"Running: {' '.join(cmd[:-1])} [test-url]")
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        logger.info(f"Exit code: {result.returncode}")
        if result.stdout:
            logger.info(f"STDOUT: {result.stdout}")
        if result.stderr:
            logger.info(f"STDERR: {result.stderr}")
    except Exception as e:
        logger.error(f"VLC simple URL test failed: {e}")

def test_vlc_with_audio_sink():
    """Test VLC with specific audio sink."""
    logger.info("\n=== VLC Audio Sink Test ===")
    test_url = "https://sample-videos.com/zip/10/mp4/SampleVideo_1280x720_1mb.mp4"
    
    # Test with HDMI sink
    cmd = ["cvlc", "--intf", "dummy", "--play-and-exit", "--run-time=3", 
           "--aout", "pulse", "--pulse-sink", "alsa_output.platform-fef00700.hdmi.hdmi-stereo", 
           test_url]
    logger.info(f"Running with HDMI sink: {' '.join(cmd[:-1])} [test-url]")
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        logger.info(f"Exit code: {result.returncode}")
        if result.stdout:
            logger.info(f"STDOUT: {result.stdout}")
        if result.stderr:
            logger.info(f"STDERR: {result.stderr}")
    except Exception as e:
        logger.error(f"VLC audio sink test failed: {e}")

if __name__ == "__main__":
    check_environment()
    test_vlc_basic()
    test_audio_sinks()
    test_vlc_with_simple_url()
    test_vlc_with_audio_sink()