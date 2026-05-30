"""AI service for target suggestions using OpenAI-compatible API."""
import json
import re
from datetime import date

from openai import OpenAI

from app.config import get_api_base, get_api_key, save_api_key

DEFAULT_MODEL = "deepseek-chat"
DEFAULT_BASE_URL = "https://api.deepseek.com"
REQUEST_TIMEOUT = 15  # seconds

SYSTEM_PROMPT = """你是一个目标管理助手。根据用户提供的目标标题和描述，生成结构化的目标建议。

请以 JSON 格式返回，包含以下字段：
- description: 对目标的简要理解（2-3句中文）
- target_type: 建议的目标类型，只能是 "deadline"（有期限）或 "short_term"（短期）或 "long_term"（长期）
- importance: 重要程度，1-5 的整数（5=最重要）
- deadline_suggestion: 如果 target_type 是 deadline，给出建议的截止日期，格式为 YYYY-MM-DD（如 "2026-05-21"），否则为 null
- milestones: 任务节点数组。对于可以拆分成多个步骤的任务，拆分为 2-5 个节点。每个节点包含：
    - title: 节点的简要描述（如"修改PPT"、"收集资料"）
    - date: 建议完成的日期，格式为 YYYY-MM-DD，日期必须从今天开始往后排

今天是 {today}。请基于这个日期来建议所有时间节点。
如果任务是简单任务（无法拆分），milestones 可以为空数组 []。

只返回 JSON，不要包含其他文字。"""


def _call_llm(prompt: str, api_key: str = "", base_url: str = "", model: str = "") -> str:
    """Call an OpenAI-compatible LLM and return the raw response text."""
    key = api_key or get_api_key()
    if not key:
        raise ValueError("API key not configured")

    client = OpenAI(api_key=key, base_url=base_url or get_api_base() or DEFAULT_BASE_URL, timeout=REQUEST_TIMEOUT)
    resp = client.chat.completions.create(
        model=model or DEFAULT_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT.format(today=date.today().isoformat())},
            {"role": "user", "content": prompt},
        ],
        temperature=0.7,
        max_tokens=800,
    )
    return resp.choices[0].message.content or ""


def _parse_suggestion(raw: str) -> dict:
    """Extract JSON from LLM response."""
    json_match = re.search(r"\{.*\}", raw, re.DOTALL)
    if json_match:
        raw = json_match.group()
    data = json.loads(raw)
    # Validate
    assert data["target_type"] in ("deadline", "short_term", "long_term")
    assert 1 <= data["importance"] <= 5

    milestones = data.get("milestones", [])
    if not isinstance(milestones, list):
        milestones = []

    return {
        "description": data.get("description", ""),
        "target_type": data["target_type"],
        "importance": data["importance"],
        "deadline_suggestion": data.get("deadline_suggestion") or None,
        "milestones": milestones,
    }


def check_api_key(api_key: str = "", base_url: str = "") -> bool:
    """Check if the API key works by making a minimal request."""
    try:
        key = api_key or get_api_key()
        if not key:
            return False
        model = DEFAULT_MODEL
        base = base_url or get_api_base() or DEFAULT_BASE_URL
        client = OpenAI(api_key=key, base_url=base, timeout=REQUEST_TIMEOUT)
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "OK"}],
            max_tokens=1,
        )
        return bool(resp.choices)
    except Exception:
        return False


DAILY_LOG_PROMPT = """你是一个个人日记助手。根据用户今天完成的以下活动，帮用户写一篇日记。

要求：
- 使用第一人称"我"
- 写流水账风格即可，不需要文采，不需要感悟和反思
- 只写确定发生的事情，不要编造内容
- 语气平淡自然，不要煽情肉麻
- 100-200字左右
- 直接返回日记内容

今天的活动：
{activities}

请写日记："""


DAILY_LOG_APPEND_PROMPT = """用户已经写了一些日记内容草稿。请结合用户今天完成的活动，把草稿完善成一篇完整的日记。

要求：
- 保留用户草稿的核心内容和原意，不要编造没有的内容
- 可以进行适当调整让语句更通顺
- 把活动记录自然地融入日记中
- 不要更改用户的分段结构，只在必要时添加新的段落
- 使用第一人称"我"
- 语气平淡自然，不要煽情肉麻
- 100-200字左右
- 直接返回完整的日记内容

用户草稿：
{existing_content}

今天的活动：
{activities}

请写完整的日记："""


def generate_daily_summary(activities: list[str], existing_content: str = "", api_key: str = "", base_url: str = "", model: str = "") -> str:
    """Generate a daily diary entry from activity descriptions.

    If existing_content is provided, the AI integrates it with activities
    into a cohesive diary entry while preserving original meaning.
    Otherwise generates a fresh entry from activities only.
    """
    key = api_key or get_api_key()
    if not key:
        raise ValueError("API key not configured")

    client = OpenAI(api_key=key, base_url=base_url or get_api_base() or DEFAULT_BASE_URL, timeout=REQUEST_TIMEOUT)
    activities_text = "\n".join(f"- {a}" for a in activities) if activities else "今天没有特别的活动记录。"

    if existing_content:
        prompt = DAILY_LOG_APPEND_PROMPT.format(existing_content=existing_content, activities=activities_text)
    else:
        prompt = DAILY_LOG_PROMPT.format(activities=activities_text)

    resp = client.chat.completions.create(
        model=model or DEFAULT_MODEL,
        messages=[
            {"role": "system", "content": "你是一个日记助手。请用中文回复，语气平淡自然。"},
            {"role": "user", "content": prompt},
        ],
        temperature=0.7,
        max_tokens=500,
    )
    new_content = resp.choices[0].message.content or ""
    return new_content  # full combined diary entry (AI handles integration of existing + new)


def suggest_target(title: str, description: str = "", api_key: str = "", base_url: str = "", model: str = "") -> dict:
    """Generate an AI suggestion for a target."""
    desc_text = f"\n描述：{description}" if description else ""
    prompt = f"目标标题：{title}{desc_text}\n\n请分析这个目标并给出建议。"
    raw = _call_llm(prompt, api_key=api_key, base_url=base_url, model=model)
    return _parse_suggestion(raw)


def refine_target(title: str, feedback: str, description: str = "", original_suggestion: dict = None, api_key: str = "", base_url: str = "", model: str = "") -> dict:
    """Refine a previous suggestion based on user feedback."""
    desc_text = f"\n描述：{description}" if description else ""

    prompt = f"目标标题：{title}{desc_text}\n\n"

    if original_suggestion:
        orig_json = json.dumps(original_suggestion, ensure_ascii=False)
        prompt += f"之前的AI建议（仅作参考）：{orig_json}\n\n"

    prompt += (
        f"用户的补充意见：{feedback}\n\n"
        f"请根据用户的反馈重新分析并更新建议。用户可能想调整类型、时间、重要度或拆分方式。"
    )
    raw = _call_llm(prompt, api_key=api_key, base_url=base_url, model=model)
    return _parse_suggestion(raw)
