"""YouTube channel model."""

from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.sql import func
from .base import Base

class Channel(Base):
    """YouTube channel for cat entertainment."""
    
    __tablename__ = "channels"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False)
    url = Column(String(500), nullable=False)
    channel_id = Column(String(100))
    search_query = Column(String(500))  # For searching specific content
    is_active = Column(Boolean, default=True)
    priority = Column(Integer, default=0)  # Higher priority = more frequent play
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
    
    def __repr__(self):
        return f"<Channel(name='{self.name}', active={self.is_active})>"