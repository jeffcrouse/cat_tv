#!/usr/bin/env python3
"""Test scheduler with immediate playback."""

import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from cat_tv.scheduler import CatTVScheduler
import time

def test_immediate_playback():
    """Test immediate Cat TV playback regardless of schedule."""
    print("🐱 Testing Immediate Cat TV Playback")
    print("=" * 50)
    
    scheduler = CatTVScheduler()
    
    print("📺 Turning on display...")
    scheduler.display.turn_on()
    
    print("🎬 Starting playback (ignoring schedule)...")
    scheduler.is_play_time = True
    scheduler.play_cat_tv_video()
    
    print("⏰ Checking if video is playing...")
    time.sleep(3)
    
    if scheduler.player.is_playing():
        print("✅ SUCCESS! Video is playing on screen!")
        print(f"🎵 Currently playing: {scheduler.player.current_video}")
        
        # Let it play for 10 seconds
        print("🎬 Letting video play for 10 seconds...")
        time.sleep(10)
        
        print("⏹ Stopping playback...")
        scheduler.player.stop()
        print("✅ Test completed successfully!")
        
    else:
        print("❌ FAILED: Video is not playing")
        print("Check the logs above for errors")

if __name__ == "__main__":
    test_immediate_playback()