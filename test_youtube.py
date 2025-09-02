#!/usr/bin/env python3
"""Test script for YouTube video extraction and playback."""

import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from cat_tv.youtube import YouTubeManager
from cat_tv.player import VideoPlayer
from cat_tv.display import DisplayController

def test_youtube_search():
    """Test YouTube search functionality."""
    print("=" * 50)
    print("Testing YouTube Search")
    print("=" * 50)
    
    youtube = YouTubeManager()
    
    # Test search
    print("Searching for 'cat tv for cats'...")
    videos = youtube.search_videos("cat tv for cats", max_results=3)
    
    if videos:
        print(f"Found {len(videos)} videos:")
        for i, video in enumerate(videos, 1):
            print(f"  {i}. {video['title']}")
            print(f"     ID: {video['id']}")
            print(f"     URL: {video['url']}")
            print(f"     Duration: {video.get('duration', 'Unknown')} seconds")
            print(f"     Live: {video.get('is_live', False)}")
            print()
        return videos
    else:
        print("No videos found!")
        return []

def test_stream_extraction(video_url):
    """Test stream URL extraction."""
    print("=" * 50)
    print("Testing Stream URL Extraction")
    print("=" * 50)
    
    youtube = YouTubeManager()
    
    print(f"Extracting stream URL for: {video_url}")
    stream_url = youtube.get_stream_url(video_url)
    
    if stream_url:
        print(f"Stream URL extracted successfully!")
        print(f"Length: {len(stream_url)} characters")
        print(f"First 100 chars: {stream_url[:100]}...")
        return stream_url
    else:
        print("Failed to extract stream URL!")
        return None

def test_random_cat_video():
    """Test getting random cat video."""
    print("=" * 50)
    print("Testing Random Cat Video")
    print("=" * 50)
    
    youtube = YouTubeManager()
    
    print("Getting random cat video...")
    video = youtube.get_random_cat_video()
    
    if video:
        print(f"Found video: {video['title']}")
        print(f"URL: {video['url']}")
        print(f"Duration: {video.get('duration', 'Unknown')} seconds")
        print(f"Live: {video.get('is_live', False)}")
        return video
    else:
        print("Failed to get random cat video!")
        return None

def test_display_control():
    """Test display control."""
    print("=" * 50)
    print("Testing Display Control")
    print("=" * 50)
    
    display = DisplayController()
    
    print("Getting display status...")
    status = display.get_status()
    print(f"Display status: {status}")
    
    print("Testing display on...")
    result = display.turn_on()
    print(f"Turn on result: {result}")
    
    return result

def test_vlc_availability():
    """Test if VLC is available."""
    print("=" * 50)
    print("Testing VLC Availability")
    print("=" * 50)
    
    import subprocess
    
    try:
        result = subprocess.run(['cvlc', '--version'], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print("VLC (cvlc) is available!")
            print(f"Version info: {result.stdout.split()[0:4]}")
            return True
        else:
            print("VLC returned non-zero exit code")
            return False
    except subprocess.TimeoutExpired:
        print("VLC command timed out")
        return False
    except FileNotFoundError:
        print("VLC (cvlc) not found! Install with: sudo apt-get install vlc")
        return False
    except Exception as e:
        print(f"Error testing VLC: {e}")
        return False

def test_actual_playback():
    """Test actual video playback with VLC."""
    print("=" * 50)
    print("Testing Actual VLC Playback")
    print("=" * 50)
    
    from cat_tv.player import VideoPlayer
    
    player = VideoPlayer()
    
    # Get a working video
    youtube = YouTubeManager()
    videos = youtube.search_videos("cat tv", max_results=5)
    
    if not videos:
        print("No videos found for playback test!")
        return False
    
    # Try the first few videos
    for i, video in enumerate(videos[:3]):
        print(f"\nTrying video {i+1}: {video['title']}")
        
        # Get stream URL
        stream_url = youtube.get_stream_url(video['url'])
        if not stream_url:
            print(f"  ❌ Failed to get stream URL")
            continue
            
        print(f"  ✓ Got stream URL: {stream_url[:100]}...")
        
        # Try to play
        print(f"  🎬 Attempting to play with VLC...")
        success = player.play(stream_url, video['title'])
        
        if success:
            print(f"  ✅ VLC started successfully!")
            print(f"  📺 Playing: {video['title']}")
            
            # Check if still playing after a moment
            import time
            time.sleep(3)
            if player.is_playing():
                print(f"  🎵 Confirmed: Video is playing!")
                player.stop()
                print(f"  ⏹ Stopped playback")
                return True
            else:
                print(f"  ❌ Video started but stopped immediately")
                player.stop()
        else:
            print(f"  ❌ Failed to start VLC")
    
    print(f"\n❌ All playback attempts failed!")
    return False

def main():
    """Run all tests."""
    print("Cat TV Test Suite")
    print("=" * 50)
    
    # Test 1: VLC availability
    vlc_available = test_vlc_availability()
    
    # Test 2: Display control
    display_working = test_display_control()
    
    # Test 3: YouTube search
    videos = test_youtube_search()
    
    # Test 4: Random cat video
    random_video = test_random_cat_video()
    
    # Test 5: Stream extraction (if we have videos)
    stream_url = None
    if videos:
        print("Testing stream extraction with first found video...")
        stream_url = test_stream_extraction(videos[0]['url'])
    elif random_video:
        print("Testing stream extraction with random video...")
        stream_url = test_stream_extraction(random_video['url'])
    
    # Test 6: Actual playback
    playback_working = False
    if stream_url:
        playback_working = test_actual_playback()
    
    # Summary
    print("=" * 50)
    print("TEST SUMMARY")
    print("=" * 50)
    print(f"VLC Available: {'✓' if vlc_available else '✗'}")
    print(f"Display Control: {'✓' if display_working else '✗'}")
    print(f"YouTube Search: {'✓' if videos else '✗'}")
    print(f"Random Video: {'✓' if random_video else '✗'}")
    print(f"Stream Extraction: {'✓' if stream_url else '✗'}")
    print(f"Actual Playback: {'✓' if playback_working else '✗'}")
    
    if all([vlc_available, videos or random_video, stream_url, playback_working]):
        print("\n🎉 All components working! Cat TV should work properly.")
    else:
        print("\n⚠️  Some components have issues. Check the logs above.")
        
    return videos, stream_url

if __name__ == "__main__":
    main()