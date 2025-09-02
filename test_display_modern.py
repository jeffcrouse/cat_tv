#!/usr/bin/env python3
"""Modern Raspberry Pi display control test."""

import os
import subprocess
import time
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def check_pi_version():
    """Check Raspberry Pi version and OS."""
    logger.info("\n📊 System Information:")
    
    try:
        # Check Pi model
        if os.path.exists('/proc/device-tree/model'):
            with open('/proc/device-tree/model', 'r') as f:
                model = f.read().strip('\x00')
                logger.info(f"🍓 Pi Model: {model}")
        
        # Check OS version
        if os.path.exists('/etc/os-release'):
            with open('/etc/os-release', 'r') as f:
                os_info = f.read()
                for line in os_info.split('\n'):
                    if line.startswith('PRETTY_NAME'):
                        logger.info(f"💿 OS: {line.split('=')[1].strip('\"')}")
        
        # Check kernel version
        result = subprocess.run(['uname', '-a'], capture_output=True, text=True)
        if result.returncode == 0:
            logger.info(f"🔧 Kernel: {result.stdout.strip()}")
            
    except Exception as e:
        logger.warning(f"⚠️ Could not get system info: {e}")

def test_kms_drm_method():
    """Test KMS/DRM display control (modern method)."""
    logger.info("\n🧪 Testing KMS/DRM display control...")
    
    try:
        # Check for DRM devices
        drm_devices = []
        if os.path.exists('/sys/class/drm'):
            drm_devices = [d for d in os.listdir('/sys/class/drm') if d.startswith('card')]
            logger.info(f"🎮 Found DRM devices: {drm_devices}")
        
        # Try to control via DRM
        for device in drm_devices:
            dpms_path = f'/sys/class/drm/{device}/device/drm/{device}/dpms'
            enabled_path = f'/sys/class/drm/{device}/enabled'
            status_path = f'/sys/class/drm/{device}/status'
            
            logger.info(f"🔍 Checking {device}...")
            
            # Check if connector is connected
            if os.path.exists(status_path):
                with open(status_path, 'r') as f:
                    status = f.read().strip()
                    logger.info(f"📺 {device} status: {status}")
                    if status != 'connected':
                        continue
            
            # Try DPMS control
            if os.path.exists(dpms_path):
                try:
                    logger.info(f"🔴 Turning OFF via DRM DPMS {device}...")
                    with open(dpms_path, 'w') as f:
                        f.write('3')  # 3 = off, 0 = on
                    
                    logger.info("💡 Display should be OFF - waiting 5 seconds...")
                    time.sleep(5)
                    
                    logger.info(f"🟢 Turning ON via DRM DPMS {device}...")
                    with open(dpms_path, 'w') as f:
                        f.write('0')  # 0 = on
                    
                    return True
                    
                except PermissionError:
                    logger.warning(f"⚠️ Permission denied for {dpms_path} - try with sudo")
                except Exception as e:
                    logger.warning(f"⚠️ Error with {device}: {e}")
    
    except Exception as e:
        logger.error(f"❌ KMS/DRM method error: {e}")
    
    return False

def test_wlr_randr_method():
    """Test wlr-randr for Wayland display control."""
    logger.info("\n🧪 Testing wlr-randr (Wayland) method...")
    
    try:
        # Check if wlr-randr is available
        result = subprocess.run(['which', 'wlr-randr'], capture_output=True, text=True)
        if result.returncode != 0:
            logger.info("⚠️ wlr-randr not found")
            return False
        
        # Get display list
        result = subprocess.run(['wlr-randr'], capture_output=True, text=True)
        if result.returncode == 0:
            logger.info(f"📺 Available displays: {result.stdout.strip()[:200]}...")
            
            # Try to turn off first display (usually HDMI-A-1 or similar)
            displays = []
            for line in result.stdout.split('\n'):
                if line and not line.startswith(' ') and ':' in line:
                    display_name = line.split(':')[0].strip()
                    displays.append(display_name)
            
            if displays:
                display = displays[0]
                logger.info(f"🔴 Turning OFF display {display}...")
                result = subprocess.run(['wlr-randr', '--output', display, '--off'], 
                                      capture_output=True, text=True)
                if result.returncode == 0:
                    logger.info("💡 Display should be OFF - waiting 5 seconds...")
                    time.sleep(5)
                    
                    logger.info(f"🟢 Turning ON display {display}...")
                    subprocess.run(['wlr-randr', '--output', display, '--on'], 
                                  capture_output=True, text=True)
                    return True
        
    except Exception as e:
        logger.error(f"❌ wlr-randr method error: {e}")
    
    return False

def test_xrandr_method():
    """Test xrandr for X11 display control."""
    logger.info("\n🧪 Testing xrandr (X11) method...")
    
    try:
        # Check if xrandr is available and can connect to display
        result = subprocess.run(['xrandr', '--listmonitors'], 
                              capture_output=True, text=True, 
                              env={**os.environ, 'DISPLAY': ':0'})
        
        if result.returncode == 0:
            logger.info(f"📺 Connected monitors: {result.stdout.strip()}")
            
            # Get the first monitor name
            lines = result.stdout.strip().split('\n')
            if len(lines) > 1:  # Skip header line
                # Parse monitor name from output like "0: +HDMI-1 1920/510x1080/287+0+0  HDMI-1"
                monitor_line = lines[1]
                if '+' in monitor_line:
                    monitor_name = monitor_line.split('+')[1].split()[0]
                    
                    logger.info(f"🔴 Turning OFF monitor {monitor_name}...")
                    result = subprocess.run(['xrandr', '--output', monitor_name, '--off'], 
                                          capture_output=True, text=True,
                                          env={**os.environ, 'DISPLAY': ':0'})
                    
                    if result.returncode == 0:
                        logger.info("💡 Display should be OFF - waiting 5 seconds...")
                        time.sleep(5)
                        
                        logger.info(f"🟢 Turning ON monitor {monitor_name}...")
                        subprocess.run(['xrandr', '--output', monitor_name, '--auto'], 
                                      capture_output=True, text=True,
                                      env={**os.environ, 'DISPLAY': ':0'})
                        return True
        else:
            logger.info("⚠️ xrandr failed - not running X11 or no permission")
            
    except Exception as e:
        logger.error(f"❌ xrandr method error: {e}")
    
    return False

def test_sudo_framebuffer():
    """Test framebuffer control with sudo."""
    logger.info("\n🧪 Testing framebuffer with sudo...")
    
    try:
        fb_files = ['/sys/class/graphics/fb0/blank', '/sys/class/graphics/fb1/blank']
        
        for fb_file in fb_files:
            if os.path.exists(fb_file):
                logger.info(f"🔴 Testing sudo access to {fb_file}...")
                
                # Turn off
                result = subprocess.run(['sudo', 'sh', '-c', f'echo 1 > {fb_file}'], 
                                      capture_output=True, text=True, timeout=5)
                
                if result.returncode == 0:
                    logger.info("💡 Framebuffer should be blank - waiting 5 seconds...")
                    time.sleep(5)
                    
                    # Turn on
                    logger.info(f"🟢 Unblanking {fb_file}...")
                    subprocess.run(['sudo', 'sh', '-c', f'echo 0 > {fb_file}'], 
                                  capture_output=True, text=True, timeout=5)
                    return True
                else:
                    logger.warning(f"⚠️ sudo framebuffer control failed for {fb_file}")
    
    except Exception as e:
        logger.error(f"❌ Sudo framebuffer error: {e}")
    
    return False

def test_cec_control():
    """Test HDMI-CEC control."""
    logger.info("\n🧪 Testing HDMI-CEC control...")
    
    try:
        # Check if cec-utils is installed
        result = subprocess.run(['which', 'cec-client'], capture_output=True, text=True)
        if result.returncode != 0:
            logger.info("⚠️ cec-client not found - install with: sudo apt install cec-utils")
            return False
        
        logger.info("🔴 Sending CEC standby command...")
        # Send standby command to TV
        result = subprocess.run(['echo', 'standby 0'], stdout=subprocess.PIPE)
        result2 = subprocess.run(['cec-client', '-s', '-d', '1'], 
                               stdin=result.stdout, capture_output=True, text=True, timeout=10)
        
        if result2.returncode == 0:
            logger.info("💡 TV should be in standby - waiting 5 seconds...")
            time.sleep(5)
            
            logger.info("🟢 Sending CEC power on command...")
            result = subprocess.run(['echo', 'on 0'], stdout=subprocess.PIPE)
            subprocess.run(['cec-client', '-s', '-d', '1'], 
                          stdin=result.stdout, capture_output=True, text=True, timeout=10)
            return True
    
    except Exception as e:
        logger.error(f"❌ HDMI-CEC error: {e}")
    
    return False

def main():
    """Main test function."""
    print("🖥️  Modern Raspberry Pi Display Control Test")
    print("=" * 50)
    print("Testing modern methods for newer Raspberry Pi OS versions")
    print()
    
    # Get system info
    check_pi_version()
    
    working_methods = []
    
    # Test modern methods
    if test_kms_drm_method():
        working_methods.append("KMS/DRM")
    
    if test_wlr_randr_method():
        working_methods.append("wlr-randr")
    
    if test_xrandr_method():
        working_methods.append("xrandr")
    
    if test_sudo_framebuffer():
        working_methods.append("sudo framebuffer")
    
    if test_cec_control():
        working_methods.append("HDMI-CEC")
    
    # Summary
    print("\n" + "=" * 50)
    print("📋 MODERN TEST SUMMARY")
    print("=" * 50)
    
    if working_methods:
        logger.info(f"🎉 SUCCESS! Working methods: {', '.join(working_methods)}")
    else:
        logger.error("❌ No modern methods worked")
        logger.info("💡 Your display might not support any software power control")
        logger.info("💡 Consider using a smart plug or IR blaster for physical control")

if __name__ == "__main__":
    main()