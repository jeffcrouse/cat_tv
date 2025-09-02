"""Display control for Raspberry Pi using framebuffer method."""

import os
import subprocess
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class DisplayController:
    """Controls display power using framebuffer blanking."""
    
    def __init__(self):
        self.fb_files = [
            '/sys/class/graphics/fb0/blank',
            '/sys/class/graphics/fb1/blank'
        ]
        self.working_fb_file = None
        self._find_working_framebuffer()
    
    def _find_working_framebuffer(self):
        """Find which framebuffer file we can use."""
        for fb_file in self.fb_files:
            if os.path.exists(fb_file):
                try:
                    # Test if we can write to it
                    if os.access(fb_file, os.W_OK):
                        self.working_fb_file = fb_file
                        logger.info(f"✅ Found writable framebuffer: {fb_file}")
                        return
                    else:
                        logger.debug(f"⚠️ Framebuffer exists but not writable: {fb_file}")
                except Exception as e:
                    logger.debug(f"⚠️ Error checking {fb_file}: {e}")
        
        logger.warning("⚠️ No writable framebuffer files found - display control may require sudo")
    
    def turn_off(self):
        """Turn off the display."""
        try:
            logger.info("🔴 Turning display OFF...")
            
            if self.working_fb_file:
                # Direct write if we have permissions
                with open(self.working_fb_file, 'w') as f:
                    f.write('1')  # 1 = blank
                logger.info("✅ Display turned off via framebuffer")
                return True
            else:
                # Use sudo if no direct permissions
                for fb_file in self.fb_files:
                    if os.path.exists(fb_file):
                        result = subprocess.run(
                            ['sudo', 'sh', '-c', f'echo 1 > {fb_file}'], 
                            capture_output=True, text=True, timeout=5
                        )
                        if result.returncode == 0:
                            logger.info(f"✅ Display turned off via sudo: {fb_file}")
                            return True
                        else:
                            logger.debug(f"⚠️ Sudo failed for {fb_file}: {result.stderr}")
            
            logger.error("❌ Failed to turn off display")
            return False
            
        except Exception as e:
            logger.error(f"❌ Failed to turn off display: {e}")
            return False
    
    def turn_on(self):
        """Turn on the display."""
        try:
            logger.info("🟢 Turning display ON...")
            
            if self.working_fb_file:
                # Direct write if we have permissions
                with open(self.working_fb_file, 'w') as f:
                    f.write('0')  # 0 = unblank
                logger.info("✅ Display turned on via framebuffer")
                return True
            else:
                # Use sudo if no direct permissions
                for fb_file in self.fb_files:
                    if os.path.exists(fb_file):
                        result = subprocess.run(
                            ['sudo', 'sh', '-c', f'echo 0 > {fb_file}'], 
                            capture_output=True, text=True, timeout=5
                        )
                        if result.returncode == 0:
                            logger.info(f"✅ Display turned on via sudo: {fb_file}")
                            return True
                        else:
                            logger.debug(f"⚠️ Sudo failed for {fb_file}: {result.stderr}")
            
            logger.error("❌ Failed to turn on display")
            return False
            
        except Exception as e:
            logger.error(f"❌ Failed to turn on display: {e}")
            return False
    
    def get_status(self):
        """Get display status information."""
        try:
            status = {
                'available': False,
                'method': 'framebuffer',
                'working_file': self.working_fb_file,
                'requires_sudo': self.working_fb_file is None
            }
            
            # Check if any framebuffer files exist
            for fb_file in self.fb_files:
                if os.path.exists(fb_file):
                    status['available'] = True
                    break
            
            # Try to read current blank status
            if self.working_fb_file:
                try:
                    with open(self.working_fb_file, 'r') as f:
                        blank_status = f.read().strip()
                        status['is_blank'] = blank_status == '1'
                except Exception as e:
                    logger.debug(f"Could not read blank status: {e}")
            
            return status
            
        except Exception as e:
            logger.error(f"Failed to get display status: {e}")
            return {'available': False, 'error': str(e)}
    
    def setup_permissions(self):
        """Setup permissions for display control without sudo."""
        logger.info("🔧 Setting up display control permissions...")
        
        try:
            # Check current user and groups
            import pwd
            import grp
            
            current_user = pwd.getpwuid(os.getuid()).pw_name
            logger.info(f"👤 Current user: {current_user}")
            
            # Try to create a udev rule for framebuffer access
            udev_rule = '''# Allow members of video group to control framebuffer
SUBSYSTEM=="graphics", KERNEL=="fb[0-9]*", GROUP="video", MODE="0664"
SUBSYSTEM=="graphics", KERNEL=="fb[0-9]*", ACTION=="add", RUN+="/bin/chmod g+w /sys/class/graphics/%k/blank"
'''
            
            rule_path = "/etc/udev/rules.d/99-framebuffer-permissions.rules"
            
            logger.info("📋 To setup automatic permissions, run these commands as root:")
            logger.info(f"sudo tee {rule_path} << 'EOF'")
            logger.info(udev_rule.strip())
            logger.info("EOF")
            logger.info("sudo udevadm control --reload-rules")
            logger.info("sudo udevadm trigger")
            logger.info(f"sudo usermod -a -G video {current_user}")
            logger.info("# Then reboot or re-login")
            
            return False  # Manual setup required
            
        except Exception as e:
            logger.error(f"Error setting up permissions: {e}")
            return False