from datetime import date, datetime
from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.target import Target, TargetContribution, TargetMilestone
from app.schemas.target_schema import TargetCreate, TargetUpdate


def list_targets(db: Session, target_type: Optional[str] = None, status: Optional[str] = None) -> List[Target]:
    q = db.query(Target)
    if target_type:
        q = q.filter(Target.target_type == target_type)
    if status and status != "all":
        q = q.filter(Target.status == status)
    elif not status:
        q = q.filter(Target.status == "active")
    return q.order_by(Target.sort_order.asc(), Target.priority.asc(), Target.deadline.asc().nullslast()).all()


def get_target(db: Session, target_id: int) -> Optional[Target]:
    return db.query(Target).filter(Target.id == target_id).first()


def create_target(db: Session, data: TargetCreate) -> Target:
    t = Target(**data.model_dump())
    db.add(t)
    db.commit()
    db.refresh(t)
    return t


def update_target(db: Session, target_id: int, data: TargetUpdate) -> Optional[Target]:
    t = get_target(db, target_id)
    if not t:
        return None
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(t, k, v)
    t.updated_at = datetime.now()
    db.commit()
    db.refresh(t)
    return t


def delete_target(db: Session, target_id: int) -> bool:
    t = get_target(db, target_id)
    if not t:
        return False
    db.delete(t)
    db.commit()
    return True


def complete_target(db: Session, target_id: int) -> Optional[Target]:
    t = get_target(db, target_id)
    if not t:
        return None
    t.status = "completed"
    t.progress = 100
    t.updated_at = datetime.now()
    db.commit()
    db.refresh(t)
    return t


def update_progress(db: Session, target_id: int, progress: int) -> Optional[Target]:
    t = get_target(db, target_id)
    if not t:
        return None
    t.progress = max(0, min(100, progress))
    if t.progress == 100:
        t.status = "completed"
    elif t.status == "completed" and t.progress < 100:
        t.status = "active"
    t.updated_at = datetime.now()
    db.commit()
    db.refresh(t)
    return t


def toggle_milestone(db: Session, milestone_id: int) -> Optional[TargetMilestone]:
    m = db.query(TargetMilestone).filter(TargetMilestone.id == milestone_id).first()
    if not m:
        return None
    m.completed = not m.completed
    m.completed_at = datetime.now() if m.completed else None
    db.flush()

    # Recalculate target progress from milestone completion ratio
    total = db.query(TargetMilestone).filter(
        TargetMilestone.target_id == m.target_id
    ).count()
    completed = db.query(TargetMilestone).filter(
        TargetMilestone.target_id == m.target_id,
        TargetMilestone.completed == True
    ).count()
    if total > 0:
        t = db.query(Target).filter(Target.id == m.target_id).first()
        if t:
            t.progress = int(completed / total * 100)
            if t.progress == 100:
                t.status = "completed"
            elif t.status == "completed" and t.progress < 100:
                t.status = "active"
            t.updated_at = datetime.now()

    db.commit()
    db.refresh(m)
    return m


def get_contribution(db: Session, target_id: int, log_date: date) -> Optional[TargetContribution]:
    return db.query(TargetContribution).filter(
        TargetContribution.target_id == target_id,
        TargetContribution.log_date == log_date,
    ).first()


def get_today_contribution(db: Session, target_id: int) -> Optional[TargetContribution]:
    return get_contribution(db, target_id, date.today())


def save_contribution(db: Session, target_id: int, content: str, log_date: date = None) -> TargetContribution:
    if log_date is None:
        log_date = date.today()
    c = db.query(TargetContribution).filter(
        TargetContribution.target_id == target_id,
        TargetContribution.log_date == log_date,
    ).first()
    if c:
        c.content = content
        c.updated_at = datetime.now()
    else:
        c = TargetContribution(target_id=target_id, log_date=log_date, content=content)
        db.add(c)
    db.commit()
    db.refresh(c)
    return c


def delete_today_contribution(db: Session, target_id: int) -> bool:
    c = get_today_contribution(db, target_id)
    if not c:
        return False
    db.delete(c)
    db.commit()
    return True


def list_recent_contributions(db: Session, target_id: int, days: int = 14) -> list[TargetContribution]:
    from datetime import timedelta
    since = date.today() - timedelta(days=days - 1)
    return db.query(TargetContribution).filter(
        TargetContribution.target_id == target_id,
        TargetContribution.log_date >= since,
    ).order_by(TargetContribution.log_date.desc()).all()


def reorder_targets(db: Session, ordered_ids: list[int]) -> None:
    for i, tid in enumerate(ordered_ids):
        db.query(Target).filter(Target.id == tid).update({"sort_order": i})
    db.commit()


def create_milestone(db: Session, target_id: int, title: str, suggested_date=None) -> TargetMilestone:
    from sqlalchemy import func
    max_order = db.query(func.max(TargetMilestone.sort_order)).filter(
        TargetMilestone.target_id == target_id
    ).scalar() or 0
    m = TargetMilestone(
        target_id=target_id, title=title,
        suggested_date=suggested_date, sort_order=max_order + 1,
    )
    db.add(m)
    db.commit()
    db.refresh(m)
    return m


def update_milestone(db: Session, milestone_id: int, title: str, suggested_date=None) -> Optional[TargetMilestone]:
    m = db.query(TargetMilestone).filter(TargetMilestone.id == milestone_id).first()
    if not m:
        return None
    m.title = title
    m.suggested_date = suggested_date
    db.commit()
    db.refresh(m)
    return m


def delete_milestone(db: Session, milestone_id: int) -> bool:
    m = db.query(TargetMilestone).filter(TargetMilestone.id == milestone_id).first()
    if not m:
        return False
    db.delete(m)
    db.commit()
    return True


def recalculate_milestone_progress(db: Session, target_id: int) -> None:
    total = db.query(TargetMilestone).filter(TargetMilestone.target_id == target_id).count()
    completed = db.query(TargetMilestone).filter(
        TargetMilestone.target_id == target_id, TargetMilestone.completed == True
    ).count()
    t = db.query(Target).filter(Target.id == target_id).first()
    if not t:
        return
    if total > 0:
        t.progress = int(completed / total * 100)
    else:
        t.progress = 0
    if t.progress == 100:
        t.status = "completed"
    elif t.status == "completed" and t.progress < 100:
        t.status = "active"
    t.updated_at = datetime.now()
    db.commit()
