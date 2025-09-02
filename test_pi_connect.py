#!/usr/bin/env python3
"""Test video playback specifically for Raspberry Pi Connect issues."""

import sys
import os
import subprocess
import time

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from cat_tv.display import DisplayController
from cat_tv.config import config

def check_pi_connect_environment():
    """Check for Raspberry Pi Connect specific environment variables."""
    print("🔍 Checking Raspberry Pi Connect Environment")
    print("=" * 50)
    
    # Check for remote session indicators
    remote_indicators = [
        'SSH_CLIENT', 'SSH_CONNECTION', 'SSH_TTY',
        'DISPLAY', 'WAYLAND_DISPLAY', 'XDG_SESSION_TYPE',
        'DESKTOP_SESSION', 'GNOME_DESKTOP_SESSION_ID'
    ]
    
    for var in remote_indicators:
        value = os.environ.get(var)
        if value:
            print(f"🔴 {var}: {value}")
        else:
            print(f"⚪ {var}: Not set")
    
    # Check current virtual terminal
    try:
        with open('/sys/class/tty/tty0/active', 'r') as f:
            active_vt = f.read().strip()
        print(f"🖥️  Active VT: {active_vt}")
    except:
        print("❌ Could not read active VT")
    
    # Check if we're in a framebuffer console
    try:
        result = subprocess.run(['tty'], capture_output=True, text=True)
        print(f"🖥️  Current TTY: {result.stdout.strip()}")
    except:
        print("❌ Could not get current TTY")
    
    print()

def test_framebuffer_access():
    """Test direct framebuffer access."""
    print("📺 Testing Framebuffer Access")
    print("=" * 50)
    
    fb_path = "/dev/fb0"
    if os.path.exists(fb_path):
        print(f"✅ Framebuffer exists: {fb_path}")
        
        try:
            # Check permissions
            stat = os.stat(fb_path)
            print(f"   Permissions: {oct(stat.st_mode)[-3:]}")
            
            # Try to read framebuffer info
            result = subprocess.run(['fbset'], capture_output=True, text=True)
            if result.returncode == 0:
                print("✅ fbset works:")
                for line in result.stdout.split('\n')[:10]:  # First 10 lines
                    if line.strip():
                        print(f"   {line}")
            else:
                print(f"❌ fbset failed: {result.stderr}")
                
        except Exception as e:
            print(f"❌ Error checking framebuffer: {e}")
    else:
        print(f"❌ Framebuffer not found: {fb_path}")
    
    print()

def test_vlc_methods():
    """Test different VLC invocation methods."""
    print("🎬 Testing VLC Methods")
    print("=" * 50)
    
    # Create a simple test pattern video URL (Big Buck Bunny sample)
    test_url = "https://sample-videos.com/zip/10/mp4/SampleVideo_1280x720_1mb.mp4"
    
    methods = [
        {
            'name': 'Standard FB Method',
            'cmd': ['cvlc', '--fullscreen', '--vout', 'fb', '--fbdev', '/dev/fb0', 
                   '--intf', 'dummy', '--no-xlib', '--quiet', '--play-and-exit', test_url],
            'env_changes': {'remove': ['DISPLAY', 'WAYLAND_DISPLAY']}
        },
        {
            'name': 'Console Switch Method', 
            'cmd': ['cvlc', '--fullscreen', '--vout', 'fb', '--fbdev', '/dev/fb0',
                   '--intf', 'dummy', '--no-xlib', '--quiet', '--play-and-exit', test_url],
            'env_changes': {'remove': ['DISPLAY', 'WAYLAND_DISPLAY'], 'console_switch': True}
        },
        {
            'name': 'Minimal Environment Method',
            'cmd': ['cvlc', '--fullscreen', '--vout', 'fb', '--fbdev', '/dev/fb0',
                   '--intf', 'dummy', '--no-xlib', '--quiet', '--play-and-exit', test_url],
            'env_changes': {'minimal_env': True}
        }
    ]
    
    for i, method in enumerate(methods, 1):
        print(f"\n🧪 Testing Method {i}: {method['name']}")
        print("-" * 30)
        
        # Setup environment
        env = os.environ.copy()
        env_changes = method.get('env_changes', {})
        
        if 'remove' in env_changes:
            for var in env_changes['remove']:
                env.pop(var, None)
                print(f"   Removed {var} from environment")
        
        if env_changes.get('minimal_env'):
            env = {
                'PATH': os.environ.get('PATH', ''),
                'HOME': os.path.expanduser('~'),
                'USER': os.environ.get('USER', 'pi'),
                'TERM': 'linux',
                'FRAMEBUFFER': '/dev/fb0',
            }
            print("   Using minimal environment")
        
        # Switch console if requested
        if env_changes.get('console_switch'):
            print("   Switching to console...")
            try:
                subprocess.run(['sudo', 'chvt', '1'], check=False, timeout=5)
                time.sleep(1)
            except:
                print("   Console switch failed or not available")
        
        # Run the command
        print(f"   Command: {' '.join(method['cmd'][:3])} ... [url]")
        print("   ⏳ Starting video (will run for 10 seconds)...")
        
        try:
            process = subprocess.Popen(
                method['cmd'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env
            )
            
            # Wait and check
            time.sleep(3)  # Give it time to start
            
            if process.poll() is None:
                print("   ✅ Process started successfully!")
                print("   🎵 Check if you can see video on the physical display")
                
                # Let it run for a bit
                time.sleep(7)
                
                # Stop it
                process.terminate()
                process.wait(timeout=5)
                print("   🛑 Stopped")
            else:
                stdout, stderr = process.communicate()
                print(f"   ❌ Process failed immediately")
                if stderr:
                    print(f"   Error: {stderr.decode()[:200]}...")
                    
        except Exception as e:
            print(f"   ❌ Exception: {e}")
        
        print("   " + "-" * 20)
        
        # Ask user for feedback
        if i < len(methods):
            response = input("\n   Did you see video on the display? (y/n/s to skip remaining): ").lower().strip()
            if response == 'y':
                print(f"   🎉 SUCCESS! Method {i} works!")
                return method
            elif response == 's':
                print("   Skipping remaining tests")
                break
    
    print("\n❌ No methods worked for displaying video")
    return None

def main():
    print("🔧 Raspberry Pi Connect Video Debug Tool")
    print("=" * 50)
    
    if not config.IS_RASPBERRY_PI:
        print("⚠️  This tool is designed for Raspberry Pi")
        print("Running anyway for testing...")
    
    print("This tool will help diagnose video display issues when")
    print("running Cat TV through Raspberry Pi Connect.")
    print()
    
    response = input("Continue with tests? (y/n): ").lower().strip()
    if response != 'y':
        print("Tests cancelled.")
        return
    
    # Run diagnostic tests
    check_pi_connect_environment()
    test_framebuffer_access()
    
    # Test display control
    print("🖥️  Testing Display Control")
    print("=" * 30)
    display = DisplayController()
    status = display.get_status()
    print(f"Display status: {status}")
    print()
    
    # Test video methods
    working_method = test_vlc_methods()
    
    if working_method:
        print(f"\n🎉 SOLUTION FOUND!")
        print(f"Working method: {working_method['name']}")
        print("The Cat TV app will be updated to use this method.")
    else:
        print(f"\n❌ No working methods found")
        print("You may need to:")
        print("1. Ensure VLC is installed: sudo apt install vlc")
        print("2. Add user to video group: sudo usermod -a -G video $USER")
        print("3. Try running directly on Pi console (not through Pi Connect)")
        print("4. Check if hardware acceleration is enabled")

if __name__ == "__main__":
    main()