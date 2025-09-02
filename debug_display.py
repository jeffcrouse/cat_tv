#!/usr/bin/env python3
"""Simple display control debug script for Raspberry Pi."""

import subprocess
import os
import time

def test_vcgencmd():
    """Test vcgencmd display control."""
    print("🔧 Testing vcgencmd display control")
    print("=" * 40)
    
    try:
        # Check current status
        print("1. Checking current display status...")
        result = subprocess.run(['vcgencmd', 'display_power'], 
                              capture_output=True, text=True)
        print(f"   Current status: {result.stdout.strip()}")
        print(f"   Return code: {result.returncode}")
        if result.stderr:
            print(f"   Error: {result.stderr.strip()}")
        
        if result.returncode != 0:
            print("❌ vcgencmd not working")
            return False
        
        # Test turning off
        print("\n2. Turning display OFF...")
        result = subprocess.run(['vcgencmd', 'display_power', '0'], 
                              capture_output=True, text=True)
        print(f"   Result: {result.stdout.strip()}")
        print(f"   Return code: {result.returncode}")
        if result.stderr:
            print(f"   Error: {result.stderr.strip()}")
        
        print("   ⏳ Waiting 3 seconds...")
        time.sleep(3)
        
        # Test turning on
        print("\n3. Turning display ON...")
        result = subprocess.run(['vcgencmd', 'display_power', '1'], 
                              capture_output=True, text=True)
        print(f"   Result: {result.stdout.strip()}")
        print(f"   Return code: {result.returncode}")
        if result.stderr:
            print(f"   Error: {result.stderr.strip()}")
        
        return result.returncode == 0
        
    except FileNotFoundError:
        print("❌ vcgencmd command not found")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_framebuffer():
    """Test framebuffer display control."""
    print("\n🔧 Testing framebuffer display control")
    print("=" * 40)
    
    fb_blank_path = "/sys/class/graphics/fb0/blank"
    
    try:
        # Check if framebuffer exists
        if not os.path.exists(fb_blank_path):
            print(f"❌ Framebuffer control not found: {fb_blank_path}")
            return False
        
        print(f"✅ Framebuffer control found: {fb_blank_path}")
        
        # Check current status
        print("1. Checking current blank status...")
        with open(fb_blank_path, 'r') as f:
            current_status = f.read().strip()
        print(f"   Current status: {current_status} (0=on, 1=off)")
        
        # Test permissions
        print("\n2. Testing write permissions...")
        try:
            with open(fb_blank_path, 'w') as f:
                f.write(current_status)  # Write back same value
            print("   ✅ Write permissions OK")
        except PermissionError:
            print("   ❌ No write permission")
            print("   Try: sudo usermod -a -G video $USER")
            return False
        
        # Test turning off
        print("\n3. Testing display OFF (blank=1)...")
        with open(fb_blank_path, 'w') as f:
            f.write('1')
        print("   ⏳ Waiting 3 seconds...")
        time.sleep(3)
        
        # Test turning on
        print("\n4. Testing display ON (blank=0)...")
        with open(fb_blank_path, 'w') as f:
            f.write('0')
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_cat_tv_display():
    """Test the actual Cat TV DisplayController."""
    print("\n🔧 Testing Cat TV DisplayController")
    print("=" * 40)
    
    try:
        import sys
        import os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
        
        from cat_tv.display import DisplayController
        from cat_tv.config import config
        
        print(f"Config - IS_RASPBERRY_PI: {config.IS_RASPBERRY_PI}")
        print(f"Config - USE_VCGENCMD: {config.USE_VCGENCMD}")
        
        controller = DisplayController()
        
        # Test get status
        print("\n1. Getting display status...")
        status = controller.get_status()
        print(f"   Status: {status}")
        
        # Test turn off
        print("\n2. Testing turn OFF...")
        success = controller.turn_off()
        print(f"   Success: {success}")
        if success:
            print("   ⏳ Waiting 3 seconds...")
            time.sleep(3)
        
        # Test turn on
        print("\n3. Testing turn ON...")
        success = controller.turn_on()
        print(f"   Success: {success}")
        
        return True
        
    except ImportError as e:
        print(f"❌ Could not import Cat TV modules: {e}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def main():
    print("🖥️  Raspberry Pi Display Control Debug")
    print("=" * 50)
    print("This will test display on/off functionality")
    print("Make sure you're running this on the Raspberry Pi!")
    print()
    
    # Test different methods
    vcgencmd_works = test_vcgencmd()
    framebuffer_works = test_framebuffer()
    cat_tv_works = test_cat_tv_display()
    
    print("\n" + "=" * 50)
    print("📋 FINAL RESULTS - PLEASE REPORT THESE 3 LINES:")
    print("=" * 50)
    result_code = ""
    result_code += "V" if vcgencmd_works else "v"
    result_code += "F" if framebuffer_works else "f" 
    result_code += "C" if cat_tv_works else "c"
    
    print(f"RESULT CODE: {result_code}")
    print(f"vcgencmd: {'WORKS' if vcgencmd_works else 'FAILED'}")
    print(f"framebuffer: {'WORKS' if framebuffer_works else 'FAILED'}")
    print(f"cat_tv: {'WORKS' if cat_tv_works else 'FAILED'}")
    print("=" * 50)
    
    if result_code == "VFC":
        print("🎉 ALL WORKING! Display control should work fine.")
    elif "V" in result_code or "F" in result_code:
        print("✅ At least one method works. Will fix Cat TV to use working method.")
    else:
        print("❌ NOTHING WORKS. Need to troubleshoot permissions/setup.")

if __name__ == "__main__":
    main()