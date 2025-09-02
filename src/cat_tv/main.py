"""Main entry point for Cat TV."""

import logging
import sys
from pathlib import Path

from .config import config
from .models import init_db, get_session, Channel, Schedule
from .scheduler import CatTVScheduler

def setup_logging():
    """Setup logging configuration."""
    config.ensure_directories()
    
    logging.basicConfig(
        level=getattr(logging, config.LOG_LEVEL),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(config.LOG_FILE),
            logging.StreamHandler(sys.stdout)
        ]
    )

def setup_default_data():
    """Setup default channels and schedules if none exist."""
    with get_session() as session:
        # Check if we have any channels
        if session.query(Channel).count() == 0:
            # Add default channels
            default_channels = [
                Channel(
                    name="Cat TV - Birds and Squirrels",
                    search_query="cat tv for cats to watch birds squirrels 4K",
                    priority=10,
                    is_active=True
                ),
                Channel(
                    name="Cat TV - Mice and Games",
                    search_query="videos for cats to watch mice games",
                    priority=5,
                    is_active=True
                ),
                Channel(
                    name="Paul Dinning Wildlife",
                    url="https://www.youtube.com/@pauldinning",
                    priority=8,
                    is_active=True
                ),
            ]
            
            for channel in default_channels:
                session.add(channel)
            
            logging.info("Added default channels")
        
        # Check if we have any schedules
        if session.query(Schedule).count() == 0:
            # Add default schedules (matching original times)
            from datetime import time
            
            default_schedules = [
                Schedule(
                    name="Morning Play",
                    start_time=time(7, 0),
                    end_time=time(11, 0),
                    days_of_week="0,1,2,3,4,5,6",
                    is_active=True
                ),
                Schedule(
                    name="Evening Play",
                    start_time=time(17, 0),
                    end_time=time(20, 0),
                    days_of_week="0,1,2,3,4,5,6",
                    is_active=True
                ),
            ]
            
            for schedule in default_schedules:
                session.add(schedule)
            
            logging.info("Added default schedules")
        
        session.commit()

def main():
    """Main entry point."""
    setup_logging()
    logger = logging.getLogger(__name__)
    
    logger.info("Starting Cat TV")
    logger.info(f"Running on Raspberry Pi: {config.IS_RASPBERRY_PI}")
    
    # Initialize database
    init_db()
    setup_default_data()
    
    # Create and run scheduler
    scheduler = CatTVScheduler()
    scheduler.setup_schedule()
    
    try:
        scheduler.run()
    except KeyboardInterrupt:
        logger.info("Cat TV stopped by user")
    except Exception as e:
        logger.error(f"Cat TV error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()