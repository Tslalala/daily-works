from datetime import date, datetime
from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.habit import CheckIn, Habit


def list_habits(db: Session, status: Optional[str] = "active") -> List[Habit]:
    q = db.query(Habit)
    if status:
        q = q.filter(Habit.status == status)
    return q.all()


def get_habit(db: Session, habit_id: int) -> Optional[Habit]:
    return db.query(Habit).filter(Habit.id == habit_id).first()


def create_habit(db: Session, name: str, icon: str = "📌", description: str = "", frequency: str = "daily") -> Habit:
    h = Habit(name=name, icon=icon, description=description or None, frequency=frequency)
    db.add(h)
    db.commit()
    db.refresh(h)
    return h


def update_habit(db: Session, habit_id: int, **kwargs) -> Optional[Habit]:
    h = get_habit(db, habit_id)
    if not h:
        return None
    for k, v in kwargs.items():
        if v is not None and hasattr(h, k):
            setattr(h, k, v)
    h.updated_at = datetime.now()
    db.commit()
    db.refresh(h)
    return h


def delete_habit(db: Session, habit_id: int) -> bool:
    h = get_habit(db, habit_id)
    if not h:
        return False
    db.delete(h)
    db.commit()
    return True


def checkin(db: Session, habit_id: int, checkin_date: Optional[date] = None, note: str = "") -> Optional[CheckIn]:
    """Create a check-in record for a habit. Returns None if already checked in."""
    d = checkin_date or date.today()
    existing = db.query(CheckIn).filter(
        CheckIn.habit_id == habit_id,
        CheckIn.checkin_date == d,
    ).first()
    if existing:
        return existing
    c = CheckIn(habit_id=habit_id, checkin_date=d, note=note or None)
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


def uncheckin(db: Session, checkin_id: int) -> bool:
    c = db.query(CheckIn).filter(CheckIn.id == checkin_id).first()
    if not c:
        return False
    db.delete(c)
    db.commit()
    return True


def get_today_checkins(db: Session, d: Optional[date] = None) -> dict:
    """Get check-in status for today: {habit_id: checkin_obj or None}"""
    today = d or date.today()
    habits = list_habits(db)
    checkins = db.query(CheckIn).filter(CheckIn.checkin_date == today).all()
    checked_habit_ids = {c.habit_id: c for c in checkins}
    result = {}
    for h in habits:
        result[h.id] = {"habit": h, "checkin": checked_habit_ids.get(h.id)}
    return result


def get_streak(db: Session, habit_id: int, up_to: Optional[date] = None) -> int:
    """Calculate continuous check-in streak up to a given date."""
    d = up_to or date.today()
    streak = 0
    checkin_dates = set(
        row[0] for row in db.query(CheckIn.checkin_date)
        .filter(CheckIn.habit_id == habit_id, CheckIn.checkin_date <= d)
        .order_by(CheckIn.checkin_date.desc())
        .all()
    )
    from datetime import timedelta
    current = d
    while current in checkin_dates:
        streak += 1
        current -= timedelta(days=1)
    return streak


def get_checkin_history(db: Session, habit_id: int, days: int = 30) -> List[date]:
    """Get list of dates where check-in was done in recent N days."""
    from datetime import timedelta
    today = date.today()
    start = today - timedelta(days=days - 1)
    rows = db.query(CheckIn.checkin_date).filter(
        CheckIn.habit_id == habit_id,
        CheckIn.checkin_date >= start,
    ).all()
    return [r[0] for r in rows]
