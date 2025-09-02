"""Playback logging model."""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.sql import func
from .base import Base

class PlaybackLog(Base):
    """Log of played videos."""
    
    __tablename__ = "playback_logs"
    
    id = Column(Integer, primary_key=True)
    channel_id = Column(Integer, ForeignKey("channels.id"))
    video_title = Column(String(500))
    video_url = Column(String(500))
    started_at = Column(DateTime, server_default=func.now())
    ended_at = Column(DateTime)
    status = Column(String(50))  # playing, completed, error
    error_message = Column(String(1000))
    
    def __repr__(self):
        return f"<PlaybackLog(video='{self.video_title}', status={self.status})>"