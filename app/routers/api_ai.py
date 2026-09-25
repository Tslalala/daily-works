import json
from datetime import date, datetime

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.i18n import tt
from app.models.user import User
from app.models.target import TargetMilestone
from app.schemas.target_schema import TargetCreate
from app.services.activity_service import log_action
from app.services.activity_service import get_logs_by_date
from app.services.ai_service import generate_daily_summary, refine_target, suggest_target
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


@router.post("/suggest-target", response_class=HTMLResponse)
async def ai_suggest_target(request: Request, user: User = Depends(get_current_user)):
    """Generate AI suggestion for a target."""
    form = await request.form()
    title = form.get("title", "").strip()
    description = form.get("description", "").strip()
    target_id = form.get("target_id") or None

    if not title:
        return HTMLResponse(f"<div class='text-red-500 text-sm'>{tt(request, 'ai.err_title')}</div>")

    try:
        suggestion = suggest_target(title, description)
    except ValueError:
        return HTMLResponse(
            f"<div class='text-amber-600 text-sm p-3 bg-amber-50 rounded-lg border border-amber-200'>"
            f"{tt(request, 'ai.err_not_configured')}"
            f"</div>"
        )
    except Exception as e:
        return HTMLResponse(
            f"<div class='text-red-500 text-sm p-3 bg-red-50 rounded-lg'>{tt(request, 'ai.err_call')}: {str(e)[:100]}</div>"
        )

    return templates.TemplateResponse(request, "targets/ai_suggestion.html", {
        "request": request,
        "suggestion": suggestion,
        "title": title,
        "description": description,
        "target_id": target_id,
        "now": datetime.now(),
    })


@router.post("/refine-target", response_class=HTMLResponse)
async def ai_refine_target(request: Request, user: User = Depends(get_current_user)):
    """Refine suggestion based on user feedback."""
    form = await request.form()
    title = form.get("title", "").strip()
    description = form.get("description", "").strip()
    feedback = form.get("feedback", "").strip()
    target_id = form.get("target_id") or None

    if not feedback:
        return HTMLResponse(f"<div class='text-red-500 text-sm'>{tt(request, 'ai.err_feedback')}</div>")

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
            f"<div class='text-red-500 text-sm p-3 bg-red-50 rounded-lg'>{tt(request, 'ai.err_call')}: {str(e)[:100]}</div>"
        )

    return templates.TemplateResponse(request, "targets/ai_suggestion.html", {
        "request": request,
        "suggestion": suggestion,
        "title": title,
        "description": description,
        "target_id": target_id,
        "now": datetime.now(),
    })


@router.post("/accept-target")
async def ai_accept_target(request: Request, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
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
        t = update_target(db, user.id, int(target_id), data)
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
        log_action(db, user.id, "update_target", f"AI 更新了{type_label}目标「{t.title}」", target_type=t.target_type, target_id=t.id)
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
        t = create_target(db, user.id, data)

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
        log_action(db, user.id, "create_target", f"创建了{type_label}目标「{t.title}」(AI)", target_type=t.target_type, target_id=t.id)
        return RedirectResponse(url=f"/targets/{t.id}?ai_created=1", status_code=303)


@router.post("/generate-daily-log", response_class=HTMLResponse)
async def ai_generate_daily_log(request: Request, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Generate a daily diary entry from today's activity logs."""
    form = await request.form()
    log_date_str = form.get("date", "").strip()
    existing_content = form.get("content", "").strip()
    try:
        log_date = date.fromisoformat(log_date_str) if log_date_str else date.today()
    except ValueError:
        log_date = date.today()

    activities = get_logs_by_date(db, user.id, log_date)
    descriptions = [a.description for a in activities]

    if not descriptions and not existing_content:
        return HTMLResponse(tt(request, "ai.no_activity"))

    try:
        result = generate_daily_summary(descriptions, existing_content=existing_content)
    except ValueError:
        return HTMLResponse(tt(request, "ai.err_not_configured"))
    except Exception as e:
        return HTMLResponse(f"{tt(request, 'ai.err_call')}: {str(e)[:80]}")

    return HTMLResponse(result)
