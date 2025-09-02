"""Single application entry point that runs both scheduler and web interface."""

import logging
import sys
import threading

# Handle both direct execution and module execution
try:
    from .config import config
    from .models import init_db
    from .scheduler import CatTVScheduler
    from .web import app, socketio
except ImportError:
    # Direct execution - adjust path
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
    from src.cat_tv.config import config
    from src.cat_tv.models import init_db
    from src.cat_tv.scheduler import CatTVScheduler
    from src.cat_tv.web import app, socketio

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
    """Setup default data if none exists."""
    # We don't need default channels/schedules anymore since we just search "cat tv"
    # Only keeping playback logs
    pass

class CatTVApp:
    """Main Cat TV application that runs both scheduler and web server."""
    
    def __init__(self):
        self.scheduler = None
        self.scheduler_thread = None
        self.running = False
        
    def setup(self):
        """Setup the application."""
        setup_logging()
        logger.info("Starting Cat TV Application")
        logger.info(f"Running on Raspberry Pi: {config.IS_RASPBERRY_PI}")
        
        # Initialize database
        init_db()
        setup_default_data()
        
        # Create scheduler
        self.scheduler = CatTVScheduler()
        self.scheduler.setup_schedule()
        
    def run_scheduler(self):
        """Run the scheduler in a separate thread."""
        logger.info("Starting Cat TV scheduler thread")
        try:
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
            
            # Start scheduler in background thread
            self.start_scheduler_thread()
            
            # Start web server in main thread
            logger.info(f"Starting web server on {config.FLASK_HOST}:{config.FLASK_PORT}")
            socketio.run(
                app, 
                host=config.FLASK_HOST, 
                port=config.FLASK_PORT, 
                debug=config.DEBUG,
                use_reloader=False  # Don't use reloader in production
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
    app = CatTVApp()
    app.run()

if __name__ == "__main__":
    main()