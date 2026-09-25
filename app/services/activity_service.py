from datetime import date, timedelta
from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.activity_log import ActivityLog


def log_action(db: Session, user_id: int, action: str, description: str, target_type: str = "", target_id: int = 0):
    entry = ActivityLog(
        user_id=user_id,
        action=action,
        description=description,
        target_type=target_type or None,
        target_id=target_id or None,
        log_date=date.today(),
    )
    db.add(entry)
    db.commit()


def remove_milestone_completion(db: Session, user_id: int, milestone_id: int):
    db.query(ActivityLog).filter(
        ActivityLog.user_id == user_id,
        ActivityLog.action == "complete_milestone",
        ActivityLog.target_id == milestone_id,
        ActivityLog.log_date == date.today(),
    ).delete()
    db.commit()


def remove_checkin_log(db: Session, user_id: int, habit_id: int):
    db.query(ActivityLog).filter(
        ActivityLog.user_id == user_id,
        ActivityLog.action == "checkin_habit",
        ActivityLog.target_id == habit_id,
        ActivityLog.log_date == date.today(),
    ).delete()
    db.commit()


def get_today_logs(db: Session, user_id: int) -> List[ActivityLog]:
    return (
        db.query(ActivityLog)
        .filter(ActivityLog.user_id == user_id, ActivityLog.log_date == date.today())
        .order_by(ActivityLog.timestamp.desc())
        .all()
    )


def get_logs_by_date(db: Session, user_id: int, log_date: date) -> List[ActivityLog]:
    return (
        db.query(ActivityLog)
        .filter(ActivityLog.user_id == user_id, ActivityLog.log_date == log_date)
        .order_by(ActivityLog.timestamp.desc())
        .all()
    )


def get_logs_by_date_range(db: Session, user_id: int, start: date, end: date) -> List[ActivityLog]:
    return (
        db.query(ActivityLog)
        .filter(
            ActivityLog.user_id == user_id,
            ActivityLog.log_date >= start,
            ActivityLog.log_date <= end,
        )
        .order_by(ActivityLog.log_date.desc(), ActivityLog.timestamp.desc())
        .all()
    )
