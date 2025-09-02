"""Flask web interface for Cat TV."""

import logging
from flask import Flask, render_template, request, jsonify, redirect, url_for
from flask_cors import CORS
from flask_socketio import SocketIO, emit
from datetime import datetime, time

from .config import config
from .models import init_db, get_session, Schedule, PlaybackLog
from .player import VideoPlayer
from .display import DisplayController
from .youtube import YouTubeManager

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = config.SECRET_KEY
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# Initialize components
player = VideoPlayer()
display = DisplayController()
youtube = YouTubeManager()

logger = logging.getLogger(__name__)

@app.route('/')
def index():
    """Main dashboard."""
    return render_template('index.html')

@app.route('/api/status')
def get_status():
    """Get current system status."""
    status = {
        'display': display.get_status(),
        'player': {
            'is_playing': player.is_playing(),
            'current_video': player.current_video
        },
        'time': datetime.now().isoformat()
    }
    return jsonify(status)

# Schedule Management
@app.route('/api/schedules')
def get_schedules():
    """Get all schedules from database."""
    with get_session() as session:
        schedules = session.query(Schedule).all()
        return jsonify([{
            'id': s.id,
            'name': s.name,
            'start_time': s.start_time.strftime('%H:%M'),
            'end_time': s.end_time.strftime('%H:%M'),
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
        
        return jsonify({'message': 'Schedule deleted successfully'})

# Playback Control
@app.route('/api/play', methods=['POST'])
def play_video():
    """Manually play a video."""
    data = request.json
    url = data.get('url')
    title = data.get('title', 'Manual Play')
    
    if url:
        display.turn_on()
        stream_url = youtube.get_stream_url(url) if url.startswith('http') else url
        if stream_url and player.play(stream_url, title):
            socketio.emit('status_update', {'playing': True, 'video': title})
            return jsonify({'message': 'Video started'})
    
    return jsonify({'error': 'Failed to play video'}), 400

@app.route('/api/stop', methods=['POST'])
def stop_video():
    """Stop current video."""
    player.stop()
    socketio.emit('status_update', {'playing': False})
    return jsonify({'message': 'Video stopped'})

@app.route('/api/display/<action>', methods=['POST'])
def control_display(action):
    """Control display power."""
    if action == 'on':
        success = display.turn_on()
    elif action == 'off':
        success = display.turn_off()
    else:
        return jsonify({'error': 'Invalid action'}), 400
    
    if success:
        socketio.emit('display_update', {'is_on': action == 'on'})
        return jsonify({'message': f'Display turned {action}'})
    return jsonify({'error': f'Failed to turn {action} display'}), 500

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

@socketio.on('request_status')
def handle_status_request():
    """Handle status request."""
    status = {
        'display': display.get_status(),
        'player': {
            'is_playing': player.is_playing(),
            'current_video': player.current_video
        }
    }
    emit('status_update', status)

def run_server():
    """Run the Flask server."""
    config.ensure_directories()
    init_db()
    
    logger.info(f"Starting web server on {config.FLASK_HOST}:{config.FLASK_PORT}")
    socketio.run(app, host=config.FLASK_HOST, port=config.FLASK_PORT, debug=config.DEBUG)

if __name__ == '__main__':
    run_server()