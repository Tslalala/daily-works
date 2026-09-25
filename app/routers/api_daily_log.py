import json
from datetime import date

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.i18n import tt
from app.models.user import User
from app.services.daily_log_service import save_log

router = APIRouter(prefix="/api")


@router.post("/daily-log/{log_date}", response_class=HTMLResponse)
async def api_save_daily_log(request: Request, log_date: date, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    form = await request.form()
    content = form.get("content", "")
    mood = form.get("mood", "")
    save_log(db, user.id, log_date, content=content, mood=mood)
    return HTMLResponse(
        "",
        headers={"HX-Trigger": json.dumps({"show-toast": {"message": tt(request, "toast.log_saved"), "type": "success"}})},
    )
