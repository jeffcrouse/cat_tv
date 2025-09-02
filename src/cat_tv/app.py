"""Single application entry point that runs both scheduler and web interface."""

import logging
import sys
import threading

from .config import config
from .models import init_db
from .scheduler import CatTVScheduler
from .web import app, socketio
from .main import setup_logging, setup_default_data

logger = logging.getLogger(__name__)

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