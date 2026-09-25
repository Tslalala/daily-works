"""Authentication: password hashing, session tokens, current-user guard.

Sessions are random tokens stored in the ``sessions`` table and carried in an
HttpOnly cookie. No external auth libraries are required.
"""
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional
from urllib.parse import quote

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import RedirectResponse, Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.models.session import AppSession

COOKIE_NAME = "session"
SESSION_DAYS = 30
PBKDF2_ITERATIONS = 600_000


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode(), bytes.fromhex(salt), PBKDF2_ITERATIONS
    ).hex()
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${salt}${digest}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algo, iterations, salt, digest = stored.split("$")
        if algo != "pbkdf2_sha256":
            return False
        candidate = hashlib.pbkdf2_hmac(
            "sha256", password.encode(), bytes.fromhex(salt), int(iterations)
        ).hex()
        return secrets.compare_digest(candidate, digest)
    except (ValueError, TypeError):
        return False


def get_user_by_username(db: Session, username: str) -> Optional[User]:
    return db.query(User).filter(User.username == username).first()


def create_session(db: Session, user_id: int) -> str:
    token = secrets.token_hex(32)
    now = datetime.now()
    db.add(AppSession(
        token=token,
        user_id=user_id,
        created_at=now,
        expires_at=now + timedelta(days=SESSION_DAYS),
    ))
    db.commit()
    return token


def delete_session(db: Session, token: str) -> None:
    db.query(AppSession).filter(AppSession.token == token).delete()
    db.commit()


def get_user_from_request(db: Session, request: Request) -> Optional[User]:
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        return None
    row = db.query(AppSession).filter(AppSession.token == token).first()
    if row is None:
        return None
    if row.expires_at < datetime.now():
        db.delete(row)
        db.commit()
        return None
    return db.get(User, row.user_id)


class LoginRequired(Exception):
    """Raised by the route guard for anonymous page visits; the registered
    exception handler turns it into a redirect to /login."""

    def __init__(self, next_url: str = "/"):
        self.next_url = next_url


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    """Route guard: logged-in users pass through; anonymous visitors get a
    redirect to /login (pages) or a 401 (API/htmx calls, handled client-side)."""
    user = get_user_from_request(db, request)
    if user is not None:
        return user
    path = request.url.path
    if path.startswith("/api/"):
        raise HTTPException(status_code=401, detail="Not authenticated")
    next_url = path + (f"?{request.url.query}" if request.url.query else "")
    raise LoginRequired(next_url)


def install_auth_handlers(app: FastAPI) -> None:
    @app.exception_handler(LoginRequired)
    async def _handle_login_required(request: Request, exc: LoginRequired) -> Response:
        return RedirectResponse(f"/login?next={quote(exc.next_url)}", status_code=302)
