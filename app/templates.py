from datetime import datetime
from pathlib import Path

from fastapi.templating import Jinja2Templates

from app.auth import get_user_from_request
from app.database import SessionLocal
from app.i18n import get_lang, jinja_t
from app.utils.quotes import random_quote

BASE_DIR = Path(__file__).resolve().parent.parent

# Cache-busting version for static assets: the CSS file's mtime, so a deploy
# that changes the stylesheet automatically invalidates browser caches.
_CSS_FILE = BASE_DIR / "static" / "editorial.css"
try:
    CSS_VERSION = _CSS_FILE.stat().st_mtime_ns
except OSError:
    CSS_VERSION = 0


def _default_context(req) -> dict:
    ctx = {
        "lang": get_lang(req),
        "now": datetime.now(),
        "css_version": CSS_VERSION,
        "quote": random_quote(),
    }
    db = SessionLocal()
    try:
        ctx["user"] = get_user_from_request(db, req)
    finally:
        db.close()
    return ctx


# context_processors inject the request's language and current time into every
# TemplateResponse context, so templates can call {{ t('key') }} / {{ now }}
# without per-route boilerplate.
templates = Jinja2Templates(
    directory=str(BASE_DIR / "templates"),
    context_processors=[_default_context],
)
templates.env.globals["t"] = jinja_t
