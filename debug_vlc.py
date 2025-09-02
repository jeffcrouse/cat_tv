#!/usr/bin/env python3
"""Debug VLC playback issues on Raspberry Pi."""

import sys
import os
import subprocess
import time

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from cat_tv.youtube import YouTubeManager

def test_vlc_commands():
    """Test different VLC commands to see which works."""
    print("🔍 Testing VLC Commands")
    print("=" * 50)
    
    # Get a working stream URL
    youtube = YouTubeManager()
    videos = youtube.search_videos("cat tv", max_results=1)
    
    if not videos:
        print("❌ No videos found for testing")
        return
    
    video = videos[0]
    print(f"📺 Testing with: {video['title']}")
    
    stream_url = youtube.get_stream_url(video['url'])
    if not stream_url:
        print("❌ Could not get stream URL")
        return
    
    print(f"✅ Got stream URL: {stream_url[:100]}...")
    
    # Test different VLC configurations
    test_configs = [
        {
            'name': 'Standard VLC (our current config)',
            'cmd': [
                'cvlc',
                '--fullscreen',
                '--no-video-title-show',
                '--no-mouse-events', 
                '--no-keyboard-events',
                '--vout', 'fb',
                '--fbdev', '/dev/fb0',
                stream_url
            ]
        },
        {
            'name': 'VLC without framebuffer',
            'cmd': [
                'cvlc',
                '--fullscreen',
                '--no-video-title-show',
                stream_url
            ]
        },
        {
            'name': 'VLC with X11 output',
            'cmd': [
                'cvlc',
                '--fullscreen',
                '--vout', 'x11',
                stream_url
            ]
        },
        {
            'name': 'OMXPlayer (Raspberry Pi native)',
            'cmd': [
                'omxplayer',
                '--blank',
                '-o', 'hdmi',
                stream_url
            ]
        }
    ]
    
    for config in test_configs:
        print(f"\n🧪 Testing: {config['name']}")
        print(f"Command: {' '.join(config['cmd'][:3])} ... [URL]")
        
        try:
            # Check if command exists
            cmd_name = config['cmd'][0]
            result = subprocess.run(['which', cmd_name], capture_output=True)
            if result.returncode != 0:
                print(f"❌ {cmd_name} not found")
                continue
                
            print(f"✅ {cmd_name} found, starting playback...")
            
            # Start the player
            proc = subprocess.Popen(
                config['cmd'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            print("⏰ Letting it run for 5 seconds...")
            time.sleep(5)
            
            # Check if still running
            poll = proc.poll()
            if poll is None:
                print("✅ Process still running - SUCCESS!")
                print("🎬 You should see/hear video now!")
                
                # Kill it
                proc.terminate()
                time.sleep(1)
                if proc.poll() is None:
                    proc.kill()
                print("⏹ Stopped playback")
                
                return config  # Return successful config
                
            else:
                print(f"❌ Process exited with code: {poll}")
                stdout, stderr = proc.communicate()
                if stderr:
                    print(f"Error: {stderr.decode()[:200]}...")
                    
        except Exception as e:
            print(f"❌ Exception: {e}")
    
    print("\n❌ All VLC configurations failed!")
    return None

def test_display_info():
    """Check display and system info."""
    print("\n🖥️  Display Information")
    print("=" * 50)
    
    # Check framebuffer
    if os.path.exists('/dev/fb0'):
        print("✅ /dev/fb0 exists")
        try:
            stat = os.stat('/dev/fb0')
            print(f"📊 Framebuffer permissions: {oct(stat.st_mode)[-3:]}")
        except Exception as e:
            print(f"❌ Could not stat /dev/fb0: {e}")
    else:
        print("❌ /dev/fb0 does not exist")
    
    # Check if user is in video group
    try:
        import grp
        video_group = grp.getgrnam('video')
        user_groups = os.getgroups()
        if video_group.gr_gid in user_groups:
            print("✅ User is in video group")
        else:
            print("❌ User is NOT in video group")
            print("💡 Run: sudo usermod -a -G video $USER")
    except Exception as e:
        print(f"⚠️  Could not check video group: {e}")
    
    # Check DISPLAY variable
    display = os.environ.get('DISPLAY')
    if display:
        print(f"📺 DISPLAY={display}")
    else:
        print("❌ No DISPLAY environment variable (expected for CLI)")
    
    # Check if running over SSH
    ssh_client = os.environ.get('SSH_CLIENT')
    if ssh_client:
        print(f"🔗 SSH connection from: {ssh_client}")
        print("💡 Video may not show over SSH - check directly on Pi")
    
    # Check vcgencmd
    try:
        result = subprocess.run(['vcgencmd', 'display_power'], 
                              capture_output=True, text=True)
        print(f"🔌 Display power: {result.stdout.strip()}")
    except Exception as e:
        print(f"⚠️  Could not check display power: {e}")

def main():
    print("🐛 VLC Debugging Script for Raspberry Pi")
    print("=" * 50)
    
    # Test display info first
    test_display_info()
    
    # Test VLC configurations
    working_config = test_vlc_commands()
    
    if working_config:
        print(f"\n🎉 SUCCESS! Working configuration: {working_config['name']}")
        print("💡 I can update the Cat TV player to use this configuration")
    else:
        print("\n❌ No working VLC configuration found")
        print("💡 Try running this script directly on the Pi (not over SSH)")
        print("💡 Make sure audio/video drivers are working: speaker-test -t wav")

if __name__ == "__main__":
    main()