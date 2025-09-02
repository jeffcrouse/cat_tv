#!/usr/bin/env python3
"""Test display control with permission checking."""

import os
import subprocess
import time
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def check_permissions():
    """Check if we have the necessary permissions for display control."""
    logger.info("🔍 Checking permissions...")
    
    # Check if we're running as root
    if os.geteuid() == 0:
        logger.info("✅ Running as root - should have all permissions")
        return True
    
    # Check if user is in video group
    try:
        result = subprocess.run(['groups'], capture_output=True, text=True, check=True)
        groups = result.stdout.strip().split()
        if 'video' in groups:
            logger.info("✅ User is in 'video' group")
        else:
            logger.warning("⚠️ User is NOT in 'video' group")
            logger.info("💡 Try: sudo usermod -a -G video $USER")
    except Exception as e:
        logger.warning(f"⚠️ Could not check groups: {e}")
    
    # Check if vcgencmd exists and is executable
    vcgencmd_path = subprocess.run(['which', 'vcgencmd'], capture_output=True, text=True)
    if vcgencmd_path.returncode == 0:
        logger.info(f"✅ vcgencmd found at: {vcgencmd_path.stdout.strip()}")
        
        # Test if we can run vcgencmd
        try:
            result = subprocess.run(['vcgencmd', 'display_power'], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                logger.info(f"✅ vcgencmd works - current status: {result.stdout.strip()}")
                return True
            else:
                logger.error(f"❌ vcgencmd failed: {result.stderr.strip()}")
        except subprocess.TimeoutExpired:
            logger.error("❌ vcgencmd timed out")
        except Exception as e:
            logger.error(f"❌ vcgencmd error: {e}")
    else:
        logger.warning("⚠️ vcgencmd not found - not on Raspberry Pi?")
    
    # Check framebuffer access
    fb_devices = ['/dev/fb0', '/dev/fb1']
    for fb in fb_devices:
        if Path(fb).exists():
            try:
                # Try to read the framebuffer device
                with open(fb, 'rb') as f:
                    f.read(1)
                logger.info(f"✅ Can read {fb}")
                
                # Check if we can write to it
                if os.access(fb, os.W_OK):
                    logger.info(f"✅ Can write to {fb}")
                else:
                    logger.warning(f"⚠️ Cannot write to {fb}")
            except PermissionError:
                logger.error(f"❌ Permission denied accessing {fb}")
            except Exception as e:
                logger.warning(f"⚠️ Error checking {fb}: {e}")
    
    return False

def test_vcgencmd_method():
    """Test display control using vcgencmd."""
    logger.info("\n🧪 Testing vcgencmd method...")
    
    try:
        # Get current status
        result = subprocess.run(['vcgencmd', 'display_power'], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode != 0:
            logger.error(f"❌ Could not get display status: {result.stderr}")
            return False
        
        original_status = result.stdout.strip()
        logger.info(f"📊 Current display status: {original_status}")
        
        # Turn display OFF
        logger.info("🔴 Turning display OFF...")
        result = subprocess.run(['vcgencmd', 'display_power', '0'], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode != 0:
            logger.error(f"❌ Failed to turn display off: {result.stderr}")
            return False
        
        logger.info("💡 Display should be OFF now - waiting 5 seconds...")
        time.sleep(5)
        
        # Turn display ON
        logger.info("🟢 Turning display ON...")
        result = subprocess.run(['vcgencmd', 'display_power', '1'], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode != 0:
            logger.error(f"❌ Failed to turn display on: {result.stderr}")
            return False
        
        logger.info("💡 Display should be ON now")
        
        # Verify it's back on
        time.sleep(1)
        result = subprocess.run(['vcgencmd', 'display_power'], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            final_status = result.stdout.strip()
            logger.info(f"📊 Final display status: {final_status}")
        
        return True
        
    except subprocess.TimeoutExpired:
        logger.error("❌ vcgencmd command timed out")
        return False
    except Exception as e:
        logger.error(f"❌ Error in vcgencmd test: {e}")
        return False

def test_framebuffer_method():
    """Test display control using framebuffer."""
    logger.info("\n🧪 Testing framebuffer method...")
    
    try:
        # Turn display OFF (blank)
        logger.info("🔴 Turning display OFF via framebuffer...")
        with open('/sys/class/graphics/fbcon/cursor_blink', 'w') as f:
            f.write('0')
        
        # Try different framebuffer blank methods
        fb_paths = ['/sys/class/graphics/fb0/blank', '/dev/fb0']
        
        for fb_path in fb_paths:
            if Path(fb_path).exists():
                try:
                    if 'blank' in fb_path:
                        logger.info(f"💡 Trying to blank {fb_path}...")
                        with open(fb_path, 'w') as f:
                            f.write('1')  # 1 = blank
                    else:
                        logger.info(f"💡 Trying to clear {fb_path}...")
                        # Clear framebuffer with zeros
                        with open(fb_path, 'wb') as f:
                            f.write(b'\x00' * 1024)
                    
                    logger.info("💡 Display should be OFF now - waiting 5 seconds...")
                    time.sleep(5)
                    
                    # Turn back ON
                    logger.info("🟢 Turning display ON...")
                    if 'blank' in fb_path:
                        with open(fb_path, 'w') as f:
                            f.write('0')  # 0 = unblank
                    
                    logger.info("💡 Display should be ON now")
                    return True
                    
                except PermissionError:
                    logger.warning(f"⚠️ Permission denied writing to {fb_path}")
                except Exception as e:
                    logger.warning(f"⚠️ Error with {fb_path}: {e}")
        
        return False
        
    except Exception as e:
        logger.error(f"❌ Error in framebuffer test: {e}")
        return False

def test_other_methods():
    """Test other display control methods."""
    logger.info("\n🧪 Testing other methods...")
    
    methods = [
        {
            'name': 'tvservice',
            'off_cmd': ['tvservice', '-o'],
            'on_cmd': ['tvservice', '-p'],
            'description': 'HDMI service control'
        },
        {
            'name': 'xset',
            'off_cmd': ['xset', 'dpms', 'force', 'off'],
            'on_cmd': ['xset', 'dpms', 'force', 'on'],
            'description': 'X11 display power management'
        }
    ]
    
    for method in methods:
        logger.info(f"\n🔧 Testing {method['name']} ({method['description']})...")
        
        # Check if command exists
        which_result = subprocess.run(['which', method['name']], 
                                    capture_output=True, text=True)
        if which_result.returncode != 0:
            logger.warning(f"⚠️ {method['name']} not found")
            continue
        
        try:
            # Turn OFF
            logger.info(f"🔴 Turning display OFF with {method['name']}...")
            result = subprocess.run(method['off_cmd'], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode != 0:
                logger.warning(f"⚠️ {method['name']} off failed: {result.stderr}")
                continue
            
            logger.info("💡 Display should be OFF - waiting 5 seconds...")
            time.sleep(5)
            
            # Turn ON
            logger.info(f"🟢 Turning display ON with {method['name']}...")
            result = subprocess.run(method['on_cmd'], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode != 0:
                logger.warning(f"⚠️ {method['name']} on failed: {result.stderr}")
            else:
                logger.info(f"✅ {method['name']} method worked!")
                return True
                
        except subprocess.TimeoutExpired:
            logger.warning(f"⚠️ {method['name']} timed out")
        except Exception as e:
            logger.warning(f"⚠️ {method['name']} error: {e}")
    
    return False

def main():
    """Main test function."""
    print("🖥️  Display Control Test")
    print("=" * 50)
    print("⚠️  WARNING: This will turn your display on/off!")
    print("Make sure you can see the screen to observe the results.")
    print()
    
    input("Press Enter to start the test, or Ctrl+C to cancel...")
    
    # Check permissions first
    has_permissions = check_permissions()
    if not has_permissions:
        logger.warning("\n⚠️ Permission issues detected. Display control might not work.")
        logger.info("💡 Try running with sudo or add user to video group")
    
    # Test different methods
    methods_tested = []
    
    # Test vcgencmd (Raspberry Pi specific)
    if test_vcgencmd_method():
        methods_tested.append("vcgencmd")
        logger.info("✅ vcgencmd method SUCCESS!")
    
    # Test framebuffer method
    if test_framebuffer_method():
        methods_tested.append("framebuffer")
        logger.info("✅ framebuffer method SUCCESS!")
    
    # Test other methods
    if test_other_methods():
        methods_tested.append("other")
        logger.info("✅ other methods SUCCESS!")
    
    # Summary
    print("\n" + "=" * 50)
    print("📋 TEST SUMMARY")
    print("=" * 50)
    
    if methods_tested:
        logger.info(f"🎉 SUCCESS! Working methods: {', '.join(methods_tested)}")
        logger.info("💡 You can now implement display control in your Cat TV app")
    else:
        logger.error("❌ NO methods worked for display control")
        logger.info("💡 Possible solutions:")
        logger.info("   1. Run with sudo")
        logger.info("   2. Add user to video group: sudo usermod -a -G video $USER")
        logger.info("   3. Check if running on actual Raspberry Pi")
        logger.info("   4. Your display might not support software control")

if __name__ == "__main__":
    main()