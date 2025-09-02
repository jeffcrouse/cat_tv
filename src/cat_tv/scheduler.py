"""Schedule management for Cat TV."""

import logging
import schedule
import time
import random
from datetime import datetime, time as dt_time
from typing import Optional, List

from .models import get_session, Channel, Schedule, PlaybackLog
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
        """Setup the schedule based on database entries."""
        # Clear existing schedule
        schedule.clear()
        
        with get_session() as session:
            schedules = session.query(Schedule).filter_by(is_active=True).all()
            
            for sched in schedules:
                # Schedule start time
                start_time = sched.start_time.strftime("%H:%M")
                schedule.every().day.at(start_time).do(self.start_playback, sched.name)
                logger.info(f"Scheduled start at {start_time} for {sched.name}")
                
                # Schedule end time
                end_time = sched.end_time.strftime("%H:%M")
                schedule.every().day.at(end_time).do(self.stop_playback, sched.name)
                logger.info(f"Scheduled stop at {end_time} for {sched.name}")
        
        # Check current time to see if we should be playing
        self.check_current_schedule()
        
        # Schedule video rotation every hour during play time
        schedule.every().hour.do(self.rotate_video)
        
    def check_current_schedule(self):
        """Check if current time is within any active schedule."""
        now = datetime.now()
        current_time = now.time()
        current_day = now.weekday()
        
        with get_session() as session:
            schedules = session.query(Schedule).filter_by(is_active=True).all()
            
            for sched in schedules:
                if sched.is_active_on_day(current_day):
                    # Handle schedules that cross midnight
                    if sched.start_time <= sched.end_time:
                        # Normal schedule (e.g., 9:00 - 17:00)
                        if sched.start_time <= current_time <= sched.end_time:
                            logger.info(f"Currently in schedule: {sched.name}")
                            self.start_playback(sched.name)
                            return
                    else:
                        # Schedule crosses midnight (e.g., 22:00 - 02:00)
                        if current_time >= sched.start_time or current_time <= sched.end_time:
                            logger.info(f"Currently in schedule: {sched.name}")
                            self.start_playback(sched.name)
                            return
        
        # No active schedule
        logger.info("No active schedule at current time")
        self.stop_playback("No active schedule")
    
    def start_playback(self, schedule_name: str):
        """Start playing videos."""
        logger.info(f"Starting playback for schedule: {schedule_name}")
        
        if not self.is_play_time:
            self.is_play_time = True
            self.display.turn_on()
            time.sleep(1)  # Give display time to turn on
            self.play_next_video()
    
    def stop_playback(self, schedule_name: str):
        """Stop playing videos."""
        logger.info(f"Stopping playback for schedule: {schedule_name}")
        
        if self.is_play_time:
            self.is_play_time = False
            self.player.stop()
            time.sleep(1)  # Give player time to stop
            self.display.turn_off()
    
    def play_next_video(self):
        """Play the next video from available channels."""
        if not self.is_play_time:
            return
            
        with get_session() as session:
            # Get active channels
            channels = session.query(Channel).filter_by(is_active=True).order_by(Channel.priority.desc()).all()
            
            if not channels:
                logger.warning("No active channels found")
                self.play_fallback_video()
                return
            
            # Rotate through channels
            channel = channels[self.current_channel_index % len(channels)]
            self.current_channel_index += 1
            
            video = None
            
            # Try to get video from channel
            if channel.search_query:
                videos = self.youtube.search_videos(channel.search_query, max_results=5)
                if videos:
                    video = random.choice(videos)
            elif channel.url:
                videos = self.youtube.get_channel_videos(channel.url, max_results=10)
                if videos:
                    video = random.choice(videos)
            
            if video:
                # Get stream URL
                stream_url = self.youtube.get_stream_url(video['url'])
                if stream_url:
                    # Log playback
                    log_entry = PlaybackLog(
                        channel_id=channel.id,
                        video_title=video['title'],
                        video_url=video['url'],
                        status='playing'
                    )
                    session.add(log_entry)
                    session.commit()
                    
                    # Play video
                    if self.player.play(stream_url, video['title']):
                        logger.info(f"Playing: {video['title']}")
                        return
            
            # Fallback if no video found
            logger.warning(f"Could not get video from channel: {channel.name}")
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
            logger.info("Rotating video")
            self.player.stop()
            time.sleep(2)
            self.play_next_video()
    
    def run(self):
        """Run the scheduler."""
        logger.info("Cat TV Scheduler started")
        
        while True:
            try:
                schedule.run_pending()
                
                # Check if current video has ended
                if self.is_play_time and not self.player.is_playing():
                    logger.info("Video ended, playing next")
                    time.sleep(5)  # Brief pause between videos
                    self.play_next_video()
                
                time.sleep(10)  # Check every 10 seconds
                
            except KeyboardInterrupt:
                logger.info("Scheduler interrupted")
                break
            except Exception as e:
                logger.error(f"Scheduler error: {e}")
                time.sleep(30)  # Wait before retrying