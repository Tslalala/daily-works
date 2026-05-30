from datetime import date, datetime, timedelta


def days_remaining(dt: datetime | None) -> str:
    if dt is None:
        return ""
    delta = (dt.date() - date.today()).days
    if delta < 0:
        return f"已过期 {abs(delta)} 天"
    elif delta == 0:
        return "今天截止！"
    elif delta == 1:
        return "明天截止"
    else:
        return f"剩余 {delta} 天"


def deadline_class(dt: datetime | None) -> str:
    if dt is None:
        return ""
    delta = (dt.date() - date.today()).days
    if delta < 0:
        return "text-red-600 font-bold"
    elif delta <= 3:
        return "text-orange-500 font-medium"
    elif delta <= 7:
        return "text-yellow-600"
    return "text-gray-500"


def format_dt(dt: datetime | None, fmt="%Y-%m-%d %H:%M") -> str:
    if dt is None:
        return ""
    return dt.strftime(fmt)


def format_date(d: date | None) -> str:
    if d is None:
        return ""
    return d.strftime("%Y-%m-%d")


def priority_label(p: int) -> str:
    return {1: "高", 2: "中", 3: "低"}.get(p, "中")


def priority_color(p: int) -> str:
    return {1: "red", 2: "yellow", 3: "gray"}.get(p, "gray")


def type_label(t: str) -> str:
    return {"deadline": "有期限", "long_term": "长期", "short_term": "短期"}.get(t, t)


def build_calendar(checkin_dates: list[date], days: int = 30, today: date | None = None, notes_map: dict | None = None) -> tuple:
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
            "day_name": ["一", "二", "三", "四", "五", "六", "日"][d.weekday()],
            "checked": checked,
            "is_today": d == today,
            "date_iso": d.isoformat(),
            "note": notes_map.get(d) or "",
        })
    return cal, checked_count
