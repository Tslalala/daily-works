from datetime import datetime

from sqlalchemy import Column, Date, DateTime, Integer, String, Text

from app.database import Base


class DailyLog(Base):
    __tablename__ = "daily_logs"

    id = Column(Integer, primary_key=True, index=True)
    log_date = Column(Date, nullable=False, unique=True)
    content = Column(Text, nullable=True)
    mood = Column(String(20), nullable=True)  # great / good / neutral / bad / awful
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
