import json
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATABASE_URL = f"sqlite:///{BASE_DIR / 'daily_planner.db'}"
APP_NAME = "Daily Planner"
TIMEZONE = "Asia/Shanghai"
API_CONFIG_FILE = BASE_DIR / ".apikey"


def _read_config() -> dict:
    if API_CONFIG_FILE.exists():
        try:
            return json.loads(API_CONFIG_FILE.read_text().strip())
        except (json.JSONDecodeError, ValueError):
            # Legacy: plain text key
            old = API_CONFIG_FILE.read_text().strip()
            if old:
                return {"key": old}
    return {}


def _write_config(data: dict):
    API_CONFIG_FILE.write_text(json.dumps(data, ensure_ascii=False))


def get_api_key():
    key = os.getenv("ANTHROPIC_API_KEY", "")
    if not key:
        key = _read_config().get("key", "")
    return key


def save_api_key(key: str):
    cfg = _read_config()
    cfg["key"] = key.strip()
    _write_config(cfg)


def clear_api_key():
    cfg = _read_config()
    cfg.pop("key", None)
    if cfg:
        _write_config(cfg)
    elif API_CONFIG_FILE.exists():
        API_CONFIG_FILE.unlink()


def get_api_base():
    return _read_config().get("base", "")


def save_api_base(url: str):
    cfg = _read_config()
    cfg["base"] = url.strip()
    _write_config(cfg)
