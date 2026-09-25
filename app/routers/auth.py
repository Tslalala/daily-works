from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.auth import (
    COOKIE_NAME,
    SESSION_DAYS,
    create_session,
    delete_session,
    get_current_user,
    get_user_by_username,
    hash_password,
    verify_password,
)
from app.database import get_db
from app.i18n import tt
from app.models.user import User
from app.services.activity_service import log_action
from app.templates import templates

router = APIRouter()

MAX_USERNAME_LEN = 30
MIN_PASSWORD_LEN = 6


def _set_session_cookie(resp: RedirectResponse, token: str) -> RedirectResponse:
    resp.set_cookie(
        COOKIE_NAME,
        token,
        max_age=SESSION_DAYS * 86400,
        httponly=True,
        samesite="lax",
        path="/",
    )
    return resp


def _safe_next(next_url: str) -> str:
    # Only allow same-site relative redirects.
    if next_url and next_url.startswith("/") and not next_url.startswith("//"):
        return next_url
    return "/"


@router.get("/login")
def login_page(request: Request, next: str = "", error: str = ""):
    return templates.TemplateResponse(request, "login.html", {
        "error": error,
        "next": next,
    })


@router.post("/login")
def login_submit(
    request: Request,
    db: Session = Depends(get_db),
    username: str = Form(""),
    password: str = Form(""),
    next: str = Form(""),
):
    user = get_user_by_username(db, username.strip())
    if user is None or not verify_password(password, user.password_hash):
        return templates.TemplateResponse(request, "login.html", {
            "error": tt(request, "auth.bad_credentials"),
            "next": next,
        }, status_code=401)
    token = create_session(db, user.id)
    log_action(db, user.id, "login", tt(request, "auth.act_login"))
    return _set_session_cookie(RedirectResponse(_safe_next(next), status_code=303), token)


@router.get("/register")
def register_page(request: Request, error: str = ""):
    return templates.TemplateResponse(request, "register.html", {"error": error})


@router.post("/register")
def register_submit(
    request: Request,
    db: Session = Depends(get_db),
    username: str = Form(""),
    password: str = Form(""),
    password2: str = Form(""),
):
    username = username.strip()
    error = ""
    if not username or len(username) > MAX_USERNAME_LEN:
        error = tt(request, "auth.username_invalid")
    elif get_user_by_username(db, username):
        error = tt(request, "auth.username_taken")
    elif len(password) < MIN_PASSWORD_LEN:
        error = tt(request, "auth.password_short")
    elif password != password2:
        error = tt(request, "auth.password_mismatch")
    if error:
        return templates.TemplateResponse(request, "register.html", {"error": error}, status_code=400)

    user = User(username=username, password_hash=hash_password(password))
    db.add(user)
    db.commit()
    db.refresh(user)
    token = create_session(db, user.id)
    log_action(db, user.id, "register", tt(request, "auth.act_register"))
    return _set_session_cookie(RedirectResponse("/", status_code=303), token)


@router.post("/logout")
def logout(request: Request, db: Session = Depends(get_db)):
    token = request.cookies.get(COOKIE_NAME)
    if token:
        delete_session(db, token)
    resp = RedirectResponse("/login", status_code=303)
    resp.delete_cookie(COOKIE_NAME, path="/")
    return resp


@router.get("/account")
def account_page(request: Request, user: User = Depends(get_current_user), changed: str = "", appearance: str = ""):
    return templates.TemplateResponse(request, "account.html", {
        "user": user,
        "changed": changed,
        "appearance": appearance,
        "error": "",
    })


@router.post("/account/appearance")
def change_appearance(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    overlay_style: str = Form("grid"),
):
    user.overlay_style = overlay_style if overlay_style in ("grid", "glass") else "grid"
    db.commit()
    log_action(db, user.id, "appearance_changed", tt(request, "auth.act_appearance_changed"))
    return RedirectResponse("/account?appearance=1", status_code=303)


@router.post("/account/password")
def change_password(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    old_password: str = Form(""),
    password: str = Form(""),
    password2: str = Form(""),
):
    if not verify_password(old_password, user.password_hash):
        return templates.TemplateResponse(request, "account.html", {
            "user": user, "changed": "", "error": tt(request, "auth.wrong_old_password"),
        }, status_code=400)
    if len(password) < MIN_PASSWORD_LEN:
        return templates.TemplateResponse(request, "account.html", {
            "user": user, "changed": "", "error": tt(request, "auth.password_short"),
        }, status_code=400)
    if password != password2:
        return templates.TemplateResponse(request, "account.html", {
            "user": user, "changed": "", "error": tt(request, "auth.password_mismatch"),
        }, status_code=400)
    user.password_hash = hash_password(password)
    db.commit()
    log_action(db, user.id, "password_changed", tt(request, "auth.act_password_changed"))
    return RedirectResponse("/account?changed=1", status_code=303)
