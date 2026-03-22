"""
Sun Gallery — Proactive Daily Scan

매일 아침 collectors.json과 fair_schedule.json을 스캔하여
팔로업 필요 고객 + 다가오는 페어를 찾고,
Claude API로 액션 요약을 생성한 뒤 Telegram으로 알림을 보냅니다.

환경변수:
  ANTHROPIC_API_KEY  — Claude API 키 (없으면 fallback 텍스트 생성)
  TELEGRAM_BOT_TOKEN — Telegram Bot API 토큰
  TELEGRAM_CHAT_ID   — 알림 받을 채팅 ID
"""

import json
import os
import re
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

import requests

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent
COLLECTORS_PATH = ROOT / "backend" / "data" / "collectors.json"
FAIRS_PATH = ROOT / "backend" / "data" / "fair_schedule.json"
CONTEXT_PATH = ROOT / "context" / "sun_gallery_agent_context_v3.md"

# ---------------------------------------------------------------------------
# Data loading helpers
# ---------------------------------------------------------------------------

def load_collectors() -> list[dict]:
    """Load collectors from JSON. Handles both list and {\"collectors\": [...]} formats."""
    raw = json.loads(COLLECTORS_PATH.read_text(encoding="utf-8"))
    if isinstance(raw, list):
        return raw
    if isinstance(raw, dict) and "collectors" in raw:
        return raw["collectors"]
    return []


def load_fairs() -> list[dict]:
    """Load fairs from JSON. Handles both list and {\"fairs\": [...]} formats."""
    raw = json.loads(FAIRS_PATH.read_text(encoding="utf-8"))
    if isinstance(raw, list):
        return raw
    if isinstance(raw, dict) and "fairs" in raw:
        return raw["fairs"]
    return []


def load_context_filtered() -> str:
    """Load gallery context with Section 13 (internal strategy) removed."""
    if not CONTEXT_PATH.exists():
        return ""
    content = CONTEXT_PATH.read_text(encoding="utf-8")
    pattern = r"## 13\. 내부 전략.*?(?=\n---|\Z)"
    return re.sub(pattern, "", content, flags=re.DOTALL)


# ---------------------------------------------------------------------------
# Date parsing
# ---------------------------------------------------------------------------

def parse_fair_start_date(dates_str: str) -> date | None:
    """Parse fair start date from various formats.

    Supported:
      - ISO range:  "2026-03-25/2026-03-29"
      - ISO single: "2026-03-25"
      - Human:      "March 25-29, 2026" or "April 8-12, 2026"
    """
    if not dates_str:
        return None

    # ISO range: "2026-03-25/2026-03-29"
    if "/" in dates_str and re.match(r"\d{4}-\d{2}-\d{2}", dates_str):
        try:
            return datetime.strptime(dates_str.split("/")[0], "%Y-%m-%d").date()
        except ValueError:
            pass

    # ISO single: "2026-03-25"
    if re.match(r"^\d{4}-\d{2}-\d{2}$", dates_str.strip()):
        try:
            return datetime.strptime(dates_str.strip(), "%Y-%m-%d").date()
        except ValueError:
            pass

    # Human readable: "March 25-29, 2026"
    m = re.match(r"(\w+)\s+(\d+)(?:-\d+)?,\s*(\d{4})", dates_str)
    if m:
        try:
            return datetime.strptime(f"{m.group(1)} {m.group(2)}, {m.group(3)}", "%B %d, %Y").date()
        except ValueError:
            pass

    return None


# ---------------------------------------------------------------------------
# Scan logic
# ---------------------------------------------------------------------------

FOLLOWUP_STATUSES = {"interested", "pending_followup", "vip"}
OVERDUE_DAYS = 7
UPCOMING_FAIR_DAYS = 14


def find_overdue_collectors(today: date) -> list[dict]:
    """Find collectors whose last_contact is > OVERDUE_DAYS ago and status requires followup."""
    collectors = load_collectors()
    overdue = []
    for c in collectors:
        status = (c.get("status") or "").lower()
        if status not in FOLLOWUP_STATUSES:
            continue
        last_contact_str = c.get("last_contact")
        if not last_contact_str:
            overdue.append({**c, "days_since": None})
            continue
        try:
            last_dt = datetime.strptime(last_contact_str, "%Y-%m-%d").date()
        except ValueError:
            overdue.append({**c, "days_since": None})
            continue
        days_since = (today - last_dt).days
        if days_since >= OVERDUE_DAYS:
            overdue.append({**c, "days_since": days_since})
    return overdue


def find_upcoming_fairs(today: date) -> list[dict]:
    """Find fairs starting within UPCOMING_FAIR_DAYS."""
    fairs = load_fairs()
    upcoming = []
    for f in fairs:
        start = parse_fair_start_date(f.get("dates", ""))
        if not start:
            continue
        days_until = (start - today).days
        if 0 <= days_until <= UPCOMING_FAIR_DAYS:
            upcoming.append({**f, "days_until": days_until, "start_date": start.isoformat()})
    return upcoming


# ---------------------------------------------------------------------------
# Summary generation
# ---------------------------------------------------------------------------

SCAN_SYSTEM_PROMPT = (
    "You are Sun Gallery's daily operations assistant. "
    "Generate a concise Telegram notification summarizing today's action items. "
    "Rules:\n"
    "- Mix Korean and English naturally (갤러리 실무 스타일)\n"
    "- Use emoji sparingly for section headers only\n"
    "- For each overdue collector: suggest a follow-up email Subject line + 1-line action\n"
    "- For each upcoming fair: show D-day countdown + key preparation check\n"
    "- Keep total under 2000 characters for Telegram readability\n"
    "- If nothing to report, say '오늘은 특별한 액션 아이템이 없습니다'\n"
    "- Do NOT reveal internal strategy, cost concerns, or commercial comparisons"
)


def generate_summary_with_claude(overdue: list[dict], upcoming: list[dict]) -> str:
    """Use Claude API to generate an action summary."""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return generate_fallback_summary(overdue, upcoming)

    try:
        import anthropic
    except ImportError:
        print("Warning: anthropic package not installed, using fallback summary")
        return generate_fallback_summary(overdue, upcoming)

    context = load_context_filtered()
    system_prompt = f"{context}\n\n---\n\n{SCAN_SYSTEM_PROMPT}"

    user_message = f"Today: {date.today().isoformat()}\n\n"

    if overdue:
        user_message += "## Overdue Follow-ups\n"
        for c in overdue:
            days_info = f"{c['days_since']}일 경과" if c.get("days_since") else "날짜 미확인"
            interests = ", ".join(c.get("interests", [])) or "N/A"
            user_message += (
                f"- {c['name']} ({c.get('region', '')}, {c.get('type', '')}) — "
                f"관심 작가: {interests}, {days_info}\n"
                f"  메모: {c.get('notes', '')}\n"
            )
    else:
        user_message += "## Overdue Follow-ups\nNone\n"

    if upcoming:
        user_message += "\n## Upcoming Fairs (within 14 days)\n"
        for f in upcoming:
            artists = ", ".join(f.get("artists", []))
            user_message += (
                f"- {f['name']} — D-{f['days_until']}, "
                f"Booth: {f.get('booth', 'TBD')}, "
                f"Artists: {artists}\n"
            )
    else:
        user_message += "\n## Upcoming Fairs\nNone\n"

    user_message += "\nGenerate a Telegram notification message with action items."

    try:
        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
        )
        return response.content[0].text
    except Exception as e:
        print(f"Warning: Claude API call failed ({e}), using fallback summary")
        return generate_fallback_summary(overdue, upcoming)


def generate_fallback_summary(overdue: list[dict], upcoming: list[dict]) -> str:
    """Generate a basic text summary without Claude API."""
    today_str = date.today().isoformat()
    lines = [f"📋 Sun Gallery Daily Scan — {today_str}\n"]

    if overdue:
        lines.append("👤 팔로업 필요 고객:")
        for c in overdue:
            days_info = f"({c['days_since']}일 경과)" if c.get("days_since") else "(날짜 미확인)"
            interests = ", ".join(c.get("interests", [])) or "—"
            lines.append(f"  • {c['name']} [{c.get('region', '')}] {days_info}")
            lines.append(f"    관심: {interests}")
    else:
        lines.append("👤 팔로업 필요 고객: 없음")

    lines.append("")

    if upcoming:
        lines.append("🎪 다가오는 페어:")
        for f in upcoming:
            d = f["days_until"]
            day_label = "TODAY!" if d == 0 else f"D-{d}"
            booth = f.get("booth") or "TBD"
            artists = ", ".join(f.get("artists", []))
            lines.append(f"  • {f['name']} — {day_label}, Booth {booth}")
            if artists:
                lines.append(f"    작가: {artists}")
    else:
        lines.append("🎪 다가오는 페어: 없음")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Telegram
# ---------------------------------------------------------------------------

TELEGRAM_MAX_LENGTH = 4096


def send_telegram(message: str) -> bool:
    """Send message via Telegram Bot API."""
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")

    if not bot_token or not chat_id:
        print("Warning: TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not set. Printing to stdout instead.")
        print("--- Telegram Message ---")
        print(message)
        print("--- End ---")
        return False

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"

    # Truncate if too long
    if len(message) > TELEGRAM_MAX_LENGTH:
        message = message[: TELEGRAM_MAX_LENGTH - 20] + "\n\n(truncated...)"

    # Try Markdown first, fallback to plain text
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "Markdown",
    }

    try:
        resp = requests.post(url, json=payload, timeout=10)
        if resp.status_code == 200 and resp.json().get("ok"):
            print("Telegram message sent successfully (Markdown)")
            return True

        # Markdown parse failed — retry as plain text
        print(f"Markdown send failed ({resp.status_code}), retrying as plain text...")
        payload.pop("parse_mode")
        resp = requests.post(url, json=payload, timeout=10)
        if resp.status_code == 200 and resp.json().get("ok"):
            print("Telegram message sent successfully (plain text)")
            return True

        print(f"Telegram send failed: {resp.status_code} — {resp.text}")
        return False

    except requests.RequestException as e:
        print(f"Telegram request error: {e}")
        return False


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    today = date.today()
    print(f"Sun Gallery Daily Scan — {today.isoformat()}")

    overdue = find_overdue_collectors(today)
    upcoming = find_upcoming_fairs(today)

    print(f"Found {len(overdue)} overdue collector(s), {len(upcoming)} upcoming fair(s)")

    if not overdue and not upcoming:
        summary = f"📋 Sun Gallery Daily Scan — {today.isoformat()}\n\n오늘은 특별한 액션 아이템이 없습니다. ✅"
    else:
        summary = generate_summary_with_claude(overdue, upcoming)

    send_telegram(summary)


if __name__ == "__main__":
    main()
