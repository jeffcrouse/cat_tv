"""Schedule management for Cat TV."""

import logging
import schedule
import time
import random
from datetime import datetime, time as dt_time
from typing import Optional, List

from .models import get_session, Schedule, PlaybackLog
from .player import VideoPlayer
from .youtube import YouTubeManager
from .display import DisplayController

logger = logging.getLogger(__name__)

class CatTVScheduler:
    """Manages the scheduling and playback of cat entertainment videos."""
    
    def __init__(self):
        # Initialize display controller first
        self.display = DisplayController()
        
        # Delay player initialization to avoid waking display
        self.player = None
        self.youtube = YouTubeManager()
        self.is_play_time = False
        self.current_channel_index = 0
        self._should_start_playing = False  # Flag to start playing immediately after setup
        
        # Immediately check if we should turn off display on startup
        self._initial_display_check()
        
        # Initialize player after display check
        self.player = VideoPlayer()
    
    def _initial_display_check(self):
        """Initial check on startup to turn off display if outside scheduled hours or start playback if within."""
        logger.info("Performing initial display check on startup...")
        
        now = datetime.now()
        current_time = now.time()
        current_day = now.weekday()
        
        # Check if we're in any active schedule
        is_in_schedule = False
        current_schedule_name = None
        
        try:
            with get_session() as session:
                schedules = session.query(Schedule).filter_by(is_active=True).all()
                
                for sched in schedules:
                    if sched.is_active_on_day(current_day):
                        # Handle schedules that cross midnight
                        if sched.start_time <= sched.end_time:
                            # Normal schedule
                            if sched.start_time <= current_time < sched.end_time:
                                logger.info(f"Startup: Currently in schedule '{sched.name}' - display should be ON")
                                is_in_schedule = True
                                current_schedule_name = sched.name
                                break
                        else:
                            # Schedule crosses midnight
                            if current_time >= sched.start_time or current_time < sched.end_time:
                                logger.info(f"Startup: Currently in schedule '{sched.name}' - display should be ON")
                                is_in_schedule = True
                                current_schedule_name = sched.name
                                break
        except Exception as e:
            logger.error(f"Error checking initial schedule: {e}")
            # On error, assume we should turn off display
            is_in_schedule = False
        
        # Turn off display if not in any schedule, or start playing if in schedule
        if not is_in_schedule:
            logger.info("🔴 Startup: Outside all scheduled hours - turning display OFF")
            if self.display.turn_off():
                logger.info("✅ Display turned off on startup")
                # Add a small delay to ensure display stays off
                time.sleep(2)
                # Turn off again in case something turned it back on
                self.display.turn_off()
            else:
                logger.warning("⚠️ Could not turn off display on startup")
        else:
            logger.info(f"🟢 Startup: Within scheduled hours ({current_schedule_name}) - starting playback immediately")
            # Set flag and start playback immediately
            self.is_play_time = True
            
            # Turn on display
            if self.display.turn_on():
                logger.info("✅ Display turned on for scheduled playback")
            else:
                logger.warning("⚠️ Could not turn on display, continuing anyway")
            
            # Start playing video immediately (in background thread after player is initialized)
            # Note: We can't play video here because player isn't initialized yet
            # We'll set a flag to start playing as soon as setup_schedule is called
            self._should_start_playing = True
        
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
        
        # Check if we should start playing immediately (set by _initial_display_check)
        if self._should_start_playing:
            logger.info("🎬 Starting playback immediately as we're within scheduled hours")
            self.play_cat_tv_video()
            self._should_start_playing = False  # Reset flag
        else:
            # Otherwise do the normal check
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
                            # Only start if not already playing
                            if not self.is_play_time:
                                self.start_scheduled_playback(f"{sched.name} (current time)")
                            else:
                                logger.info("Already in play time, continuing current video")
                            return
                    else:
                        # Schedule crosses midnight (e.g., 22:00 - 02:00)
                        if current_time >= sched.start_time or current_time < sched.end_time:
                            logger.info(f"Currently in schedule: {sched.name}")
                            # Only start if not already playing
                            if not self.is_play_time:
                                self.start_scheduled_playback(f"{sched.name} (current time)")
                            else:
                                logger.info("Already in play time, continuing current video")
                            return
        
        # No active schedule
        logger.info("Outside all scheduled hours")
        if self.is_play_time:
            logger.info("Stopping playback - outside scheduled hours")
            self.stop_playback("Outside scheduled hours")
        else:
            logger.info("Already stopped, ensuring display is off...")
            # Turn off display when outside scheduled hours (even if not playing)
            if self.display.turn_off():
                logger.info("✅ Display turned off - outside scheduled hours")
            else:
                logger.warning("⚠️ Could not turn off display")

    def start_scheduled_playback(self, schedule_name: str):
        """Start scheduled cat TV playback."""
        logger.info(f"Starting Cat TV playback for: {schedule_name}")
        
        if not self.is_play_time:
            # Turn on display first
            logger.info("🟢 Turning on display for scheduled playback...")
            if self.display.turn_on():
                logger.info("✅ Display turned on for playback")
            else:
                logger.warning("⚠️ Could not turn on display, continuing anyway")
            
            self.is_play_time = True
            self.play_cat_tv_video()
    
    def stop_playback(self, reason: str = "Manual stop"):
        """Stop playing videos."""
        logger.info(f"Stopping playback: {reason}")
        
        if self.is_play_time:
            self.is_play_time = False
            self.player.stop()
            
            # Turn off display when stopping scheduled playback
            if "scheduled" in reason.lower() or "outside" in reason.lower():
                logger.info("🔴 Turning off display - outside scheduled hours...")
                if self.display.turn_off():
                    logger.info("✅ Display turned off")
                else:
                    logger.warning("⚠️ Could not turn off display")
    
    def play_cat_tv_video(self):
        """Search and play long Cat TV videos."""
        if not self.is_play_time:
            return
            
        logger.info("Searching for Cat TV videos...")
        
        # Search for cat TV videos using fast cached search
        videos = self.youtube.search_videos_fast("cat tv", max_results=10)
        
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
            
            # Try only the first good video for faster startup
            for video in long_videos[:1]:  # Only try 1 video instead of 3
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
                    
                    # Try to play video with retries
                    logger.info(f"Attempting to play with VLC: {video['title']}")
                    play_success = self.player.play(stream_url, video['title'])
                    
                    if play_success:
                        logger.info(f"✅ VLC started successfully: {video['title']}")
                        
                        # Give VLC more time to stabilize and check multiple times
                        stable_count = 0
                        for check in range(5):  # Check 5 times over 5 seconds
                            time.sleep(1)
                            if self.player.is_playing():
                                stable_count += 1
                            else:
                                logger.warning(f"Check {check+1}: Video not playing")
                                break
                        
                        if stable_count >= 3:  # If playing for at least 3 seconds
                            logger.info(f"✅ Confirmed stable playback: {video['title']}")
                            
                            # Update log to success
                            with get_session() as session:
                                log_entry.status = 'playing'
                                session.add(log_entry)
                                session.commit()
                            return
                        else:
                            logger.warning(f"❌ VLC started but video stopped after {stable_count} seconds: {video['title']}")
                    else:
                        logger.warning(f"❌ Failed to start VLC for: {video['title']}")
                else:
                    logger.warning(f"❌ Could not get stream URL for: {video['title']}")
                    
            # If first video fails, try more videos from the list
            if len(long_videos) > 1:
                logger.info("First video failed, trying backup videos...")
                for video in long_videos[1:5]:  # Try up to 4 backup videos
                    logger.info(f"Trying backup: {video['title']}")
                    stream_url = self.youtube.get_stream_url(video['url'])
                    
                    if stream_url:
                        if self.player.play(stream_url, video['title']):
                            # Check stability for backup videos too
                            time.sleep(3)
                            if self.player.is_playing():
                                logger.info(f"✅ Backup video playing stably: {video['title']}")
                                return
                            else:
                                logger.warning(f"Backup video stopped: {video['title']}")
                    else:
                        logger.warning(f"Could not get stream for backup: {video['title']}")
            
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