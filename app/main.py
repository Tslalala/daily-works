import json
from datetime import date, datetime, timedelta

from fastapi import FastAPI, Depends, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from sqlalchemy.orm import Session

from app.auth import get_current_user, install_auth_handlers
from app.database import get_db, init_db
from app.i18n import tt
from app.models.activity_log import ActivityLog
from app.models.user import User
from app.routers import pages, auth, api_targets, api_habits, api_daily_log, api_ai, api_settings, api_work
from app.services.activity_service import get_logs_by_date_range, get_today_logs
from app.templates import templates

app = FastAPI(title="Daily Planner")
install_auth_handlers(app)

BASE_DIR = Path(__file__).resolve().parent.parent
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
# Wallpaper images for the appearance picker (same set as curiosity-web)
# Long-lived browser caching: wallpapers are large and rarely change per filename.
# (StaticFiles in this starlette version has no cache_control kwarg, so subclass it.)
class CachedWallpaperFiles(StaticFiles):
    async def get_response(self, path: str, scope):
        response = await super().get_response(path, scope)
        response.headers["Cache-Control"] = "public, max-age=31536000"
        return response


app.mount("/wallpapers", CachedWallpaperFiles(directory=str(BASE_DIR / "wallpaper_high"), check_dir=False), name="wallpapers")

# Register routers
app.include_router(auth.router)
app.include_router(pages.router)
app.include_router(api_targets.router)
app.include_router(api_habits.router)
app.include_router(api_work.router)
app.include_router(api_daily_log.router)
app.include_router(api_ai.router)
app.include_router(api_settings.router)

# Register template filters
pages.register_template_filters(templates)


@app.on_event("startup")
def on_startup():
    init_db()


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    today = date.today()
    week_ago = today - timedelta(days=6)
    logs = get_logs_by_date_range(db, user.id, week_ago, today)
    return templates.TemplateResponse(request, "dashboard.html", {
        "request": request,
        "now": datetime.now(),
        "today": today,
        "week_ago": week_ago,
        "month_ago": today - timedelta(days=29),
        "logs": logs,
    })


@app.get("/api/activity-logs", response_class=HTMLResponse)
async def activity_logs(
    request: Request,
    start: str = Query(default=""),
    end: str = Query(default=""),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    today = date.today()
    start_date = date.fromisoformat(start) if start else today
    end_date = date.fromisoformat(end) if end else today
    logs = get_logs_by_date_range(db, user.id, start_date, end_date)
    return templates.TemplateResponse(request, "dashboard/logs_fragment.html", {
        "request": request,
        "logs": logs,
        "now": datetime.now(),
    })


def _get_owned_activity_log(db: Session, user_id: int, log_id: int) -> ActivityLog:
    return db.query(ActivityLog).filter(
        ActivityLog.id == log_id,
        ActivityLog.user_id == user_id,
    ).first()


@app.get("/api/activity-logs/{log_id}/row", response_class=HTMLResponse)
async def activity_log_row(request: Request, log_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    log = _get_owned_activity_log(db, user.id, log_id)
    if not log:
        return HTMLResponse("", status_code=404)
    return templates.TemplateResponse(request, "dashboard/activity_row.html", {
        "request": request, "log": log, "now": datetime.now(),
    })


@app.get("/api/activity-logs/{log_id}/edit", response_class=HTMLResponse)
async def activity_log_edit_form(request: Request, log_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    log = _get_owned_activity_log(db, user.id, log_id)
    if not log:
        return HTMLResponse("", status_code=404)
    return templates.TemplateResponse(request, "dashboard/activity_row_edit.html", {
        "request": request, "log": log, "now": datetime.now(),
    })


@app.post("/api/activity-logs/{log_id}/edit", response_class=HTMLResponse)
async def activity_log_save(request: Request, log_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    log = _get_owned_activity_log(db, user.id, log_id)
    if not log:
        return HTMLResponse("", status_code=404)
    form = await request.form()
    description = (form.get("description") or "").strip()
    if description:
        log.description = description[:500]
        db.commit()
        db.refresh(log)
    return templates.TemplateResponse(request, "dashboard/activity_row.html", {
        "request": request, "log": log, "now": datetime.now(),
    }, headers={"HX-Trigger": json.dumps({"show-toast": {"message": tt(request, "toast.act_updated"), "type": "success"}})})


@app.delete("/api/activity-logs/{log_id}", response_class=HTMLResponse)
async def activity_log_delete(request: Request, log_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    log = _get_owned_activity_log(db, user.id, log_id)
    if not log:
        return HTMLResponse("", status_code=404)
    db.delete(log)
    db.commit()
    return HTMLResponse("", headers={"HX-Trigger": json.dumps({"show-toast": {"message": tt(request, "toast.act_deleted"), "type": "success"}})})
