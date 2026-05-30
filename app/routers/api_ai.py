import json
from datetime import date, datetime

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.config import get_api_key, save_api_key, save_api_base
from app.database import get_db
from app.models.target import TargetMilestone
from app.schemas.ai_schema import AISuggestRequest, SetKeyRequest
from app.schemas.target_schema import TargetCreate
from app.services.activity_service import log_action
from app.services.activity_service import get_logs_by_date
from app.services.ai_service import check_api_key, generate_daily_summary, refine_target, suggest_target
from app.services.target_service import create_target, update_target
from app.templates import templates

router = APIRouter(prefix="/api/ai")


def _import_to_priority(importance: int) -> int:
    """Map 5-star importance to 1-3 priority."""
    if importance >= 4:
        return 1
    elif importance >= 3:
        return 2
    return 3


@router.get("/key-input", response_class=HTMLResponse)
async def ai_key_input(request: Request):
    """Return the API key input form fragment."""
    return templates.TemplateResponse("components/api_key_input.html", {"request": request})


@router.get("/status")
async def ai_status():
    """Check if AI is available (API key configured + working)."""
    key = get_api_key()
    if not key:
        return {"available": False, "reason": "no_key"}
    ok = check_api_key()
    return {"available": ok}


@router.post("/set-key", response_class=HTMLResponse)
async def set_api_key(request: Request):
    """Save API key and test it."""
    form = await request.form()
    api_key = form.get("api_key", "").strip()
    api_base = form.get("api_base", "").strip()
    if not api_key:
        return HTMLResponse("<div class='text-red-500 text-sm'>API Key 不能为空</div>")

    # Test the key
    ok = check_api_key(api_key=api_key, base_url=api_base)
    if not ok:
        return HTMLResponse("<div class='text-red-500 text-sm'>API Key 无效或网络不可达，请检查</div>")

    # Save key
    save_api_key(api_key)
    # Also persist api_base if provided
    if api_base:
        save_api_base(api_base)

    return HTMLResponse("", headers={"HX-Trigger": '{"show-toast": {"message": "API Key saved! AI activated.", "type": "success"}, "settings-saved": {}}'})


@router.post("/suggest-target", response_class=HTMLResponse)
async def ai_suggest_target(request: Request):
    """Generate AI suggestion for a target."""
    form = await request.form()
    title = form.get("title", "").strip()
    description = form.get("description", "").strip()
    target_id = form.get("target_id") or None

    if not title:
        return HTMLResponse("<div class='text-red-500 text-sm'>请先输入目标名称</div>")

    try:
        suggestion = suggest_target(title, description)
    except ValueError as e:
        return HTMLResponse(
            f"<div class='text-amber-600 text-sm p-3 bg-amber-50 rounded-lg border border-amber-200'>"
            f"AI not available: {e}. Click ⚙️ Settings in the navbar to configure an API Key."
            f"</div>"
        )
    except Exception as e:
        return HTMLResponse(
            f"<div class='text-red-500 text-sm p-3 bg-red-50 rounded-lg'>AI 调用失败: {str(e)[:100]}</div>"
        )

    return templates.TemplateResponse("targets/ai_suggestion.html", {
        "request": request,
        "suggestion": suggestion,
        "title": title,
        "description": description,
        "target_id": target_id,
        "now": datetime.now(),
    })


@router.post("/refine-target", response_class=HTMLResponse)
async def ai_refine_target(request: Request):
    """Refine suggestion based on user feedback."""
    form = await request.form()
    title = form.get("title", "").strip()
    description = form.get("description", "").strip()
    feedback = form.get("feedback", "").strip()
    target_id = form.get("target_id") or None

    if not feedback:
        return HTMLResponse("<div class='text-red-500 text-sm'>请输入补充说明</div>")

    # Parse the original suggestion if provided
    original_suggestion = None
    original_json = form.get("original_suggestion", "").strip()
    if original_json:
        try:
            original_suggestion = json.loads(original_json)
        except (json.JSONDecodeError, TypeError):
            pass

    try:
        suggestion = refine_target(title, feedback, description, original_suggestion=original_suggestion)
    except Exception as e:
        return HTMLResponse(
            f"<div class='text-red-500 text-sm p-3 bg-red-50 rounded-lg'>AI 调用失败: {str(e)[:100]}</div>"
        )

    return templates.TemplateResponse("targets/ai_suggestion.html", {
        "request": request,
        "suggestion": suggestion,
        "title": title,
        "description": description,
        "target_id": target_id,
        "now": datetime.now(),
    })


@router.post("/accept-target")
async def ai_accept_target(request: Request, db: Session = Depends(get_db)):
    """Accept AI suggestion and create or update the target."""
    form = await request.form()
    title = form.get("title", "").strip()
    description = form.get("ai_description", "").strip() or form.get("description", "").strip()
    target_type = form.get("target_type", "short_term")
    importance = int(form.get("importance", 3))
    priority = _import_to_priority(importance)
    target_id = form.get("target_id") or None

    # Parse deadline if provided
    deadline = None
    ai_deadline = form.get("ai_deadline", "").strip()
    if ai_deadline:
        try:
            deadline = datetime.strptime(ai_deadline, "%Y-%m-%d")
        except ValueError:
            pass

    # Parse milestones from AI suggestion
    milestones_json = form.get("milestones", "[]")
    try:
        milestones_data = json.loads(milestones_json)
    except (json.JSONDecodeError, TypeError):
        milestones_data = []

    if target_id:
        # Update existing target
        from app.schemas.target_schema import TargetUpdate
        data = TargetUpdate(
            title=title,
            description=description,
            target_type=target_type,
            priority=priority,
            deadline=deadline,
        )
        t = update_target(db, int(target_id), data)
        if not t:
            return HTMLResponse("Target not found", status_code=404)

        # Replace milestones
        db.query(TargetMilestone).filter(TargetMilestone.target_id == t.id).delete()
        for i, m in enumerate(milestones_data):
            milestone_date = None
            if m.get("date"):
                try:
                    milestone_date = datetime.strptime(m["date"], "%Y-%m-%d")
                except ValueError:
                    pass
            ms = TargetMilestone(
                target_id=t.id,
                title=m.get("title", ""),
                suggested_date=milestone_date,
                sort_order=i,
            )
            db.add(ms)
        db.commit()

        type_label = {"deadline": "有期限", "short_term": "短期", "long_term": "长期"}.get(t.target_type, "短期")
        log_action(db, "update_target", f"AI 更新了{type_label}目标「{t.title}」", target_type=t.target_type, target_id=t.id)
        return RedirectResponse(url=f"/targets/{t.id}?ai_updated=1", status_code=303)
    else:
        # Create new target
        data = TargetCreate(
            title=title,
            description=description,
            target_type=target_type,
            priority=priority,
            deadline=deadline,
        )
        t = create_target(db, data)

        for i, m in enumerate(milestones_data):
            milestone_date = None
            if m.get("date"):
                try:
                    milestone_date = datetime.strptime(m["date"], "%Y-%m-%d")
                except ValueError:
                    pass
            ms = TargetMilestone(
                target_id=t.id,
                title=m.get("title", ""),
                suggested_date=milestone_date,
                sort_order=i,
            )
            db.add(ms)
        db.commit()

        type_label = {"deadline": "有期限", "short_term": "短期", "long_term": "长期"}.get(t.target_type, "短期")
        log_action(db, "create_target", f"创建了{type_label}目标「{t.title}」(AI)", target_type=t.target_type, target_id=t.id)
        return RedirectResponse(url=f"/targets/{t.id}?ai_created=1", status_code=303)


@router.post("/generate-daily-log", response_class=HTMLResponse)
async def ai_generate_daily_log(request: Request, db: Session = Depends(get_db)):
    """Generate a daily diary entry from today's activity logs."""
    form = await request.form()
    log_date_str = form.get("date", "").strip()
    existing_content = form.get("content", "").strip()
    try:
        log_date = date.fromisoformat(log_date_str) if log_date_str else date.today()
    except ValueError:
        log_date = date.today()

    activities = get_logs_by_date(db, log_date)
    descriptions = [a.description for a in activities]

    if not descriptions and not existing_content:
        return HTMLResponse("今天还没有活动记录，先去完成一些任务吧！")

    try:
        result = generate_daily_summary(descriptions, existing_content=existing_content)
    except ValueError:
        return HTMLResponse("AI 未配置，请先在 ⚙️ 设置中配置 API Key")
    except Exception as e:
        return HTMLResponse(f"AI 调用失败: {str(e)[:80]}")

    return HTMLResponse(result)
