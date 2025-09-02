"""Display control for Raspberry Pi."""

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
            if config.USE_VCGENCMD:
                # Raspberry Pi specific using vcgencmd
                subprocess.run(["vcgencmd", "display_power", "1"], check=True)
            else:
                # Try generic Linux framebuffer unblank
                try:
                    with open("/sys/class/graphics/fb0/blank", "w") as f:
                        f.write("0")
                except FileNotFoundError:
                    # Try xset if available (fallback for development)
                    subprocess.run(["xset", "dpms", "force", "on"], check=False)
            
            self.is_on = True
            logger.info("Display turned on")
            return True
            
        except Exception as e:
            logger.error(f"Failed to turn on display: {e}")
            return False
    
    def turn_off(self) -> bool:
        """Turn off the display."""
        try:
            if config.USE_VCGENCMD:
                # Raspberry Pi specific using vcgencmd
                subprocess.run(["vcgencmd", "display_power", "0"], check=True)
            else:
                # Try generic Linux framebuffer blank
                try:
                    with open("/sys/class/graphics/fb0/blank", "w") as f:
                        f.write("1")
                except FileNotFoundError:
                    # Try xset if available (fallback for development)
                    subprocess.run(["xset", "dpms", "force", "off"], check=False)
            
            self.is_on = False
            logger.info("Display turned off")
            return True
            
        except Exception as e:
            logger.error(f"Failed to turn off display: {e}")
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