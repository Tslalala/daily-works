from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATABASE_URL = f"sqlite:///{BASE_DIR / 'daily_planner.db'}"
APP_NAME = "Daily Planner"
TIMEZONE = "Asia/Shanghai"

# Fixed AI endpoint (local service) — no user-facing configuration.
AI_API_KEY = "callmemaybe"
AI_BASE_URL = "http://47.109.104.139:21000/v1"
AI_MODEL = "Qwen3.8-27B-BF16"
