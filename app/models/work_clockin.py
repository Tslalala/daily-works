from datetime import datetime

from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, Time, UniqueConstraint

from app.database import Base


class WorkClockin(Base):
    """One work-day clock-in/out record per user. Flexible start (7:30-9:30),
    45-min lunch break; times are kept at minute precision."""
    __tablename__ = "work_clockins"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    work_date = Column(Date, nullable=False)
    clock_in = Column(Time, nullable=False)
    clock_out = Column(Time, nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    __table_args__ = (UniqueConstraint("user_id", "work_date", name="uq_user_work_date"),)
