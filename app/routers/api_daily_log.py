from datetime import date

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.daily_log_service import save_log

router = APIRouter(prefix="/api")


@router.post("/daily-log/{log_date}", response_class=HTMLResponse)
async def api_save_daily_log(request: Request, log_date: date, db: Session = Depends(get_db)):
    form = await request.form()
    content = form.get("content", "")
    mood = form.get("mood", "")
    save_log(db, log_date, content=content, mood=mood)
    return HTMLResponse(
        "",
        headers={"HX-Trigger": '{"show-toast": {"message": "Log saved!", "type": "success"}}'},
    )
