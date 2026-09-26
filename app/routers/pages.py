from datetime import date, datetime

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from jinja2 import pass_context

from app.auth import get_current_user
from app.database import get_db
from app.i18n import get_lang, tt
from app.models.user import User
from app.services.target_service import get_target, get_today_contribution, list_recent_contributions, list_targets
from app.services.habit_service import get_checkin_history, get_habit, get_streak, get_today_checkins, list_habits
from app.services.daily_log_service import get_log, list_logs, save_log
from app.services import work_service
from app.templates import templates
from app.i18n import translate
from app.utils.date_utils import build_calendar, days_remaining, deadline_class, format_duration, format_dt, priority_color, priority_label, type_label, weekday_long
from app.utils.moon import moon_shadow_path

router = APIRouter()


def register_template_filters(templates_obj):
    # Filters that need the current language read it from the Jinja context.
    @pass_context
    def f_days_remaining(context, dt):
        return days_remaining(dt, context.get("lang", "zh"))

    @pass_context
    def f_priority_label(context, p):
        return priority_label(p, context.get("lang", "zh"))

    @pass_context
    def f_priority_label_full(context, p):
        key = {1: "prio.high", 2: "prio.mid", 3: "prio.low"}.get(p, "prio.mid")
        return translate(context.get("lang", "zh"), key)

    @pass_context
    def f_type_label(context, t):
        return type_label(t, context.get("lang", "zh"))

    @pass_context
    def f_weekday_long(context, d):
        return weekday_long(d, context.get("lang", "zh"))

    @pass_context
    def f_work_duration(context, minutes):
        return format_duration(minutes, context.get("lang", "zh"))

    @pass_context
    def f_suggested_out(context, clock_in):
        if clock_in is None:
            return ""
        t, next_day = work_service.suggested_out(clock_in)
        text = t.strftime("%H:%M")
        if next_day:
            text += " " + translate(context.get("lang", "zh"), "work.next_day")
        return text

    templates_obj.env.filters["days_remaining"] = f_days_remaining
    templates_obj.env.filters["deadline_class"] = deadline_class
    templates_obj.env.filters["format_dt"] = format_dt
    templates_obj.env.filters["priority_color"] = priority_color
    templates_obj.env.filters["priority_label"] = f_priority_label
    templates_obj.env.filters["priority_label_full"] = f_priority_label_full
    templates_obj.env.filters["type_label"] = f_type_label
    templates_obj.env.filters["weekday_long"] = f_weekday_long
    templates_obj.env.filters["work_duration"] = f_work_duration
    templates_obj.env.filters["suggested_out"] = f_suggested_out
    templates_obj.env.filters["moon_shadow"] = moon_shadow_path


@router.get("/targets", response_class=HTMLResponse)
async def target_list(request: Request, target_type: str = "", status: str = "", db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    type_filter = target_type if target_type else None
    status_filter = status if status else None
    targets = list_targets(db, user.id, target_type=type_filter, status=status_filter)
    return templates.TemplateResponse(request, "targets/list.html", {
        "request": request,
        "targets": targets,
        "current_type": target_type,
        "current_status": status,
        "now": datetime.now(),
    })


@router.get("/targets/new", response_class=HTMLResponse)
async def target_new_form(request: Request, user: User = Depends(get_current_user)):
    return templates.TemplateResponse(request, "targets/form.html", {
        "request": request,
        "target": None,
        "now": datetime.now(),
    })


@router.get("/targets/{target_id}", response_class=HTMLResponse)
async def target_detail(request: Request, target_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    t = get_target(db, user.id, target_id)
    if not t:
        return templates.TemplateResponse(request, "components/empty_state.html", {
            "request": request, "message": tt(request, "targets.not_found"),
        }, status_code=404)
    contribution = get_today_contribution(db, target_id)
    recent_contributions = list_recent_contributions(db, target_id)
    return templates.TemplateResponse(request, "targets/detail.html", {
        "request": request,
        "target": t,
        "contribution": contribution,
        "recent_contributions": recent_contributions,
        "now": datetime.now(),
    })


@router.get("/targets/{target_id}/edit", response_class=HTMLResponse)
async def target_edit_form(request: Request, target_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    t = get_target(db, user.id, target_id)
    if not t:
        return templates.TemplateResponse(request, "components/empty_state.html", {
            "request": request, "message": tt(request, "targets.not_found"),
        }, status_code=404)
    return templates.TemplateResponse(request, "targets/form.html", {
        "request": request,
        "target": t,
        "now": datetime.now(),
    })


# --- Habit pages ---

@router.get("/habits", response_class=HTMLResponse)
async def habit_list(request: Request, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    today_checkins = get_today_checkins(db, user.id)
    habits_with_streak = []
    for hid, data in today_checkins.items():
        habits_with_streak.append({
            "habit": data["habit"],
            "checkin": data["checkin"],
            "streak": get_streak(db, hid),
        })
    work_rec = work_service.get_today(db, user.id)
    work_hist = work_service.history_items(db, user.id)
    work_today = next((i for i in work_hist if i["rec"].work_date == date.today()), None)
    return templates.TemplateResponse(request, "habits/list.html", {
        "request": request,
        "habits_data": habits_with_streak,
        "work_rec": work_rec,
        "work_today": work_today,
        "work_hist": work_hist,
        "work_total_ot": sum(i["overtime"] or 0 for i in work_hist),
        "now": datetime.now(),
    })


@router.get("/habits/new", response_class=HTMLResponse)
async def habit_new_form(request: Request, user: User = Depends(get_current_user)):
    return templates.TemplateResponse(request, "habits/form.html", {
        "request": request,
        "habit": None,
        "now": datetime.now(),
    })


@router.get("/habits/{habit_id}", response_class=HTMLResponse)
async def habit_detail(request: Request, habit_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    h = get_habit(db, user.id, habit_id)
    if not h:
        return templates.TemplateResponse(request, "components/empty_state.html", {
            "request": request, "message": tt(request, "habits.not_found"),
        }, status_code=404)
    streak = get_streak(db, habit_id)
    checkin_dates = get_checkin_history(db, habit_id)
    # Build notes map: date -> note
    from datetime import timedelta
    from app.models.habit import CheckIn
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
    calendar_days, checked_count = build_calendar(checkin_dates, notes_map=notes_map, lang=get_lang(request))
    # Default focus to today
    focus_date = today
    focus_checked = focus_date in checkin_dates
    focus_note = notes_map.get(focus_date, "")
    return templates.TemplateResponse(request, "habits/detail.html", {
        "request": request,
        "habit": h,
        "streak": streak,
        "checkin_dates": checkin_dates,
        "calendar_days": calendar_days,
        "checked_count": checked_count,
        "checkins_with_notes": checkins_with_notes,
        "focus_date": focus_date,
        "focus_checked": focus_checked,
        "focus_note": focus_note,
        "now": datetime.now(),
    })


@router.get("/habits/{habit_id}/edit", response_class=HTMLResponse)
async def habit_edit_form(request: Request, habit_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    h = get_habit(db, user.id, habit_id)
    if not h:
        return templates.TemplateResponse(request, "components/empty_state.html", {
            "request": request, "message": tt(request, "habits.not_found"),
        }, status_code=404)
    return templates.TemplateResponse(request, "habits/form.html", {
        "request": request,
        "habit": h,
        "now": datetime.now(),
    })


# --- Daily Log pages ---

@router.get("/daily-log", response_class=HTMLResponse)
async def daily_log_list(request: Request, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    logs = list_logs(db, user.id)
    return templates.TemplateResponse(request, "daily_log/list.html", {
        "request": request,
        "logs": logs,
        "now": datetime.now(),
    })


@router.get("/daily-log/today", response_class=HTMLResponse)
async def daily_log_today(request: Request, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    today = date.today()
    log = get_log(db, user.id, today)
    return templates.TemplateResponse(request, "daily_log/entry.html", {
        "request": request,
        "log": log,
        "log_date": today,
        "now": datetime.now(),
    })


@router.get("/daily-log/{log_date}", response_class=HTMLResponse)
async def daily_log_by_date(request: Request, log_date: date, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    log = get_log(db, user.id, log_date)
    return templates.TemplateResponse(request, "daily_log/entry.html", {
        "request": request,
        "log": log,
        "log_date": log_date,
        "now": datetime.now(),
    })
