from datetime import date, datetime

from sqlalchemy import Column, Date, DateTime, Integer, String

from app.database import Base


class ActivityLog(Base):
    __tablename__ = "activity_logs"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.now)
    log_date = Column(Date, default=date.today, index=True)
    action = Column(String(50), nullable=False)
    description = Column(String(500), nullable=False)
    target_type = Column(String(50), nullable=True)
    target_id = Column(Integer, nullable=True)
