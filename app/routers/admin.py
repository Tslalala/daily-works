"""Admin backend: user management and cross-user data browsing (is_admin only)."""
from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.auth import require_admin
from app.database import get_db
from app.i18n import tt
from app.models.activity_log import ActivityLog
from app.models.daily_log import DailyLog
from app.models.habit import CheckIn, Habit
from app.models.session import AppSession
from app.models.target import Target, TargetContribution, TargetMilestone
from app.models.user import User
from app.models.work_clockin import WorkClockin
from app.services.activity_service import log_action
from app.templates import templates

router = APIRouter(prefix="/admin")


def _user_counts(db: Session, user_id: int) -> dict:
    return {
        "targets": db.query(Target).filter(Target.user_id == user_id).count(),
        "habits": db.query(Habit).filter(Habit.user_id == user_id).count(),
        "logs": db.query(DailyLog).filter(DailyLog.user_id == user_id).count(),
    }


def _render_list(request: Request, db: Session, error: str = ""):
    users = db.query(User).order_by(User.id).all()
    rows = [{"user": u, "counts": _user_counts(db, u.id)} for u in users]
    return templates.TemplateResponse(request, "admin/list.html", {
        "request": request, "users": rows, "error": error,
    })


def _delete_user_data(db: Session, user_id: int) -> None:
    for t in db.query(Target).filter(Target.user_id == user_id).all():
        db.query(TargetMilestone).filter(TargetMilestone.target_id == t.id).delete()
        db.query(TargetContribution).filter(TargetContribution.target_id == t.id).delete()
        db.delete(t)
    for h in db.query(Habit).filter(Habit.user_id == user_id).all():
        db.query(CheckIn).filter(CheckIn.habit_id == h.id).delete()
        db.delete(h)
    db.query(DailyLog).filter(DailyLog.user_id == user_id).delete()
    db.query(WorkClockin).filter(WorkClockin.user_id == user_id).delete()
    db.query(AppSession).filter(AppSession.user_id == user_id).delete()
    db.query(ActivityLog).filter(ActivityLog.user_id == user_id).delete()


@router.get("")
def admin_index(request: Request, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    return _render_list(request, db)


@router.get("/users/{user_id}")
def admin_user_detail(request: Request, user_id: int, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    u = db.query(User).filter(User.id == user_id).first()
    if u is None:
        return RedirectResponse("/admin", status_code=303)
    targets = db.query(Target).filter(Target.user_id == user_id).order_by(Target.id).all()
    habits = db.query(Habit).filter(Habit.user_id == user_id).order_by(Habit.id).all()
    logs = db.query(DailyLog).filter(DailyLog.user_id == user_id).order_by(DailyLog.log_date.desc()).all()
    return templates.TemplateResponse(request, "admin/user_detail.html", {
        "request": request, "target_user": u, "targets": targets, "habits": habits, "logs": logs,
    })


@router.post("/users/{user_id}/admin")
def admin_toggle_admin(request: Request, user_id: int, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    u = db.query(User).filter(User.id == user_id).first()
    if u is None:
        return RedirectResponse("/admin", status_code=303)
    if u.is_admin:
        n_admins = db.query(User).filter(User.is_admin.is_(True)).count()
        if n_admins <= 1:
            return _render_list(request, db, error=tt(request, "admin.last_admin"))
        u.is_admin = False
        log_action(db, admin.id, "admin_admin_unset", tt(request, "admin.act_admin_unset").format(name=u.username))
    else:
        u.is_admin = True
        log_action(db, admin.id, "admin_admin_set", tt(request, "admin.act_admin_set").format(name=u.username))
    db.commit()
    return RedirectResponse("/admin", status_code=303)


@router.post("/users/{user_id}/delete")
def admin_delete_user(request: Request, user_id: int, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    u = db.query(User).filter(User.id == user_id).first()
    if u is None:
        return RedirectResponse("/admin", status_code=303)
    if u.id == admin.id:
        return _render_list(request, db, error=tt(request, "admin.no_self_delete"))
    _delete_user_data(db, u.id)
    name = u.username
    db.delete(u)
    db.commit()
    log_action(db, admin.id, "admin_delete_user", tt(request, "admin.act_delete_user").format(name=name))
    return RedirectResponse("/admin", status_code=303)


@router.get("/activity")
def admin_activity(request: Request, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    logs = db.query(ActivityLog).order_by(ActivityLog.id.desc()).limit(200).all()
    usernames = {u.id: u.username for u in db.query(User).all()}
    return templates.TemplateResponse(request, "admin/activity.html", {
        "request": request, "logs": logs, "usernames": usernames,
    })
