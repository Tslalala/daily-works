from datetime import date, datetime, timedelta

from fastapi import FastAPI, Depends, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from sqlalchemy.orm import Session

from app.database import get_db, init_db
from app.routers import pages, api_targets, api_habits, api_daily_log, api_ai
from app.services.activity_service import get_logs_by_date_range, get_today_logs
from app.templates import templates

app = FastAPI(title="Daily Planner")

BASE_DIR = Path(__file__).resolve().parent.parent
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

# Register routers
app.include_router(pages.router)
app.include_router(api_targets.router)
app.include_router(api_habits.router)
app.include_router(api_daily_log.router)
app.include_router(api_ai.router)

# Register template filters
pages.register_template_filters(templates)


@app.on_event("startup")
def on_startup():
    init_db()


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, db: Session = Depends(get_db)):
    today = date.today()
    week_ago = today - timedelta(days=6)
    logs = get_logs_by_date_range(db, week_ago, today)
    return templates.TemplateResponse("dashboard.html", {
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
):
    today = date.today()
    start_date = date.fromisoformat(start) if start else today
    end_date = date.fromisoformat(end) if end else today
    logs = get_logs_by_date_range(db, start_date, end_date)
    return templates.TemplateResponse("dashboard/logs_fragment.html", {
        "request": request,
        "logs": logs,
        "now": datetime.now(),
    })
