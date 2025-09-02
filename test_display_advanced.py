#!/usr/bin/env python3
"""Advanced display control test with more methods."""

import os
import subprocess
import time
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def test_hdmi_output_control():
    """Test controlling HDMI output directly."""
    logger.info("\n🧪 Testing HDMI output control...")
    
    try:
        # Turn off HDMI output
        logger.info("🔴 Turning OFF HDMI output...")
        result = subprocess.run(['/opt/vc/bin/tvservice', '-o'], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            logger.info("💡 HDMI output should be OFF - waiting 5 seconds...")
            time.sleep(5)
            
            # Turn on HDMI output
            logger.info("🟢 Turning ON HDMI output...")
            # Note: -p preferred mode, or try -e "CEA 4 HDMI" for specific mode
            result = subprocess.run(['/opt/vc/bin/tvservice', '-p'], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                logger.info("💡 HDMI output should be ON")
                
                # Need to refresh framebuffer after turning HDMI back on
                logger.info("🔄 Refreshing framebuffer...")
                subprocess.run(['sudo', 'chvt', '6'], capture_output=True)
                subprocess.run(['sudo', 'chvt', '7'], capture_output=True)
                
                return True
        else:
            logger.error(f"❌ tvservice failed: {result.stderr}")
            
    except Exception as e:
        logger.error(f"❌ HDMI output control error: {e}")
    
    return False

def test_framebuffer_blanking():
    """Test blanking the framebuffer."""
    logger.info("\n🧪 Testing framebuffer blanking...")
    
    try:
        # Try different blanking approaches
        blank_methods = [
            ('/sys/class/graphics/fb0/blank', '1', '0'),
            ('/sys/class/graphics/fb1/blank', '1', '0'),
            ('/sys/class/tty/console/blank', '1', '0')
        ]
        
        for blank_file, off_value, on_value in blank_methods:
            if os.path.exists(blank_file):
                try:
                    logger.info(f"🔴 Trying to blank using {blank_file}...")
                    
                    # Turn off
                    with open(blank_file, 'w') as f:
                        f.write(off_value)
                    
                    logger.info("💡 Screen should be blank - waiting 5 seconds...")
                    time.sleep(5)
                    
                    # Turn on
                    logger.info("🟢 Unblanking screen...")
                    with open(blank_file, 'w') as f:
                        f.write(on_value)
                    
                    logger.info(f"✅ Framebuffer blanking via {blank_file} completed!")
                    return True
                    
                except PermissionError:
                    logger.warning(f"⚠️ Permission denied for {blank_file} - try with sudo")
                except Exception as e:
                    logger.warning(f"⚠️ Error with {blank_file}: {e}")
        
    except Exception as e:
        logger.error(f"❌ Framebuffer blanking error: {e}")
    
    return False

def test_console_blanking():
    """Test console blanking methods."""
    logger.info("\n🧪 Testing console blanking...")
    
    try:
        # Method 1: setterm
        logger.info("🔴 Using setterm to blank console...")
        result = subprocess.run(['setterm', '-blank', '1'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            # Force blank now
            subprocess.run(['setterm', '-powersave', 'on'], 
                          capture_output=True, text=True)
            logger.info("💡 Console should be blank - waiting 5 seconds...")
            time.sleep(5)
            
            # Turn back on
            logger.info("🟢 Turning console back on...")
            subprocess.run(['setterm', '-powersave', 'off'], 
                          capture_output=True, text=True)
            subprocess.run(['setterm', '-blank', '0'], 
                          capture_output=True, text=True)
            
            return True
    except Exception as e:
        logger.error(f"❌ Console blanking error: {e}")
    
    return False

def test_backlight_control():
    """Test backlight control."""
    logger.info("\n🧪 Testing backlight control...")
    
    backlight_paths = [
        '/sys/class/backlight/rpi_backlight/brightness',
        '/sys/class/backlight/10-0045/brightness',
        '/sys/class/backlight/backlight/brightness'
    ]
    
    for backlight_path in backlight_paths:
        if os.path.exists(backlight_path):
            try:
                # Read current brightness
                with open(backlight_path, 'r') as f:
                    original_brightness = f.read().strip()
                
                logger.info(f"🔴 Setting backlight to 0 via {backlight_path}...")
                with open(backlight_path, 'w') as f:
                    f.write('0')
                
                logger.info("💡 Backlight should be OFF - waiting 5 seconds...")
                time.sleep(5)
                
                logger.info("🟢 Restoring backlight...")
                with open(backlight_path, 'w') as f:
                    f.write(original_brightness)
                
                logger.info(f"✅ Backlight control via {backlight_path} completed!")
                return True
                
            except PermissionError:
                logger.warning(f"⚠️ Permission denied for {backlight_path} - try with sudo")
            except Exception as e:
                logger.warning(f"⚠️ Error with {backlight_path}: {e}")
    
    logger.info("⚠️ No backlight control files found")
    return False

def test_dpms_methods():
    """Test DPMS (Display Power Management System) methods."""
    logger.info("\n🧪 Testing DPMS methods...")
    
    # Method 1: Direct DPMS via framebuffer
    try:
        logger.info("🔴 Testing DPMS via framebuffer ioctl...")
        # This requires a more complex implementation with ioctl calls
        # For now, we'll test via other tools
        
        # Method 2: vbetool (if available)
        vbetool_result = subprocess.run(['which', 'vbetool'], 
                                       capture_output=True, text=True)
        if vbetool_result.returncode == 0:
            logger.info("🔴 Using vbetool to turn off display...")
            result = subprocess.run(['sudo', 'vbetool', 'dpms', 'off'], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                logger.info("💡 Display should be OFF via vbetool - waiting 5 seconds...")
                time.sleep(5)
                
                logger.info("🟢 Turning display back on...")
                subprocess.run(['sudo', 'vbetool', 'dpms', 'on'], 
                              capture_output=True, text=True, timeout=10)
                return True
        else:
            logger.info("⚠️ vbetool not found")
            
    except Exception as e:
        logger.error(f"❌ DPMS methods error: {e}")
    
    return False

def check_display_info():
    """Check display information and capabilities."""
    logger.info("\n📊 Display Information:")
    
    try:
        # Get display mode info
        result = subprocess.run(['/opt/vc/bin/tvservice', '-s'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            logger.info(f"📺 Display status: {result.stdout.strip()}")
        
        # Get supported modes
        result = subprocess.run(['/opt/vc/bin/tvservice', '-m', 'CEA'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            logger.info(f"📺 Supported CEA modes: {result.stdout.strip()[:100]}...")
        
        # Check HDMI status
        result = subprocess.run(['vcgencmd', 'display_power'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            logger.info(f"🔌 HDMI power status: {result.stdout.strip()}")
        
        # Check config.txt settings related to display
        config_file = '/boot/config.txt'
        if os.path.exists(config_file):
            with open(config_file, 'r') as f:
                config_content = f.read()
                hdmi_lines = [line.strip() for line in config_content.split('\n') 
                             if 'hdmi' in line.lower() and not line.startswith('#')]
                if hdmi_lines:
                    logger.info(f"⚙️ HDMI config settings: {hdmi_lines}")
        
    except Exception as e:
        logger.warning(f"⚠️ Could not get display info: {e}")

def main():
    """Main test function."""
    print("🖥️  Advanced Display Control Test")
    print("=" * 50)
    print("⚠️  This will test multiple methods to turn your display on/off!")
    print("Watch your screen carefully to see which methods actually work.")
    print()
    
    # Get display info first
    check_display_info()
    
    # Test methods in order of likelihood to work
    working_methods = []
    
    # Test HDMI output control (most likely to work)
    if test_hdmi_output_control():
        working_methods.append("HDMI output control")
    
    # Test framebuffer blanking
    if test_framebuffer_blanking():
        working_methods.append("Framebuffer blanking")
    
    # Test console blanking
    if test_console_blanking():
        working_methods.append("Console blanking")
    
    # Test backlight control
    if test_backlight_control():
        working_methods.append("Backlight control")
    
    # Test DPMS methods
    if test_dpms_methods():
        working_methods.append("DPMS methods")
    
    # Summary
    print("\n" + "=" * 50)
    print("📋 ADVANCED TEST SUMMARY")
    print("=" * 50)
    
    if working_methods:
        logger.info(f"🎉 SUCCESS! Working methods: {', '.join(working_methods)}")
        logger.info("💡 You can implement these methods in your Cat TV app")
    else:
        logger.error("❌ No methods successfully controlled the display")
        logger.info("💡 Your display may not support software power control")
        logger.info("💡 Try running with sudo: sudo python test_display_advanced.py")

if __name__ == "__main__":
    main()