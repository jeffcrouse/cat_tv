"""Flask web interface for Cat TV."""

import logging
import threading
import time as time_module
from flask import Flask, render_template, request, jsonify, redirect, url_for
from flask_cors import CORS
from flask_socketio import SocketIO, emit
from datetime import datetime, time

from .config import config
from .models import init_db, get_session, Schedule, PlaybackLog
from .player import VideoPlayer
from .youtube import YouTubeManager
from .display import DisplayController

# Initialize Flask app
app = Flask(__name__, 
            static_folder='static',
            static_url_path='/static')
app.config['SECRET_KEY'] = config.SECRET_KEY
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# Initialize components
player = VideoPlayer()  # This will be replaced by scheduler's player
youtube = YouTubeManager()
display = DisplayController()

# Global reference to scheduler (set by app.py)
_scheduler = None
_status_broadcast_thread = None
_status_broadcast_running = False

def set_scheduler(scheduler):
    """Set the scheduler reference so we can access its player."""
    global _scheduler
    _scheduler = scheduler

logger = logging.getLogger(__name__)

def get_status_data():
    """Get current status data for broadcasting."""
    # Use scheduler's player if available, fallback to local player
    active_player = _scheduler.player if _scheduler else player
    
    # Use scheduler's display if available, fallback to local display
    active_display = _scheduler.display if _scheduler else display
    
    # Check which schedule is currently active
    current_schedule = get_current_active_schedule()
    
    return {
        'player': {
            'is_playing': active_player.is_playing(),
            'current_video': active_player.current_video
        },
        'scheduler': {
            'is_play_time': _scheduler.is_play_time if _scheduler else False,
            'current_schedule': current_schedule
        },
        'display': active_display.get_status(),
        'time': datetime.now().isoformat()
    }

def status_broadcast_worker():
    """Background thread that broadcasts status every second."""
    global _status_broadcast_running
    
    logger.info("Starting status broadcast worker")
    
    while _status_broadcast_running:
        try:
            status = get_status_data()
            socketio.emit('status_update', status)
        except Exception as e:
            logger.error(f"Error broadcasting status: {e}")
        
        time_module.sleep(1)
    
    logger.info("Status broadcast worker stopped")

def start_status_broadcast():
    """Start the status broadcast background thread."""
    global _status_broadcast_thread, _status_broadcast_running
    
    if not _status_broadcast_running:
        _status_broadcast_running = True
        _status_broadcast_thread = threading.Thread(target=status_broadcast_worker, daemon=True)
        _status_broadcast_thread.start()
        logger.info("Status broadcast started")

def stop_status_broadcast():
    """Stop the status broadcast background thread."""
    global _status_broadcast_running
    
    if _status_broadcast_running:
        _status_broadcast_running = False
        logger.info("Status broadcast stopped")

@app.route('/')
def index():
    """Main dashboard."""
    return render_template('index.html')

@app.route('/api/status')
def get_status():
    """Get current system status."""
    return jsonify(get_status_data())

def get_current_active_schedule():
    """Get the currently active schedule, if any."""
    try:
        now = datetime.now()
        current_time = now.time()
        current_day = now.weekday()  # 0=Monday, 6=Sunday
        
        with get_session() as session:
            schedules = session.query(Schedule).filter_by(is_active=True).all()
            
            for sched in schedules:
                if sched.is_active_on_day(current_day):
                    # Check if we're in the time window
                    if sched.start_time <= sched.end_time:
                        # Normal schedule (e.g., 14:00 - 16:00)
                        if sched.start_time <= current_time < sched.end_time:
                            return {
                                'name': sched.name,
                                'start_time': sched.start_time.strftime('%I:%M %p'),
                                'end_time': sched.end_time.strftime('%I:%M %p')
                            }
                    else:
                        # Schedule crosses midnight (e.g., 22:00 - 02:00)
                        if current_time >= sched.start_time or current_time < sched.end_time:
                            return {
                                'name': sched.name,
                                'start_time': sched.start_time.strftime('%I:%M %p'),
                                'end_time': sched.end_time.strftime('%I:%M %p')
                            }
        
        return None
        
    except Exception as e:
        logger.error(f"Error checking active schedule: {e}")
        return None

# Schedule Management
@app.route('/api/schedules')
def get_schedules():
    """Get all schedules from database."""
    with get_session() as session:
        schedules = session.query(Schedule).all()
        return jsonify([{
            'id': s.id,
            'name': s.name,
            'start_time': s.start_time.strftime('%I:%M %p'),
            'end_time': s.end_time.strftime('%I:%M %p'),
            'days_of_week': s.days_of_week,
            'is_active': s.is_active
        } for s in schedules])

@app.route('/api/schedules', methods=['POST'])
def add_schedule():
    """Add a new schedule."""
    try:
        data = request.json
        logger.info(f"Received schedule data: {data}")
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
            
        # Validate required fields
        required_fields = ['name', 'start_time', 'end_time']
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        with get_session() as session:
            schedule = Schedule(
                name=data['name'],
                start_time=time.fromisoformat(data['start_time']),
                end_time=time.fromisoformat(data['end_time']),
                days_of_week=data.get('days_of_week', '0,1,2,3,4,5,6'),
                is_active=data.get('is_active', True)
            )
            session.add(schedule)
            session.commit()
            
            logger.info(f"Created schedule: {schedule.name} ({schedule.start_time}-{schedule.end_time})")
            
            # Notify scheduler to reload schedules
            socketio.emit('schedule_updated', {'action': 'reload'})
            
            # Tell scheduler to reload and check current time
            if _scheduler:
                logger.info("Schedule added, reloading scheduler and checking current time")
                _scheduler.setup_schedule()  # Reload schedules and check if should be playing
            
            return jsonify({'id': schedule.id, 'message': 'Schedule added successfully'})
            
    except ValueError as e:
        logger.error(f"Invalid time format: {e}")
        return jsonify({'error': 'Invalid time format. Use HH:MM format'}), 400
    except Exception as e:
        logger.error(f"Error creating schedule: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/schedules/<int:schedule_id>', methods=['PUT']) 
def update_schedule(schedule_id):
    """Update a schedule."""
    data = request.json
    
    with get_session() as session:
        schedule = session.query(Schedule).get(schedule_id)
        if not schedule:
            return jsonify({'error': 'Schedule not found'}), 404
        
        schedule.name = data.get('name', schedule.name)
        if 'start_time' in data:
            schedule.start_time = time.fromisoformat(data['start_time'])
        if 'end_time' in data:
            schedule.end_time = time.fromisoformat(data['end_time'])
        schedule.days_of_week = data.get('days_of_week', schedule.days_of_week)
        schedule.is_active = data.get('is_active', schedule.is_active)
        session.commit()
        
        # Notify scheduler to reload schedules
        socketio.emit('schedule_updated', {'action': 'reload'})
        
        # Tell scheduler to reload and check current time
        if _scheduler:
            logger.info("Schedule updated, reloading scheduler and checking current time")
            _scheduler.setup_schedule()  # Reload schedules and check if should be playing
        
        return jsonify({'message': 'Schedule updated successfully'})

@app.route('/api/schedules/<int:schedule_id>', methods=['DELETE'])
def delete_schedule(schedule_id):
    """Delete a schedule."""
    with get_session() as session:
        schedule = session.query(Schedule).get(schedule_id)
        if not schedule:
            return jsonify({'error': 'Schedule not found'}), 404
        
        session.delete(schedule)
        session.commit()
        
        # Notify scheduler to reload schedules
        socketio.emit('schedule_updated', {'action': 'reload'})
        
        # Tell scheduler to reload and check current time
        if _scheduler:
            logger.info("Schedule deleted, reloading scheduler and checking current time")
            _scheduler.setup_schedule()  # Reload schedules and check if should be playing
        
        return jsonify({'message': 'Schedule deleted successfully'})

# Playback Control
@app.route('/api/play', methods=['POST'])
def play_video():
    """Manually play a video."""
    data = request.json
    url = data.get('url')
    title = data.get('title', 'Manual Play')
    
    if url:
        stream_url = youtube.get_stream_url(url) if url.startswith('http') else url
        if stream_url and player.play(stream_url, title):
            socketio.emit('status_update', {'playing': True, 'video': title})
            return jsonify({'message': 'Video started'})
    
    return jsonify({'error': 'Failed to play video'}), 400

@app.route('/api/stop', methods=['POST'])
def stop_video():
    """Stop current video."""
    # Use scheduler's player if available, fallback to local player
    active_player = _scheduler.player if _scheduler else player
    active_player.stop()
    socketio.emit('status_update', {'playing': False})
    return jsonify({'message': 'Video stopped'})

# Display Control
@app.route('/api/display/on', methods=['POST'])
def display_on():
    """Turn display on."""
    # Use scheduler's display if available, fallback to local display
    active_display = _scheduler.display if _scheduler else display
    
    if active_display.turn_on():
        return jsonify({'message': 'Display turned on'})
    else:
        return jsonify({'error': 'Failed to turn display on'}), 500

@app.route('/api/display/off', methods=['POST'])
def display_off():
    """Turn display off."""
    # Use scheduler's display if available, fallback to local display
    active_display = _scheduler.display if _scheduler else display
    
    if active_display.turn_off():
        return jsonify({'message': 'Display turned off'})
    else:
        return jsonify({'error': 'Failed to turn display off'}), 500

@app.route('/api/display/status')
def display_status():
    """Get display status."""
    # Use scheduler's display if available, fallback to local display
    active_display = _scheduler.display if _scheduler else display
    return jsonify(active_display.get_status())

# Playback History
@app.route('/api/history')
def get_history():
    """Get playback history."""
    with get_session() as session:
        logs = session.query(PlaybackLog).order_by(PlaybackLog.started_at.desc()).limit(50).all()
        return jsonify([{
            'id': log.id,
            'video_title': log.video_title,
            'started_at': log.started_at.isoformat() if log.started_at else None,
            'ended_at': log.ended_at.isoformat() if log.ended_at else None,
            'status': log.status
        } for log in logs])

# WebSocket events
@socketio.on('connect')
def handle_connect():
    """Handle client connection."""
    logger.info("Client connected")
    emit('connected', {'message': 'Connected to Cat TV'})
    
    # Start status broadcasting when first client connects
    start_status_broadcast()

@socketio.on('request_status')
def handle_status_request():
    """Handle status request."""
    emit('status_update', get_status_data())

def run_server():
    """Run the Flask server."""
    config.ensure_directories()
    init_db()
    
    logger.info(f"Starting web server on {config.FLASK_HOST}:{config.FLASK_PORT}")
    try:
        socketio.run(app, host=config.FLASK_HOST, port=config.FLASK_PORT, debug=config.DEBUG)
    finally:
        # Stop status broadcasting when server shuts down
        stop_status_broadcast()

if __name__ == '__main__':
    run_server()