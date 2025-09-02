"""Schedule model for play times."""

from sqlalchemy import Column, Integer, String, Time, Boolean
from .base import Base

class Schedule(Base):
    """Schedule for when videos should play."""
    
    __tablename__ = "schedules"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    days_of_week = Column(String(20), default="0,1,2,3,4,5,6")  # 0=Monday, 6=Sunday
    is_active = Column(Boolean, default=True)
    
    def __repr__(self):
        return f"<Schedule(name='{self.name}', {self.start_time}-{self.end_time})>"
    
    def is_active_on_day(self, day: int) -> bool:
        """Check if schedule is active on given day (0=Monday, 6=Sunday)."""
        active_days = [int(d) for d in self.days_of_week.split(",")]
        return day in active_days