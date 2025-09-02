"""Schedule management for Cat TV."""

import logging
import schedule
import time
import random
from datetime import datetime, time as dt_time
from typing import Optional, List

from .models import get_session, PlaybackLog
from .player import VideoPlayer
from .display import DisplayController
from .youtube import YouTubeManager

logger = logging.getLogger(__name__)

class CatTVScheduler:
    """Manages the scheduling and playback of cat entertainment videos."""
    
    def __init__(self):
        self.player = VideoPlayer()
        self.display = DisplayController()
        self.youtube = YouTubeManager()
        self.is_play_time = False
        self.current_channel_index = 0
        
    def setup_schedule(self):
        """Setup scheduled Cat TV playback."""
        # Clear existing schedule
        schedule.clear()
        
        logger.info("Setting up Cat TV schedule")
        
        # Default schedule - Morning and Evening
        # Morning: 7:00 AM - 11:00 AM
        schedule.every().day.at("07:00").do(self.start_scheduled_playback, "Morning")
        schedule.every().day.at("11:00").do(self.stop_playback, "Morning ended")
        
        # Evening: 5:00 PM - 8:00 PM  
        schedule.every().day.at("17:00").do(self.start_scheduled_playback, "Evening")
        schedule.every().day.at("20:00").do(self.stop_playback, "Evening ended")
        
        logger.info("Scheduled Cat TV for:")
        logger.info("  Morning: 7:00 AM - 11:00 AM")
        logger.info("  Evening: 5:00 PM - 8:00 PM")
        
        # Check if we should be playing right now
        self.check_current_time()
        
        # Schedule video rotation every hour to prevent burn-in
        schedule.every().hour.do(self.rotate_video)
        
    
    def check_current_time(self):
        """Check if current time is within scheduled play times."""
        now = datetime.now()
        current_time = now.time()
        
        # Morning schedule: 7:00 AM - 11:00 AM
        morning_start = dt_time(7, 0)
        morning_end = dt_time(11, 0)
        
        # Evening schedule: 5:00 PM - 8:00 PM
        evening_start = dt_time(17, 0)
        evening_end = dt_time(20, 0)
        
        if morning_start <= current_time < morning_end:
            logger.info("Currently in morning schedule, starting playback")
            self.start_scheduled_playback("Morning (current time)")
        elif evening_start <= current_time < evening_end:
            logger.info("Currently in evening schedule, starting playback")
            self.start_scheduled_playback("Evening (current time)")
        else:
            logger.info("Outside scheduled hours, stopping playback")
            self.stop_playback("Outside scheduled hours")

    def start_scheduled_playback(self, schedule_name: str):
        """Start scheduled cat TV playback."""
        logger.info(f"Starting Cat TV playback for: {schedule_name}")
        
        if not self.is_play_time:
            self.is_play_time = True
            self.display.turn_on()
            time.sleep(1)  # Give display time to turn on
            self.play_cat_tv_video()
    
    def stop_playback(self, reason: str = "Manual stop"):
        """Stop playing videos."""
        logger.info(f"Stopping playback: {reason}")
        
        if self.is_play_time:
            self.is_play_time = False
            self.player.stop()
            time.sleep(1)  # Give player time to stop
            self.display.turn_off()
    
    def play_cat_tv_video(self):
        """Search and play long Cat TV videos."""
        if not self.is_play_time:
            return
            
        logger.info("Searching for Cat TV videos...")
        
        # Search for cat TV videos, preferring longer ones
        videos = self.youtube.search_videos("cat tv", max_results=20)
        
        if videos:
            # Filter for longer videos (over 30 minutes) or live streams
            long_videos = [v for v in videos if 
                          (v.get('duration') and v['duration'] > 1800) or  # 30+ minutes
                          v.get('is_live')]
            
            if not long_videos:
                # If no long videos, take any videos we found
                long_videos = videos
            
            # Sort by duration (longest first), handling None durations
            long_videos.sort(key=lambda x: x.get('duration') or float('inf'), reverse=True)
            
            # Try the top 3 longest videos
            for video in long_videos[:3]:
                logger.info(f"Trying video: {video['title']} ({video.get('duration', 'Live')} seconds)")
                
                # Get stream URL
                stream_url = self.youtube.get_stream_url(video['url'])
                if stream_url:
                    # Log playback
                    with get_session() as session:
                        log_entry = PlaybackLog(
                            video_title=video['title'],
                            video_url=video['url'],
                            status='playing'
                        )
                        session.add(log_entry)
                        session.commit()
                    
                    # Play video
                    if self.player.play(stream_url, video['title']):
                        logger.info(f"Now playing: {video['title']}")
                        return
                else:
                    logger.warning(f"Could not get stream URL for: {video['title']}")
            
        # Fallback if nothing worked
        logger.warning("No Cat TV videos found, trying fallback...")
        self.play_fallback_video()
    
    def play_fallback_video(self):
        """Play a fallback video when regular channels fail."""
        logger.info("Playing fallback video")
        
        video = self.youtube.get_random_cat_video()
        if video:
            stream_url = self.youtube.get_stream_url(video['url'])
            if stream_url:
                self.player.play(stream_url, video['title'])
                return
        
        logger.error("Failed to play any video")
    
    def rotate_video(self):
        """Rotate to a different video to prevent burn-in."""
        if self.is_play_time:
            logger.info("Rotating to next Cat TV video")
            self.player.stop()
            time.sleep(2)
            self.play_cat_tv_video()
    
    def run(self):
        """Run the scheduler."""
        logger.info("Cat TV Scheduler started")
        
        while True:
            try:
                schedule.run_pending()
                
                # Check if current video has ended
                if self.is_play_time and not self.player.is_playing():
                    logger.info("Video ended, playing next Cat TV video")
                    time.sleep(5)  # Brief pause between videos
                    self.play_cat_tv_video()
                
                time.sleep(10)  # Check every 10 seconds
                
            except KeyboardInterrupt:
                logger.info("Scheduler interrupted")
                break
            except Exception as e:
                logger.error(f"Scheduler error: {e}")
                time.sleep(30)  # Wait before retrying