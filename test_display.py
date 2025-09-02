#!/usr/bin/env python3
"""Test display control functionality."""

import sys
import os
import subprocess
import time

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from cat_tv.display import DisplayController
from cat_tv.config import config

def test_display_permissions():
    """Test display control permissions and methods."""
    print("🖥️  Testing Display Control Permissions")
    print("=" * 50)
    
    # Check if we're on Raspberry Pi
    print(f"Is Raspberry Pi: {config.IS_RASPBERRY_PI}")
    print(f"Use vcgencmd: {config.USE_VCGENCMD}")
    
    # Test vcgencmd availability and permissions
    if config.USE_VCGENCMD:
        try:
            result = subprocess.run(['vcgencmd', 'display_power'], 
                                  capture_output=True, text=True, timeout=5)
            print(f"✅ vcgencmd available")
            print(f"   Current display power: {result.stdout.strip()}")
            print(f"   Return code: {result.returncode}")
            if result.stderr:
                print(f"   Stderr: {result.stderr.strip()}")
        except FileNotFoundError:
            print("❌ vcgencmd not found")
        except subprocess.TimeoutExpired:
            print("❌ vcgencmd timed out")
        except Exception as e:
            print(f"❌ vcgencmd error: {e}")
    
    # Test framebuffer permissions
    fb_path = "/sys/class/graphics/fb0/blank"
    if os.path.exists(fb_path):
        print(f"✅ Framebuffer found: {fb_path}")
        try:
            with open(fb_path, 'r') as f:
                current_state = f.read().strip()
            print(f"   Current blank state: {current_state} (0=on, 1=off)")
            
            # Test write permissions
            try:
                with open(fb_path, 'w') as f:
                    f.write(current_state)  # Write back same value
                print(f"   ✅ Write permission OK")
            except PermissionError:
                print(f"   ❌ No write permission - try: sudo usermod -a -G video $USER")
        except Exception as e:
            print(f"   ❌ Framebuffer access error: {e}")
    else:
        print(f"❌ Framebuffer not found: {fb_path}")
    
    # Test user groups
    try:
        import grp
        groups = [grp.getgrgid(gid).gr_name for gid in os.getgroups()]
        print(f"User groups: {', '.join(groups)}")
        if 'video' in groups:
            print("✅ User is in video group")
        else:
            print("❌ User NOT in video group - run: sudo usermod -a -G video $USER && newgrp video")
    except Exception as e:
        print(f"Could not check groups: {e}")

def test_display_control():
    """Test the DisplayController class."""
    print("\n🎛️  Testing DisplayController Class")
    print("=" * 50)
    
    controller = DisplayController()
    
    # Test getting status
    print("Getting display status...")
    status = controller.get_status()
    print(f"Status: {status}")
    
    # Test turn off
    print("\n🔴 Testing display OFF...")
    result = controller.turn_off()
    print(f"Turn off result: {result}")
    
    if result:
        print("⏳ Waiting 3 seconds to see effect...")
        time.sleep(3)
        print("💡 Your display should be OFF now")
        
        # Test turn on
        print("\n🟢 Testing display ON...")
        result = controller.turn_on()
        print(f"Turn on result: {result}")
        
        if result:
            print("💡 Your display should be ON now")
        else:
            print("❌ Failed to turn display on")
    else:
        print("❌ Failed to turn display off")

def test_manual_commands():
    """Test manual display commands."""
    print("\n⚙️  Testing Manual Commands")
    print("=" * 50)
    
    commands_to_test = [
        {
            'name': 'vcgencmd display_power 0 (OFF)',
            'cmd': ['vcgencmd', 'display_power', '0'],
            'description': 'Turn display off with vcgencmd'
        },
        {
            'name': 'Sleep 2 seconds',
            'cmd': None,
            'description': 'Wait to see effect'
        },
        {
            'name': 'vcgencmd display_power 1 (ON)',
            'cmd': ['vcgencmd', 'display_power', '1'], 
            'description': 'Turn display on with vcgencmd'
        }
    ]
    
    for test in commands_to_test:
        print(f"\n🧪 {test['name']}")
        print(f"   {test['description']}")
        
        if test['cmd'] is None:
            time.sleep(2)
            continue
            
        try:
            result = subprocess.run(test['cmd'], capture_output=True, text=True, timeout=10)
            print(f"   Return code: {result.returncode}")
            if result.stdout:
                print(f"   Stdout: {result.stdout.strip()}")
            if result.stderr:
                print(f"   Stderr: {result.stderr.strip()}")
                
            if result.returncode == 0:
                print(f"   ✅ Command successful")
            else:
                print(f"   ❌ Command failed")
                
        except FileNotFoundError:
            print(f"   ❌ Command not found")
        except subprocess.TimeoutExpired:
            print(f"   ❌ Command timed out")
        except Exception as e:
            print(f"   ❌ Error: {e}")

def main():
    print("🖥️  Display Control Test Suite")
    print("=" * 50)
    
    print("⚠️  WARNING: This test will turn your display on/off!")
    print("Make sure you're running this on the actual Raspberry Pi.")
    
    response = input("Continue? (y/n): ").lower().strip()
    if response != 'y':
        print("Test cancelled.")
        return
    
    # Run tests
    test_display_permissions()
    test_display_control()
    test_manual_commands()
    
    print("\n" + "=" * 50)
    print("🏁 Test completed!")
    print("If display control didn't work, check the error messages above.")

if __name__ == "__main__":
    main()