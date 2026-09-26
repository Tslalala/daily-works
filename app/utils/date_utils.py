from datetime import date, datetime, timedelta

from app.i18n import translate

WEEKDAY_LONG_KEYS = [
    "weekday.mon", "weekday.tue", "weekday.wed", "weekday.thu",
    "weekday.fri", "weekday.sat", "weekday.sun",
]
WEEKDAY_SHORT_KEYS = [
    "weekday_short.mon", "weekday_short.tue", "weekday_short.wed", "weekday_short.thu",
    "weekday_short.fri", "weekday_short.sat", "weekday_short.sun",
]


def days_remaining(dt: datetime | None, lang: str = "zh") -> str:
    if dt is None:
        return ""
    delta = (dt.date() - date.today()).days
    if delta < 0:
        return translate(lang, "due.overdue", n=abs(delta))
    elif delta == 0:
        return translate(lang, "due.today")
    elif delta == 1:
        return translate(lang, "due.tomorrow")
    else:
        return translate(lang, "due.left", n=delta)


def deadline_class(dt: datetime | None) -> str:
    # Injected into a style="..." attribute, so this must be CSS, not class names.
    if dt is None:
        return ""
    delta = (dt.date() - date.today()).days
    if delta < 0:
        return "color: var(--danger); font-weight: 700;"
    elif delta <= 3:
        return "color: var(--warn); font-weight: 500;"
    elif delta <= 7:
        return "color: var(--caution);"
    return "color: var(--text-muted);"


def format_dt(dt: datetime | None, fmt="%Y-%m-%d %H:%M") -> str:
    if dt is None:
        return ""
    return dt.strftime(fmt)


def format_date(d: date | None) -> str:
    if d is None:
        return ""
    return d.strftime("%Y-%m-%d")


def priority_label(p: int, lang: str = "zh") -> str:
    key = {1: "prio.high_short", 2: "prio.mid_short", 3: "prio.low_short"}.get(p, "prio.mid_short")
    return translate(lang, key)


def priority_color(p: int) -> str:
    return {1: "red", 2: "yellow", 3: "gray"}.get(p, "gray")


def type_label(t: str, lang: str = "zh") -> str:
    key = {"deadline": "ttype.deadline", "long_term": "ttype.long_term", "short_term": "ttype.short_term"}.get(t)
    return translate(lang, key) if key else t


def weekday_long(d: date | datetime, lang: str = "zh") -> str:
    return translate(lang, WEEKDAY_LONG_KEYS[d.weekday()])


def format_duration(minutes: int, lang: str = "zh") -> str:
    """Minute-precision duration: '8小时48分' / '8h 48m'."""
    minutes = max(0, int(minutes))
    h, m = divmod(minutes, 60)
    if lang == "zh":
        if h and m:
            return f"{h}小时{m}分"
        if h:
            return f"{h}小时"
        return f"{m}分钟"
    if h and m:
        return f"{h}h {m}m"
    if h:
        return f"{h}h"
    return f"{m}m"


def build_calendar(checkin_dates: list[date], days: int = 30, today: date | None = None, notes_map: dict | None = None, lang: str = "zh") -> tuple:
    """Build calendar display data. Returns (calendar_days, checked_count).
    notes_map is an optional dict of date -> note string for tooltip display."""
    today = today or date.today()
    notes_map = notes_map or {}
    cal = []
    checked_count = 0
    for i in range(days - 1, -1, -1):
        d = today - timedelta(days=i)
        checked = d in checkin_dates
        if checked:
            checked_count += 1
        cal.append({
            "day_num": d.day,
            "day_name": translate(lang, WEEKDAY_SHORT_KEYS[d.weekday()]),
            "checked": checked,
            "is_today": d == today,
            "date_iso": d.isoformat(),
            "note": notes_map.get(d) or "",
        })
    return cal, checked_count
