"""Settings API: language switch (cookie-backed, full-page reload on change)."""
from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse

from app.i18n import COOKIE_NAME, SUPPORTED

router = APIRouter(prefix="/api/settings")


@router.post("/lang")
async def set_language(request: Request):
    form = await request.form()
    lang = form.get("lang", "").strip()
    if lang not in SUPPORTED:
        lang = "zh"
    referer = request.headers.get("Referer") or "/"
    # Keep the query string so we land back where the user was.
    if "?" in referer:
        referer = referer.split("?", 1)[0]
    return RedirectResponse(url=referer, status_code=303, headers={
        "Set-Cookie": f"{COOKIE_NAME}={lang}; Path=/; Max-Age=31536000; SameSite=Lax",
    })
