from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.habit_schema import HabitCreate, HabitUpdate
from app.services.activity_service import log_action, remove_checkin_log
from app.services.habit_service import (
    checkin, create_habit, delete_habit, get_checkin_history, get_habit, get_streak, uncheckin, update_habit,
)
from app.templates import templates
from app.utils.date_utils import build_calendar

router = APIRouter(prefix="/api")


def _build_history_response(request: Request, habit_id: int, focus_date: date, db: Session) -> HTMLResponse:
    """Build the history calendar fragment response for a habit."""
    from app.models.habit import CheckIn
    h = get_habit(db, habit_id)
    if not h:
        return HTMLResponse("习惯不存在", status_code=404)
    dates = get_checkin_history(db, habit_id, days=30)
    today = date.today()
    start = today - timedelta(days=29)
    checkins = db.query(CheckIn).filter(
        CheckIn.habit_id == habit_id,
        CheckIn.checkin_date >= start,
    ).all()
    notes_map = {}
    checkins_with_notes = []
    for c in checkins:
        if c.note:
            notes_map[c.checkin_date] = c.note
            checkins_with_notes.append(c)

    calendar_days, checked_count = build_calendar(dates, notes_map=notes_map)
    focus_checked = focus_date in dates
    focus_note = notes_map.get(focus_date, "")

    return templates.TemplateResponse("habits/history_calendar.html", {
        "request": request, "habit": h, "checkin_dates": dates,
        "calendar_days": calendar_days, "checked_count": checked_count,
        "checkins_with_notes": checkins_with_notes,
        "focus_date": focus_date,
        "focus_checked": focus_checked,
        "focus_note": focus_note,
    })


@router.post("/habits")
async def api_create_habit(request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    h = create_habit(
        db,
        name=form.get("name"),
        icon=form.get("icon", "📌"),
        description=form.get("description") or None,
        frequency=form.get("frequency", "daily"),
    )
    log_action(db, "create_habit", f"创建了习惯「{h.name}」{h.icon}", target_type="habit", target_id=h.id)
    return RedirectResponse(url="/habits?created=1", status_code=303)


@router.put("/habits/{habit_id}", response_class=HTMLResponse)
async def api_update_habit(request: Request, habit_id: int, db: Session = Depends(get_db)):
    form = await request.form()
    h = update_habit(
        db, habit_id,
        name=form.get("name"),
        icon=form.get("icon"),
        description=form.get("description") or None,
        frequency=form.get("frequency"),
    )
    if not h:
        return HTMLResponse("Habit not found", status_code=404)
    return templates.TemplateResponse("habits/card.html", {
        "request": request, "habit": h, "checkin": None, "streak": get_streak(db, habit_id),
    }, headers={"HX-Trigger": '{"show-toast": {"message": "Habit updated!", "type": "success"}}'})


@router.delete("/habits/{habit_id}")
async def api_delete_habit(habit_id: int, db: Session = Depends(get_db)):
    ok = delete_habit(db, habit_id)
    if not ok:
        return HTMLResponse("Habit not found", status_code=404)
    return HTMLResponse("", headers={"HX-Trigger": '{"show-toast": {"message": "Habit deleted", "type": "success"}}'})


@router.post("/checkins/{habit_id}", response_class=HTMLResponse)
async def api_checkin(request: Request, habit_id: int, db: Session = Depends(get_db)):
    form = await request.form()
    note = form.get("note", "").strip()
    c = checkin(db, habit_id, note=note)
    h = get_habit(db, habit_id)
    if not h:
        return HTMLResponse("Habit not found", status_code=404)
    streak = get_streak(db, habit_id)
    if c and c.checkin_date == date.today():
        log_action(db, "checkin_habit", f"完成了习惯「{h.name}」{h.icon}打卡", target_type="habit", target_id=habit_id)
    return templates.TemplateResponse("habits/card.html", {
        "request": request, "habit": h, "checkin": c if c and c.checkin_date == date.today() else None, "streak": streak,
    }, headers={"HX-Trigger": '{"show-toast": {"message": "Check-in done!", "type": "success"}}'})


@router.delete("/checkins/{checkin_id}", response_class=HTMLResponse)
async def api_uncheckin(request: Request, checkin_id: int, db: Session = Depends(get_db)):
    from app.models.habit import CheckIn
    chk = db.query(CheckIn).filter(CheckIn.id == checkin_id).first()
    if not chk:
        return HTMLResponse("Check-in not found", status_code=404)
    habit_id = chk.habit_id
    uncheckin(db, checkin_id)
    remove_checkin_log(db, habit_id)
    h = get_habit(db, habit_id)
    streak = get_streak(db, habit_id)
    return templates.TemplateResponse("habits/card.html", {
        "request": request, "habit": h, "checkin": None, "streak": streak,
    }, headers={"HX-Trigger": '{"show-toast": {"message": "Check-in undone", "type": "success"}}'})


@router.get("/habits/{habit_id}/history", response_class=HTMLResponse)
async def api_habit_history(request: Request, habit_id: int, db: Session = Depends(get_db)):
    focus = request.query_params.get("focus", "")
    focus_date = None
    if focus:
        try:
            focus_date = date.fromisoformat(focus)
        except ValueError:
            pass
    if not focus_date:
        focus_date = date.today()
    return _build_history_response(request, habit_id, focus_date, db)


@router.post("/habits/{habit_id}/toggle-date", response_class=HTMLResponse)
async def api_toggle_date(request: Request, habit_id: int, db: Session = Depends(get_db)):
    from app.models.habit import CheckIn
    form = await request.form()
    d = date.fromisoformat(form.get("date"))

    existing = db.query(CheckIn).filter(
        CheckIn.habit_id == habit_id,
        CheckIn.checkin_date == d,
    ).first()

    if existing:
        db.delete(existing)
        db.commit()
    else:
        db.add(CheckIn(habit_id=habit_id, checkin_date=d, note=None))
        db.commit()

    return _build_history_response(request, habit_id, d, db)


@router.post("/habits/{habit_id}/save-note", response_class=HTMLResponse)
async def api_save_note(request: Request, habit_id: int, db: Session = Depends(get_db)):
    from app.models.habit import CheckIn
    form = await request.form()
    d = date.fromisoformat(form.get("date"))
    note = form.get("note", "").strip()

    existing = db.query(CheckIn).filter(
        CheckIn.habit_id == habit_id,
        CheckIn.checkin_date == d,
    ).first()

    if existing:
        existing.note = note or None
        db.commit()
    elif note:
        db.add(CheckIn(habit_id=habit_id, checkin_date=d, note=note or None))
        db.commit()

    return _build_history_response(request, habit_id, d, db)
