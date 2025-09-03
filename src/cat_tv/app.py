"""Single application entry point that runs both scheduler and web interface."""

import logging
import sys
import threading

# Handle both direct execution and module execution
try:
    from .config import config
    from .models import init_db
    from .scheduler import CatTVScheduler
    from .web import app, socketio, set_scheduler, start_status_broadcast
except ImportError:
    # Direct execution - adjust path
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
    from src.cat_tv.config import config
    from src.cat_tv.models import init_db
    from src.cat_tv.scheduler import CatTVScheduler
    from src.cat_tv.web import app, socketio, set_scheduler, start_status_broadcast

logger = logging.getLogger(__name__)

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
    """Setup default schedules if none exist."""
    from .models import get_session, Schedule
    from datetime import time
    
    with get_session() as session:
        # Check if we have any schedules
        if session.query(Schedule).count() == 0:
            # Add default schedules (matching original times)
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
            
            session.commit()
            logger.info("Added default schedules")

class CatTVApp:
    """Main Cat TV application that runs both scheduler and web server."""
    
    def __init__(self):
        self.scheduler = None
        self.scheduler_thread = None
        self.running = False
        
    def setup(self):
        """Setup the application (lightweight setup for fast startup)."""
        setup_logging()
        logger.info("Starting Cat TV Application")
        logger.info(f"Running on Raspberry Pi: {config.IS_RASPBERRY_PI}")
        
        # Initialize database
        init_db()
        setup_default_data()
        
        # Create scheduler but don't set up schedules yet
        self.scheduler = CatTVScheduler()
        
        # Share scheduler with web interface for player status
        set_scheduler(self.scheduler)
        
    def run_scheduler(self):
        """Run the scheduler in a separate thread."""
        logger.info("Starting Cat TV scheduler thread")
        try:
            # Setup schedule here (this is where YouTube search happens)
            logger.info("Setting up schedules in background...")
            self.scheduler.setup_schedule()
            
            # Now run the scheduler
            self.scheduler.run()
        except Exception as e:
            logger.error(f"Scheduler error: {e}")
            
    def start_scheduler_thread(self):
        """Start the scheduler in a background thread."""
        self.scheduler_thread = threading.Thread(target=self.run_scheduler, daemon=True)
        self.scheduler_thread.start()
        
    def run(self):
        """Run the complete Cat TV application."""
        try:
            self.setup()
            
            # Start web server immediately in main thread
            logger.info(f"Starting web server on {config.FLASK_HOST}:{config.FLASK_PORT}")
            logger.info("Web interface will be available immediately")
            
            # Start scheduler in background thread (this will do YouTube searches etc.)
            self.start_scheduler_thread()
            
            # Start status broadcasting
            start_status_broadcast()
            
            # Run web server
            socketio.run(
                app, 
                host=config.FLASK_HOST, 
                port=config.FLASK_PORT, 
                debug=config.DEBUG,
                use_reloader=False,  # Don't use reloader in production
                allow_unsafe_werkzeug=True  # Allow Werkzeug in production (for embedded systems)
            )
            
        except KeyboardInterrupt:
            logger.info("Cat TV application stopped by user")
        except Exception as e:
            logger.error(f"Cat TV application error: {e}")
            sys.exit(1)
        finally:
            self.cleanup()
            
    def cleanup(self):
        """Cleanup when shutting down."""
        logger.info("Cleaning up Cat TV application")
        if self.scheduler:
            self.scheduler.player.stop()

def main():
    """Main entry point."""
    import os
    import pwd
    
    # Log user context immediately on startup with distinctive markers
    print(f"🔍 STARTUP USER CHECK: Real UID={os.getuid()}, Effective UID={os.geteuid()}")
    try:
        username = pwd.getpwuid(os.getuid()).pw_name
        print(f"🔍 STARTUP USER CHECK: Username='{username}'")
    except Exception as e:
        print(f"🔍 STARTUP USER CHECK: Could not get username: {e}")
    print(f"🔍 STARTUP USER CHECK: USER env={os.getenv('USER', 'NOT_SET')}")
    print(f"🔍 STARTUP USER CHECK: HOME env={os.getenv('HOME', 'NOT_SET')}")
    
    app = CatTVApp()
    app.run()

if __name__ == "__main__":
    main()