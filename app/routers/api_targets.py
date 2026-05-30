"""Target API endpoints."""
import json

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.target_schema import TargetCreate, TargetUpdate
from app.services.activity_service import log_action, remove_milestone_completion
from app.services.target_service import (
    complete_target, create_target, create_milestone, delete_milestone, delete_target,
    delete_today_contribution, get_contribution, get_target, get_today_contribution,
    list_recent_contributions, list_targets, recalculate_milestone_progress, reorder_targets,
    save_contribution, toggle_milestone, update_milestone, update_progress, update_target,
)
from app.templates import templates
from datetime import datetime
from app.models.target import TargetMilestone

router = APIRouter(prefix="/api")

TYPE_LABEL = {"deadline": "有期限", "short_term": "短期", "long_term": "长期"}


@router.post("/targets")
async def api_create_target(request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    data = TargetCreate(
        title=form.get("title"),
        description=form.get("description") or None,
        target_type=form.get("target_type", "short_term"),
        deadline=form.get("deadline") or None,
        priority=int(form.get("priority", 2)),
    )
    t = create_target(db, data)
    type_label = TYPE_LABEL.get(t.target_type, "短期")
    log_action(db, "create_target", f"创建了{type_label}目标「{t.title}」", target_type=t.target_type, target_id=t.id)
    return RedirectResponse(url=f"/targets/{t.id}", status_code=303)


@router.put("/targets/{target_id}", response_class=HTMLResponse)
async def api_update_target(request: Request, target_id: int, db: Session = Depends(get_db)):
    form = await request.form()
    data = TargetUpdate(
        title=form.get("title") or None,
        description=form.get("description") or None,
        target_type=form.get("target_type") or None,
        deadline=form.get("deadline") or None,
        priority=int(form["priority"]) if form.get("priority") else None,
    )
    t = update_target(db, target_id, data)
    if not t:
        return HTMLResponse("Target not found", status_code=404)
    return templates.TemplateResponse("targets/card.html", {
        "request": request, "target": t,
    }, headers={"HX-Trigger": '{"show-toast": {"message": "Target updated!", "type": "success"}}'})


@router.put("/targets/{target_id}/header", response_class=HTMLResponse)
async def api_update_target_header(request: Request, target_id: int, db: Session = Depends(get_db)):
    form = await request.form()
    t = get_target(db, target_id)
    if not t:
        return HTMLResponse("", status_code=404)
    if form.get("target_type"):
        t.target_type = form["target_type"]
    if form.get("priority"):
        t.priority = int(form["priority"])
    if "description" in form:
        t.description = form.get("description") or None
    t.updated_at = datetime.now()
    db.commit()
    db.refresh(t)
    return templates.TemplateResponse("targets/detail_header.html", {
        "request": request, "target": t,
    }, headers={"HX-Trigger": json.dumps({"show-toast": {"message": "已更新", "type": "success"}})})


@router.delete("/targets/{target_id}", response_class=HTMLResponse)
async def api_delete_target(target_id: int, db: Session = Depends(get_db)):
    ok = delete_target(db, target_id)
    if not ok:
        return HTMLResponse("Target not found", status_code=404)
    return HTMLResponse("", headers={"HX-Trigger": '{"show-toast": {"message": "Target deleted", "type": "success"}}'})


@router.post("/targets/{target_id}/complete", response_class=HTMLResponse)
async def api_complete_target(request: Request, target_id: int, db: Session = Depends(get_db)):
    t = complete_target(db, target_id)
    if not t:
        return HTMLResponse("Target not found", status_code=404)
    log_action(db, "complete_target", f"完成了目标「{t.title}」", target_type=t.target_type, target_id=t.id)
    return templates.TemplateResponse("targets/card.html", {
        "request": request, "target": t,
    }, headers={"HX-Trigger": '{"show-toast": {"message": "Target completed!", "type": "success"}}'})


@router.post("/targets/{target_id}/progress", response_class=HTMLResponse)
async def api_update_progress(request: Request, target_id: int, db: Session = Depends(get_db)):
    form = await request.form()
    progress = int(form.get("progress", 0))
    t = update_progress(db, target_id, progress)
    if not t:
        return HTMLResponse("Target not found", status_code=404)
    if request.query_params.get("section"):
        return templates.TemplateResponse("targets/progress_section.html", {
            "request": request, "target": t,
        })
    return templates.TemplateResponse("targets/card.html", {
        "request": request, "target": t,
    })


@router.post("/milestones/{milestone_id}/toggle", response_class=HTMLResponse)
async def api_toggle_milestone(request: Request, milestone_id: int, db: Session = Depends(get_db)):
    m = toggle_milestone(db, milestone_id)
    if not m:
        return HTMLResponse("Milestone not found", status_code=404)
    t = get_target(db, m.target_id)
    if m.completed:
        log_action(db, "complete_milestone", f"完成了「{t.title}」里程碑「{m.title}」", target_id=m.id)
    else:
        remove_milestone_completion(db, m.id)
    row_html = templates.get_template("targets/milestone_row.html").render({"request": request, "m": m})
    progress_html = templates.get_template("targets/progress_section.html").render({"request": request, "target": t, "oob": True})
    return HTMLResponse(row_html + progress_html)


@router.get("/milestones/{milestone_id}/row", response_class=HTMLResponse)
async def api_get_milestone_row(request: Request, milestone_id: int, db: Session = Depends(get_db)):
    m = db.query(TargetMilestone).filter(TargetMilestone.id == milestone_id).first()
    if not m:
        return HTMLResponse("", status_code=404)
    return templates.TemplateResponse("targets/milestone_row.html", {"request": request, "m": m})


@router.get("/milestones/{milestone_id}/edit", response_class=HTMLResponse)
async def api_edit_milestone_form(request: Request, milestone_id: int, db: Session = Depends(get_db)):
    m = db.query(TargetMilestone).filter(TargetMilestone.id == milestone_id).first()
    if not m:
        return HTMLResponse("", status_code=404)
    return templates.TemplateResponse("targets/milestone_edit.html", {"request": request, "m": m})


@router.put("/milestones/{milestone_id}", response_class=HTMLResponse)
async def api_update_milestone(request: Request, milestone_id: int, db: Session = Depends(get_db)):
    form = await request.form()
    title = form.get("title", "").strip()
    date_str = form.get("suggested_date", "").strip()
    suggested_date = None
    if date_str:
        try:
            suggested_date = datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            pass
    m = update_milestone(db, milestone_id, title=title, suggested_date=suggested_date)
    if not m:
        return HTMLResponse("", status_code=404)
    t = get_target(db, m.target_id)
    list_html = templates.get_template("targets/milestone_list.html").render({"request": request, "target": t})
    heading_html = f'<h2 class="text-sm font-medium mb-2" style="color: var(--text-primary)" hx-swap-oob="true">里程碑 ({len(t.milestones)})</h2>'
    return HTMLResponse(list_html + heading_html)


@router.delete("/milestones/{milestone_id}", response_class=HTMLResponse)
async def api_delete_milestone(request: Request, milestone_id: int, db: Session = Depends(get_db)):
    m = db.query(TargetMilestone).filter(TargetMilestone.id == milestone_id).first()
    if not m:
        return HTMLResponse("", status_code=404)
    target_id = m.target_id
    delete_milestone(db, milestone_id)
    recalculate_milestone_progress(db, target_id)
    t = get_target(db, target_id)
    list_html = templates.get_template("targets/milestone_list.html").render({"request": request, "target": t})
    heading_html = f'<h2 class="text-sm font-medium mb-2" style="color: var(--text-primary)" hx-swap-oob="true">里程碑 ({len(t.milestones)})</h2>'
    progress_html = templates.get_template("targets/progress_section.html").render({"request": request, "target": t, "oob": True})
    return HTMLResponse(
        list_html + heading_html + progress_html,
        headers={"HX-Trigger": json.dumps({"show-toast": {"message": "里程碑已删除", "type": "success"}})}
    )


@router.post("/targets/{target_id}/milestones", response_class=HTMLResponse)
async def api_add_milestone(request: Request, target_id: int, db: Session = Depends(get_db)):
    form = await request.form()
    title = form.get("title", "").strip()
    if not title:
        return HTMLResponse("", status_code=400)
    date_str = form.get("suggested_date", "").strip()
    suggested_date = None
    if date_str:
        try:
            suggested_date = datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            pass
    create_milestone(db, target_id, title, suggested_date=suggested_date)
    recalculate_milestone_progress(db, target_id)
    t = get_target(db, target_id)
    list_html = templates.get_template("targets/milestone_list.html").render({"request": request, "target": t})
    heading_html = f'<h2 class="text-sm font-medium mb-2" style="color: var(--text-primary)" hx-swap-oob="true">里程碑 ({len(t.milestones)})</h2>'
    progress_html = templates.get_template("targets/progress_section.html").render({"request": request, "target": t, "oob": True})
    return HTMLResponse(
        list_html + heading_html + progress_html,
        headers={"HX-Trigger": json.dumps({"show-toast": {"message": "里程碑已添加", "type": "success"}})}
    )


@router.post("/targets/{target_id}/contribution", response_class=HTMLResponse)
async def api_save_contribution(request: Request, target_id: int, db: Session = Depends(get_db)):
    form = await request.form()
    content = form.get("content", "").strip()
    date_str = form.get("date", "").strip()

    t = get_target(db, target_id)
    if not t:
        return HTMLResponse("", status_code=404)

    from datetime import date as date_cls
    log_date = date_cls.today()
    if date_str:
        try:
            log_date = date_cls.fromisoformat(date_str)
        except ValueError:
            pass

    save_contribution(db, target_id, content, log_date=log_date)
    today_c = get_today_contribution(db, target_id)
    recent = list_recent_contributions(db, target_id)
    return templates.TemplateResponse("targets/contribution_section.html", {
        "request": request, "target": t, "contribution": today_c, "recent_contributions": recent,
    }, headers={"HX-Trigger": json.dumps({"show-toast": {"message": "贡献已保存", "type": "success"}})})


@router.delete("/targets/{target_id}/contribution", response_class=HTMLResponse)
async def api_delete_contribution(request: Request, target_id: int, db: Session = Depends(get_db)):
    from datetime import date as date_cls
    date_str = request.query_params.get("date", "")
    log_date = date_cls.today()
    if date_str:
        try:
            log_date = date_cls.fromisoformat(date_str)
        except ValueError:
            pass
    c = get_contribution(db, target_id, log_date)
    if c:
        db.delete(c)
        db.commit()
    t = get_target(db, target_id)
    recent = list_recent_contributions(db, target_id)
    today_c = get_today_contribution(db, target_id)
    return templates.TemplateResponse("targets/contribution_section.html", {
        "request": request, "target": t, "contribution": today_c, "recent_contributions": recent,
    }, headers={"HX-Trigger": json.dumps({"show-toast": {"message": "贡献已删除", "type": "success"}})})


@router.post("/targets/reorder", response_class=HTMLResponse)
async def api_reorder_targets(request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    ids_str = form.get("ids", "")
    if not ids_str:
        return HTMLResponse("", status_code=400)
    ordered_ids = [int(x) for x in ids_str.split(",") if x.strip().isdigit()]
    reorder_targets(db, ordered_ids)
    return HTMLResponse("")
