"""Work clock-in/out service: flexible start, 8h work + 45min lunch.

Overtime = (clock_out - clock_in) - 8h45min, clamped at zero.
"""
from datetime import date, datetime, time, timedelta
from typing import List, Optional, Tuple

from sqlalchemy.orm import Session

from app.models.work_clockin import WorkClockin

WORK_SPAN = timedelta(hours=8)
LUNCH_BREAK = timedelta(minutes=45)
STANDARD_SPAN = WORK_SPAN + LUNCH_BREAK


def _now_minute() -> time:
    return datetime.now().replace(second=0, microsecond=0).time()


def get_by_date(db: Session, user_id: int, work_date: date) -> Optional[WorkClockin]:
    return db.query(WorkClockin).filter(
        WorkClockin.user_id == user_id, WorkClockin.work_date == work_date
    ).first()


def get_today(db: Session, user_id: int) -> Optional[WorkClockin]:
    return get_by_date(db, user_id, date.today())


def clock_in(db: Session, user_id: int) -> WorkClockin:
    rec = get_today(db, user_id)
    if rec:
        return rec
    rec = WorkClockin(user_id=user_id, work_date=date.today(), clock_in=_now_minute())
    db.add(rec)
    db.commit()
    db.refresh(rec)
    return rec


def clock_out(db: Session, user_id: int) -> Optional[WorkClockin]:
    rec = get_today(db, user_id)
    if not rec:
        return None
    rec.clock_out = _now_minute()
    db.commit()
    db.refresh(rec)
    return rec


def save_times(db: Session, user_id: int, work_date: date,
               clock_in: Optional[time], clock_out: Optional[time]) -> Optional[WorkClockin]:
    """Upsert one day's times. Both empty -> delete the record (un-count the day).

    00:00 can never be a real work clock time — some browsers serialize a
    cleared time input as "00:00" — so it is treated as "not provided".
    """
    if clock_in == time(0, 0):
        clock_in = None
    if clock_out == time(0, 0):
        clock_out = None
    rec = get_by_date(db, user_id, work_date)
    if clock_in is None and clock_out is None:
        if rec:
            db.delete(rec)
            db.commit()
        return None
    if rec is None:
        if clock_in is None:
            return None  # a record needs a clock-in
        rec = WorkClockin(user_id=user_id, work_date=work_date, clock_in=clock_in)
        db.add(rec)
    else:
        if clock_in is not None:
            rec.clock_in = clock_in
    if clock_out is not None:
        rec.clock_out = clock_out
    db.commit()
    db.refresh(rec)
    return rec


def suggested_out(clock_in: time) -> Tuple[time, bool]:
    """Suggested clock-out = clock-in + 8h45min. Returns (time, crosses_midnight)."""
    dt = datetime.combine(date.today(), clock_in) + STANDARD_SPAN
    return dt.time().replace(second=0, microsecond=0), dt.date() > date.today()


def _span(rec: WorkClockin) -> Optional[timedelta]:
    if not rec or not rec.clock_out:
        return None
    return datetime.combine(rec.work_date, rec.clock_out) - datetime.combine(rec.work_date, rec.clock_in)


def worked_minutes(rec: WorkClockin) -> Optional[int]:
    span = _span(rec)
    if span is None:
        return None
    return max(0, int((span - LUNCH_BREAK).total_seconds() // 60))


def overtime_minutes(rec: WorkClockin) -> Optional[int]:
    span = _span(rec)
    if span is None:
        return None
    return max(0, int((span - STANDARD_SPAN).total_seconds() // 60))


def history_items(db: Session, user_id: int, days: int = 30) -> List[dict]:
    """Last N days with worked/overtime pre-computed, newest first."""
    since = date.today() - timedelta(days=days - 1)
    recs: List[WorkClockin] = db.query(WorkClockin).filter(
        WorkClockin.user_id == user_id, WorkClockin.work_date >= since
    ).order_by(WorkClockin.work_date.desc()).all()
    return [{"rec": r, "worked": worked_minutes(r), "overtime": overtime_minutes(r)} for r in recs]
