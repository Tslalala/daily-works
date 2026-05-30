from datetime import date, datetime
from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.daily_log import DailyLog


def get_log(db: Session, log_date: date) -> Optional[DailyLog]:
    return db.query(DailyLog).filter(DailyLog.log_date == log_date).first()


def list_logs(db: Session, limit: int = 30) -> List[DailyLog]:
    return db.query(DailyLog).order_by(DailyLog.log_date.desc()).limit(limit).all()


def save_log(db: Session, log_date: date, content: str = "", mood: str = "") -> DailyLog:
    """Create or update a daily log."""
    existing = get_log(db, log_date)
    if existing:
        existing.content = content or None
        existing.mood = mood or None
        existing.updated_at = datetime.now()
        db.commit()
        db.refresh(existing)
        return existing
    dl = DailyLog(log_date=log_date, content=content or None, mood=mood or None)
    db.add(dl)
    db.commit()
    db.refresh(dl)
    return dl
