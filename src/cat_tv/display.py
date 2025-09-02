"""Display control for Raspberry Pi."""

import os
import subprocess
import logging
from typing import Optional

from .config import config

logger = logging.getLogger(__name__)

class DisplayController:
    """Controls display power and settings."""
    
    def __init__(self):
        self.is_on = True
        
    def turn_on(self) -> bool:
        """Turn on the display."""
        try:
            logger.info("Attempting to turn on display...")
            
            # Try multiple methods for better compatibility
            success = False
            
            if config.USE_VCGENCMD:
                # Method 1: vcgencmd display_power
                logger.info("Trying vcgencmd display_power")
                result = subprocess.run(["vcgencmd", "display_power", "1"], 
                                      capture_output=True, text=True)
                logger.info(f"vcgencmd result: {result.stdout.strip()}")
                if result.returncode == 0:
                    success = True
                
                # Method 2: HDMI on via tvservice (for HDMI displays)
                logger.info("Trying tvservice to turn on HDMI")
                result = subprocess.run(["tvservice", "-p"], 
                                      capture_output=True, text=True)
                logger.info(f"tvservice result: {result.returncode}")
                if result.returncode == 0:
                    success = True
                    # After turning HDMI back on, may need to refresh framebuffer
                    try:
                        subprocess.run(["fbset", "-depth", "8"], check=False)
                        subprocess.run(["fbset", "-depth", "16"], check=False)
                    except:
                        pass
            
            # Method 3: Framebuffer unblank
            try:
                logger.info("Trying framebuffer unblank")
                with open("/sys/class/graphics/fb0/blank", "w") as f:
                    f.write("0")
                logger.info("Framebuffer unblank successful")
                success = True
            except (FileNotFoundError, PermissionError) as e:
                logger.info(f"Framebuffer unblank failed: {e}")
            
            # Method 4: DPMS via /sys (for some displays)
            try:
                logger.info("Trying DPMS power management")
                dpms_path = "/sys/class/drm/card0-HDMI-A-1/dpms"
                if os.path.exists(dpms_path):
                    with open(dpms_path, "w") as f:
                        f.write("0")  # 0 = on
                    logger.info("DPMS on successful")
                    success = True
                else:
                    logger.info("DPMS path not found, skipping")
            except (FileNotFoundError, PermissionError) as e:
                logger.info(f"DPMS control failed: {e}")
            except Exception as e:
                logger.warning(f"DPMS unexpected error: {e}")
            
            self.is_on = True
            if success:
                logger.info("✅ Display turned on (one or more methods succeeded)")
            else:
                logger.warning("⚠️ All methods attempted but may not have worked")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to turn on display: {e}")
            return False
    
    def turn_off(self) -> bool:
        """Turn off the display."""
        try:
            logger.info("Attempting to turn off display...")
            
            # Try multiple methods for better compatibility
            success = False
            
            if config.USE_VCGENCMD:
                # Method 1: vcgencmd display_power
                logger.info("Trying vcgencmd display_power")
                result = subprocess.run(["vcgencmd", "display_power", "0"], 
                                      capture_output=True, text=True)
                logger.info(f"vcgencmd result: {result.stdout.strip()}")
                if result.returncode == 0:
                    success = True
                
                # Method 2: HDMI off via tvservice (for HDMI displays)
                logger.info("Trying tvservice to turn off HDMI")
                result = subprocess.run(["tvservice", "-o"], 
                                      capture_output=True, text=True)
                logger.info(f"tvservice result: {result.returncode}")
                if result.returncode == 0:
                    success = True
                
            # Method 3: Framebuffer blank
            try:
                logger.info("Trying framebuffer blank")
                with open("/sys/class/graphics/fb0/blank", "w") as f:
                    f.write("1")
                logger.info("Framebuffer blank successful")
                success = True
            except (FileNotFoundError, PermissionError) as e:
                logger.info(f"Framebuffer blank failed: {e}")
            
            # Method 4: DPMS via /sys (for some displays)
            try:
                logger.info("Trying DPMS power management")
                dpms_path = "/sys/class/drm/card0-HDMI-A-1/dpms"
                if os.path.exists(dpms_path):
                    with open(dpms_path, "w") as f:
                        f.write("3")  # 3 = off
                    logger.info("DPMS off successful")
                    success = True
                else:
                    logger.info("DPMS path not found, skipping")
            except (FileNotFoundError, PermissionError) as e:
                logger.info(f"DPMS control failed: {e}")
            except Exception as e:
                logger.warning(f"DPMS unexpected error: {e}")
            
            self.is_on = False
            if success:
                logger.info("✅ Display turned off (one or more methods succeeded)")
            else:
                logger.warning("⚠️ All methods attempted but may not have worked")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to turn off display: {e}")
            return False
    
    def get_status(self) -> dict:
        """Get display status information."""
        status = {"is_on": self.is_on}
        
        if config.USE_VCGENCMD:
            try:
                # Get display power status
                result = subprocess.run(
                    ["vcgencmd", "display_power"],
                    capture_output=True,
                    text=True
                )
                status["power_state"] = result.stdout.strip()
                
                # Get display resolution
                result = subprocess.run(
                    ["vcgencmd", "get_config", "hdmi_mode"],
                    capture_output=True,
                    text=True
                )
                status["hdmi_mode"] = result.stdout.strip()
                
            except Exception as e:
                logger.error(f"Failed to get display status: {e}")
        
        return status
    
    def set_brightness(self, level: int) -> bool:
        """Set display brightness (0-100)."""
        # This is display-dependent and may not work on all setups
        try:
            if 0 <= level <= 100:
                # Try to use backlight control if available
                backlight_path = "/sys/class/backlight/rpi_backlight/brightness"
                max_brightness = 255
                brightness_value = int((level / 100) * max_brightness)
                
                try:
                    with open(backlight_path, "w") as f:
                        f.write(str(brightness_value))
                    logger.info(f"Set brightness to {level}%")
                    return True
                except FileNotFoundError:
                    logger.warning("Backlight control not available")
                    return False
            else:
                logger.error("Brightness level must be between 0 and 100")
                return False
                
        except Exception as e:
            logger.error(f"Failed to set brightness: {e}")
            return False