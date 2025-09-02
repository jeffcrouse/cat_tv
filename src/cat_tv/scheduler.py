"""Schedule management for Cat TV."""

import logging
import schedule
import time
import random
from datetime import datetime, time as dt_time
from typing import Optional, List

from .models import get_session, Schedule, PlaybackLog
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
        """Setup scheduled Cat TV playback from database."""
        # Clear existing schedule
        schedule.clear()
        
        logger.info("Setting up Cat TV schedule from database")
        
        with get_session() as session:
            schedules = session.query(Schedule).filter_by(is_active=True).all()
            
            for sched in schedules:
                # Schedule start time
                start_time = sched.start_time.strftime("%H:%M")
                schedule.every().day.at(start_time).do(self.start_scheduled_playback, sched.name)
                logger.info(f"Scheduled start at {start_time} for {sched.name}")
                
                # Schedule end time
                end_time = sched.end_time.strftime("%H:%M")
                schedule.every().day.at(end_time).do(self.stop_playback, f"{sched.name} ended")
                logger.info(f"Scheduled stop at {end_time} for {sched.name}")
        
        # Check if we should be playing right now
        self.check_current_time()
        
        # Schedule video rotation every hour to prevent burn-in
        schedule.every().hour.do(self.rotate_video)
        
    
    def check_current_time(self):
        """Check if current time is within any scheduled play times."""
        now = datetime.now()
        current_time = now.time()
        current_day = now.weekday()  # 0=Monday, 6=Sunday
        
        with get_session() as session:
            schedules = session.query(Schedule).filter_by(is_active=True).all()
            
            for sched in schedules:
                if sched.is_active_on_day(current_day):
                    # Handle schedules that cross midnight
                    if sched.start_time <= sched.end_time:
                        # Normal schedule (e.g., 9:00 - 17:00)
                        if sched.start_time <= current_time < sched.end_time:
                            logger.info(f"Currently in schedule: {sched.name}")
                            self.start_scheduled_playback(f"{sched.name} (current time)")
                            return
                    else:
                        # Schedule crosses midnight (e.g., 22:00 - 02:00)
                        if current_time >= sched.start_time or current_time < sched.end_time:
                            logger.info(f"Currently in schedule: {sched.name}")
                            self.start_scheduled_playback(f"{sched.name} (current time)")
                            return
        
        # No active schedule
        logger.info("Outside all scheduled hours, stopping playback")
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
                logger.info(f"Getting stream URL for: {video['url']}")
                stream_url = self.youtube.get_stream_url(video['url'])
                
                if stream_url:
                    logger.info(f"Got stream URL (length: {len(stream_url)} chars)")
                    
                    # Log playback attempt
                    with get_session() as session:
                        log_entry = PlaybackLog(
                            video_title=video['title'],
                            video_url=video['url'],
                            status='attempting'
                        )
                        session.add(log_entry)
                        session.commit()
                    
                    # Try to play video
                    logger.info(f"Attempting to play with VLC: {video['title']}")
                    play_success = self.player.play(stream_url, video['title'])
                    
                    if play_success:
                        logger.info(f"✅ VLC started successfully: {video['title']}")
                        
                        # Wait a moment and check if still playing
                        time.sleep(2)
                        if self.player.is_playing():
                            logger.info(f"✅ Confirmed playing: {video['title']}")
                            
                            # Update log to success
                            with get_session() as session:
                                log_entry.status = 'playing'
                                session.add(log_entry)
                                session.commit()
                            return
                        else:
                            logger.warning(f"❌ VLC started but video stopped immediately: {video['title']}")
                    else:
                        logger.warning(f"❌ Failed to start VLC for: {video['title']}")
                else:
                    logger.warning(f"❌ Could not get stream URL for: {video['title']}")
            
        # Fallback if nothing worked
        logger.warning("No Cat TV videos worked, trying fallback...")
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