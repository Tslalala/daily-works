"""Work clock-in/out API: the flexible work-day card on the habits page."""
import json
from datetime import date, datetime

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.i18n import get_lang, tt
from app.models.user import User
from app.services.activity_service import log_action
from app.services.work_service import (
    clock_in, clock_out, get_by_date, get_today, history_items,
    overtime_minutes, save_times, worked_minutes,
)
from app.utils.date_utils import format_duration
from app.templates import templates

router = APIRouter(prefix="/api/work")


def _card_context(request: Request, db: Session, user: User) -> dict:
    rec = get_today(db, user.id)
    items = history_items(db, user.id)
    today_item = next((i for i in items if i["rec"].work_date == date.today()), None)
    return {
        "request": request,
        "work_rec": rec,
        "work_today": today_item,
        "work_hist": items,
        "work_total_ot": sum(i["overtime"] or 0 for i in items),
        "now": datetime.now(),
    }


@router.get("/card", response_class=HTMLResponse)
async def work_card(request: Request, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return templates.TemplateResponse(request, "habits/work_clockin_card.html", _card_context(request, db, user))


@router.post("/clock-in", response_class=HTMLResponse)
async def work_clock_in(request: Request, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rec = clock_in(db, user.id)
    log_action(db, user.id, "work_clockin", f"上班打卡 {rec.clock_in.strftime('%H:%M')}")
    return templates.TemplateResponse(request, "habits/work_clockin_card.html", _card_context(request, db, user),
                                      headers={"HX-Trigger": json.dumps({"show-toast": {
                                          "message": tt(request, "toast.work_in", time=rec.clock_in.strftime("%H:%M")),
                                          "type": "success"}})})


@router.post("/clock-out", response_class=HTMLResponse)
async def work_clock_out(request: Request, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rec = clock_out(db, user.id)
    if not rec:
        return HTMLResponse(tt(request, "work.no_record_today"), status_code=400)
    ot = overtime_minutes(rec)
    ot_text = format_duration(ot, get_lang(request))
    log_action(db, user.id, "work_clockout",
               f"下班打卡 {rec.clock_out.strftime('%H:%M')}（加班 {ot_text}）")
    msg = tt(request, "toast.work_out", time=rec.clock_out.strftime("%H:%M"), overtime=ot_text) if ot \
        else tt(request, "toast.work_out_no_ot", time=rec.clock_out.strftime("%H:%M"))
    return templates.TemplateResponse(request, "habits/work_clockin_card.html", _card_context(request, db, user),
                                      headers={"HX-Trigger": json.dumps({"show-toast": {"message": msg, "type": "success"}})})


@router.post("/edit", response_class=HTMLResponse)
async def work_edit(request: Request, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    form = await request.form()
    try:
        work_date = date.fromisoformat(form.get("work_date") or date.today().isoformat())
    except ValueError:
        return HTMLResponse("Invalid date", status_code=400)
    ci = co = None
    ci_raw = (form.get("clock_in") or "").strip()
    co_raw = (form.get("clock_out") or "").strip()
    try:
        if ci_raw:
            ci = datetime.strptime(ci_raw, "%H:%M").time()
        if co_raw:
            co = datetime.strptime(co_raw, "%H:%M").time()
    except ValueError:
        return HTMLResponse("Invalid time", status_code=400)
    if work_date > date.today():
        return HTMLResponse("Invalid date", status_code=400)
    save_times(db, user.id, work_date, ci, co)
    return templates.TemplateResponse(request, "habits/work_clockin_card.html", _card_context(request, db, user),
                                      headers={"HX-Trigger": json.dumps({"show-toast": {
                                          "message": tt(request, "toast.work_updated"), "type": "success"}})})


def _item_for(db: Session, user_id: int, work_date: date):
    rec = get_by_date(db, user_id, work_date)
    if rec is None:
        return None
    return {"rec": rec, "worked": worked_minutes(rec), "overtime": overtime_minutes(rec)}


@router.get("/history/add/edit", response_class=HTMLResponse)
async def work_history_add_form(request: Request, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return templates.TemplateResponse(request, "habits/work_history_add_edit.html", {"request": request})


@router.get("/history/add/row", response_class=HTMLResponse)
async def work_history_add_button(request: Request, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return templates.TemplateResponse(request, "habits/work_history_add.html", {"request": request})


@router.post("/history/add", response_class=HTMLResponse)
async def work_history_add_save(request: Request, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    form = await request.form()
    try:
        work_date = date.fromisoformat(form.get("work_date") or "")
    except ValueError:
        return HTMLResponse("Invalid date", status_code=400)
    if work_date > date.today():
        return HTMLResponse("Invalid date", status_code=400)
    ci = co = None
    try:
        ci_raw = (form.get("clock_in") or "").strip()
        co_raw = (form.get("clock_out") or "").strip()
        if ci_raw:
            ci = datetime.strptime(ci_raw, "%H:%M").time()
        if co_raw:
            co = datetime.strptime(co_raw, "%H:%M").time()
    except ValueError:
        return HTMLResponse("Invalid time", status_code=400)
    if ci is None:
        return HTMLResponse("Clock-in required", status_code=400)
    rec = save_times(db, user.id, work_date, ci, co)
    if rec is None:  # clock_in was normalized away (e.g. 00:00 from a cleared input)
        return HTMLResponse("Clock-in required", status_code=400)
    return templates.TemplateResponse(request, "habits/work_clockin_card.html", _card_context(request, db, user),
                                      headers={"HX-Trigger": json.dumps({"show-toast": {
                                          "message": tt(request, "toast.work_added"), "type": "success"}})})


@router.get("/history/{work_date}/row", response_class=HTMLResponse)
async def work_history_row(request: Request, work_date: date, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    item = _item_for(db, user.id, work_date)
    if not item:
        return HTMLResponse("Not found", status_code=404)
    return templates.TemplateResponse(request, "habits/work_history_row.html", {"request": request, "item": item})


@router.get("/history/{work_date}/edit", response_class=HTMLResponse)
async def work_history_row_edit(request: Request, work_date: date, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rec = get_by_date(db, user.id, work_date)
    if not rec:
        return HTMLResponse("Not found", status_code=404)
    return templates.TemplateResponse(request, "habits/work_history_row_edit.html", {"request": request, "rec": rec})


@router.post("/history/{work_date}/delete", response_class=HTMLResponse)
async def work_history_delete(request: Request, work_date: date, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rec = get_by_date(db, user.id, work_date)
    if not rec:
        return HTMLResponse("Not found", status_code=404)
    was_today = work_date == date.today()
    db.delete(rec)
    db.commit()
    headers = {"HX-Trigger": json.dumps({"show-toast": {
        "message": tt(request, "toast.work_deleted"), "type": "success"}})}
    if was_today:
        return templates.TemplateResponse(request, "habits/work_clockin_card.html",
                                          _card_context(request, db, user), headers=headers)
    return HTMLResponse("", headers=headers)


@router.post("/history/{work_date}/edit", response_class=HTMLResponse)
async def work_history_row_save(request: Request, work_date: date, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    form = await request.form()
    ci = co = None
    try:
        ci_raw = (form.get("clock_in") or "").strip()
        co_raw = (form.get("clock_out") or "").strip()
        if ci_raw:
            ci = datetime.strptime(ci_raw, "%H:%M").time()
        if co_raw:
            co = datetime.strptime(co_raw, "%H:%M").time()
    except ValueError:
        return HTMLResponse("Invalid time", status_code=400)
    if work_date > date.today():
        return HTMLResponse("Invalid date", status_code=400)
    save_times(db, user.id, work_date, ci, co)
    headers = {"HX-Trigger": json.dumps({"show-toast": {
        "message": tt(request, "toast.work_updated"), "type": "success"}})}
    item = _item_for(db, user.id, work_date)
    if item is None:  # both times cleared -> the day is un-counted, drop the row
        return HTMLResponse("", headers=headers)
    return templates.TemplateResponse(request, "habits/work_history_row.html",
                                      {"request": request, "item": item}, headers=headers)
