from datetime import datetime

from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship

from app.database import Base


class Habit(Base):
    __tablename__ = "habits"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    frequency = Column(String(20), default="daily")  # daily / weekly
    icon = Column(String(50), default="📌")
    status = Column(String(20), default="active")  # active / archived
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    checkins = relationship("CheckIn", back_populates="habit", cascade="all, delete-orphan")


class CheckIn(Base):
    __tablename__ = "checkins"

    id = Column(Integer, primary_key=True, index=True)
    habit_id = Column(Integer, ForeignKey("habits.id"), nullable=False)
    checkin_date = Column(Date, nullable=False)
    note = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.now)

    habit = relationship("Habit", back_populates="checkins")

    __table_args__ = (
        UniqueConstraint("habit_id", "checkin_date", name="uq_habit_date"),
    )
