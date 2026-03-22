"""
Sun Gallery — Interactive Telegram Bot

Telegram 채팅으로 갤러리 업무 지시를 받아 Claude API로 처리하고 결과를 반환합니다.

명령어:
  /start          — 봇 소개 + 명령어 목록
  /email <내용>   — 이메일 드래프트 생성
  /whatsapp <내용> — WhatsApp 답장 생성
  /marketing <내용> — 마케팅 콘텐츠 생성
  /document <내용> — 갤러리 문서 생성
  /translate <내용> — 미술 전문 번역
  /fair <내용>     — 페어 준비 도우미
  /collectors     — 팔로업 필요 고객 목록
  /fairs          — 다가오는 페어 일정
  /scan           — 데일리 스캔 즉시 실행
  /inbox          — 네이버웍스 안 읽은 메일 확인
  /reply <번호>   — 수신 메일에 AI 답장 생성 + 발송 확인
  /sendmail <to> <subject> | <body> — 메일 직접 발송
  /wa <번호> <메시지> — WhatsApp 메시지 직접 발송
  (일반 텍스트)    — 자유 질문 (갤러리 컨텍스트 기반 응답)

환경변수:
  ANTHROPIC_API_KEY    — Claude API 키 (필수)
  TELEGRAM_BOT_TOKEN   — Telegram Bot API 토큰 (필수)
  NAVER_WORKS_EMAIL    — 네이버 웍스 이메일 (선택, /inbox 등에 필요)
  NAVER_WORKS_PASSWORD — 네이버 웍스 외부 앱 비밀번호 (선택)
  WHATSAPP_TOKEN       — WhatsApp Business API 토큰 (선택, /wa에 필요)
  WHATSAPP_PHONE_ID    — WhatsApp 전화번호 ID (선택)

실행:
  python scripts/telegram_bot.py
"""

import json
import os
import re
import time
from datetime import date, datetime
from pathlib import Path

import requests

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent
COLLECTORS_PATH = ROOT / "backend" / "data" / "collectors.json"
FAIRS_PATH = ROOT / "backend" / "data" / "fair_schedule.json"
ARTISTS_PATH = ROOT / "backend" / "data" / "artists.json"
INVENTORY_PATH = ROOT / "backend" / "data" / "inventory.json"
CONTEXT_PATH = ROOT / "context" / "sun_gallery_agent_context_v3.md"

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
TELEGRAM_API = "https://api.telegram.org/bot{token}"
POLL_TIMEOUT = 30  # long polling timeout (seconds)
TELEGRAM_MAX_LENGTH = 4096


# ---------------------------------------------------------------------------
# Data helpers
# ---------------------------------------------------------------------------

def load_json(path: Path) -> list[dict]:
    """Load JSON file, handling both list and dict-wrapped formats."""
    if not path.exists():
        return []
    raw = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(raw, list):
        return raw
    if isinstance(raw, dict):
        # Return first list value found
        for v in raw.values():
            if isinstance(v, list):
                return v
    return []


def load_context_filtered() -> str:
    """Load gallery context with Section 13 removed."""
    if not CONTEXT_PATH.exists():
        return ""
    content = CONTEXT_PATH.read_text(encoding="utf-8")
    pattern = r"## 13\. 내부 전략.*?(?=\n---|\Z)"
    return re.sub(pattern, "", content, flags=re.DOTALL)


def parse_fair_start_date(dates_str: str) -> date | None:
    """Parse fair start date from various formats."""
    if not dates_str:
        return None
    if "/" in dates_str and re.match(r"\d{4}-\d{2}-\d{2}", dates_str):
        try:
            return datetime.strptime(dates_str.split("/")[0], "%Y-%m-%d").date()
        except ValueError:
            pass
    if re.match(r"^\d{4}-\d{2}-\d{2}$", dates_str.strip()):
        try:
            return datetime.strptime(dates_str.strip(), "%Y-%m-%d").date()
        except ValueError:
            pass
    m = re.match(r"(\w+)\s+(\d+)(?:-\d+)?,\s*(\d{4})", dates_str)
    if m:
        try:
            return datetime.strptime(
                f"{m.group(1)} {m.group(2)}, {m.group(3)}", "%B %d, %Y"
            ).date()
        except ValueError:
            pass
    return None


# ---------------------------------------------------------------------------
# Claude API
# ---------------------------------------------------------------------------

MODE_SYSTEM_PROMPTS = {
    "email": (
        "You are drafting a professional email for Sun Gallery.\n"
        "- Always include a Subject line at the top.\n"
        "- Default sender: Joonwha Lee, Manager, Sun Gallery | Seoul, Korea\n"
        "- Adjust tone by recipient type. Be concise.\n"
        "- End with signature: Joonwha Lee / Manager / Sun Gallery | Seoul, Korea / "
        "sungallery1977@gmail.com / +82 2-734-0458"
    ),
    "whatsapp": (
        "You are composing a WhatsApp reply for Sun Gallery.\n"
        "- STRICTLY 3-5 sentences maximum.\n"
        "- Key info only (booth, artist, dates). Minimal emoji.\n"
        "- Encourage in-person meetings."
    ),
    "marketing": (
        "You are creating marketing content for Sun Gallery.\n"
        "- Use 'pioneering force' not 'longest-running'.\n"
        "- Gallery intro: 30-40 words English.\n"
        "- Never expose internal strategy."
    ),
    "document": (
        "You are generating a gallery document for Sun Gallery.\n"
        "- Types: Invoice, Condition Report, CoA, Sale Offer.\n"
        "- Default terms: buyer collection, payment first, no refunds, "
        "48h damage claims.\n"
        "- UAE: 5% customs + 5% VAT = 10.25% on CIF."
    ),
    "translate": (
        "You are an art translation assistant for Sun Gallery.\n"
        "- KR ↔ EN ↔ AR. 이정지 = Chungji Lee.\n"
        "- Arabic gallery name: معرض صن (Ma'rad San).\n"
        "- Maintain art terminology consistency."
    ),
    "fair": (
        "You are a fair preparation assistant for Sun Gallery.\n"
        "- Modes: before (checklist/outreach), after (follow-up), checklist.\n"
        "- Include booth numbers, artists, dates.\n"
        "- Never mention cost concerns externally."
    ),
    "general": (
        "You are Sun Gallery's AI assistant. Answer questions about the gallery, "
        "artists, exhibitions, fairs, and operations based on the provided context.\n"
        "- Mix Korean and English naturally (갤러리 실무 스타일).\n"
        "- Be concise and actionable.\n"
        "- Never reveal internal strategy (Section 13 content)."
    ),
}


def call_claude(mode: str, user_message: str) -> str:
    """Call Claude API with gallery context and mode-specific prompt."""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return "Error: ANTHROPIC_API_KEY가 설정되지 않았습니다."

    try:
        import anthropic
    except ImportError:
        return "Error: anthropic 패키지가 설치되지 않았습니다. pip install anthropic"

    context = load_context_filtered()
    mode_prompt = MODE_SYSTEM_PROMPTS.get(mode, MODE_SYSTEM_PROMPTS["general"])
    system_prompt = f"{context}\n\n---\n\n{mode_prompt}"

    try:
        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=2048,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
        )
        return response.content[0].text
    except Exception as e:
        return f"Claude API 오류: {e}"


# ---------------------------------------------------------------------------
# Command handlers
# ---------------------------------------------------------------------------

def cmd_start() -> str:
    return (
        "🎨 *Sun Gallery AI Assistant*\n"
        "선화랑 업무 도우미입니다.\n\n"
        "📌 *AI 콘텐츠 생성:*\n"
        "/email `<내용>` — 이메일 드래프트\n"
        "/whatsapp `<내용>` — WhatsApp 답장\n"
        "/marketing `<내용>` — 마케팅 콘텐츠\n"
        "/document `<내용>` — 문서 생성\n"
        "/translate `<내용>` — 미술 번역\n"
        "/fair `<내용>` — 페어 준비\n\n"
        "📬 *실제 이메일 연동 (네이버 웍스):*\n"
        "/inbox — 안 읽은 메일 확인\n"
        "/reply `<번호>` — AI 답장 생성\n"
        "/sendmail `<수신자> <제목> | <본문>` — 메일 발송\n\n"
        "💬 *WhatsApp 연동:*\n"
        "/wa `<전화번호> <메시지>` — WhatsApp 발송\n\n"
        "📊 *조회:*\n"
        "/collectors — 팔로업 필요 고객\n"
        "/fairs — 다가오는 페어 일정\n"
        "/scan — 데일리 스캔 즉시 실행\n\n"
        "💭 명령어 없이 메시지를 보내면 자유 질문으로 처리됩니다."
    )


def cmd_collectors() -> str:
    """List collectors needing follow-up."""
    collectors = load_json(COLLECTORS_PATH)
    today = date.today()
    followup_statuses = {"interested", "pending_followup", "vip"}
    overdue = []

    for c in collectors:
        status = (c.get("status") or "").lower()
        if status not in followup_statuses:
            continue
        last = c.get("last_contact")
        if not last:
            overdue.append((c, None))
            continue
        try:
            days = (today - datetime.strptime(last, "%Y-%m-%d").date()).days
        except ValueError:
            overdue.append((c, None))
            continue
        if days >= 7:
            overdue.append((c, days))

    if not overdue:
        return "✅ 팔로업 필요 고객이 없습니다."

    lines = [f"👤 *팔로업 필요 고객* ({len(overdue)}명)\n"]
    for c, days in overdue:
        days_str = f"{days}일 경과" if days else "날짜 미확인"
        interests = ", ".join(c.get("interests", [])) or "—"
        lines.append(
            f"• *{c['name']}* [{c.get('region', '')}] ({days_str})\n"
            f"  관심: {interests}"
        )
    return "\n".join(lines)


def cmd_fairs() -> str:
    """List upcoming fairs within 30 days."""
    fairs = load_json(FAIRS_PATH)
    today = date.today()
    upcoming = []

    for f in fairs:
        start = parse_fair_start_date(f.get("dates", ""))
        if not start:
            continue
        days_until = (start - today).days
        if 0 <= days_until <= 30:
            upcoming.append((f, days_until))

    if not upcoming:
        return "📅 30일 이내 예정된 페어가 없습니다."

    upcoming.sort(key=lambda x: x[1])
    lines = [f"🎪 *다가오는 페어* ({len(upcoming)}건)\n"]
    for f, days in upcoming:
        day_label = "🔴 TODAY" if days == 0 else f"D-{days}"
        booth = f.get("booth") or "TBD"
        artists = ", ".join(f.get("artists", []))
        title = f.get("exhibition_title")
        lines.append(f"• *{f['name']}* — {day_label}")
        lines.append(f"  Booth: {booth} | {f.get('dates', '')}")
        if title:
            lines.append(f"  \"{title}\"")
        if artists:
            lines.append(f"  작가: {artists}")
        lines.append("")
    return "\n".join(lines)


def cmd_scan() -> str:
    """Run daily scan immediately."""
    try:
        from daily_scan import find_overdue_collectors, find_upcoming_fairs, generate_summary_with_claude
        today = date.today()
        overdue = find_overdue_collectors(today)
        upcoming = find_upcoming_fairs(today)
        if not overdue and not upcoming:
            return f"📋 Daily Scan — {today}\n\n오늘은 특별한 액션 아이템이 없습니다. ✅"
        return generate_summary_with_claude(overdue, upcoming)
    except ImportError:
        # Fallback: inline scan
        collectors_msg = cmd_collectors()
        fairs_msg = cmd_fairs()
        return f"📋 *Daily Scan* — {date.today()}\n\n{collectors_msg}\n\n{fairs_msg}"


def cmd_mode(mode: str, text: str) -> str:
    """Handle mode-specific commands (email, whatsapp, etc.)."""
    if not text.strip():
        mode_names = {
            "email": "이메일", "whatsapp": "WhatsApp", "marketing": "마케팅",
            "document": "문서", "translate": "번역", "fair": "페어",
        }
        return f"사용법: /{mode} <요청 내용>\n\n예: /{mode} Ahmed에게 Art Central HK 초대 메시지"
    return call_claude(mode, text)


def cmd_general(text: str) -> str:
    """Handle free-form questions."""
    return call_claude("general", text)


# ---------------------------------------------------------------------------
# Email/WhatsApp integration commands
# ---------------------------------------------------------------------------

# Cache for inbox results (so /reply can reference them)
_inbox_cache: list = []


def cmd_inbox() -> str:
    """Check unread emails from Naver Works."""
    global _inbox_cache
    try:
        from naver_works_mail import NaverWorksMailReader
    except ImportError:
        return "Error: naver_works_mail 모듈을 찾을 수 없습니다."

    email_addr = os.getenv("NAVER_WORKS_EMAIL")
    password = os.getenv("NAVER_WORKS_PASSWORD")
    if not email_addr or not password:
        return (
            "⚠️ 네이버 웍스 메일이 설정되지 않았습니다.\n\n"
            "환경변수를 설정하세요:\n"
            "`NAVER_WORKS_EMAIL` — 이메일 주소\n"
            "`NAVER_WORKS_PASSWORD` — 외부 앱 비밀번호"
        )

    try:
        with NaverWorksMailReader(email_addr, password) as reader:
            emails = reader.fetch_unread(limit=5)
    except Exception as e:
        return f"메일 수신 오류: {e}"

    if not emails:
        return "📭 안 읽은 메일이 없습니다."

    _inbox_cache = emails
    lines = [f"📬 *안 읽은 메일* ({len(emails)}건)\n"]
    for i, e in enumerate(emails, 1):
        lines.append(
            f"*{i}.* {e.sender_name}\n"
            f"   제목: {e.subject}\n"
            f"   날짜: {e.date}\n"
            f"   내용: {e.body[:100]}...\n"
        )
    lines.append("💡 `/reply 1` 으로 AI 답장 생성")
    return "\n".join(lines)


def cmd_reply(text: str) -> str:
    """Generate AI reply for an inbox email and offer to send."""
    global _inbox_cache

    if not text.strip():
        return "사용법: /reply <번호>\n\n먼저 /inbox 로 메일을 확인하세요."

    try:
        idx = int(text.strip()) - 1
    except ValueError:
        return "번호를 입력하세요. 예: /reply 1"

    if not _inbox_cache:
        return "먼저 /inbox 로 메일을 확인하세요."

    if idx < 0 or idx >= len(_inbox_cache):
        return f"1~{len(_inbox_cache)} 사이 번호를 입력하세요."

    mail = _inbox_cache[idx]
    prompt = (
        f"다음 수신 메일에 대한 답장을 작성해줘.\n\n"
        f"보낸 사람: {mail.sender_name} <{mail.sender}>\n"
        f"제목: {mail.subject}\n"
        f"내용:\n{mail.body}\n\n"
        f"갤러리 매니저 Joonwha Lee로서 전문적이고 간결한 답장을 작성해줘. "
        f"Subject line을 포함해줘."
    )

    draft = call_claude("email", prompt)

    return (
        f"📧 *AI 답장 드래프트*\n"
        f"To: {mail.sender}\n"
        f"Re: {mail.subject}\n\n"
        f"---\n{draft}\n---\n\n"
        f"💡 발송하려면:\n"
        f"`/sendmail {mail.sender} Re: {mail.subject} | (위 내용 복사)`"
    )


def cmd_sendmail(text: str) -> str:
    """Send email via Naver Works SMTP."""
    if not text.strip():
        return (
            "사용법: /sendmail <수신자> <제목> | <본문>\n\n"
            "예: /sendmail ahmed@example.com Art Central Invitation | "
            "Dear Ahmed, we would like to invite you..."
        )

    try:
        from naver_works_mail import send_mail
    except ImportError:
        return "Error: naver_works_mail 모듈을 찾을 수 없습니다."

    email_addr = os.getenv("NAVER_WORKS_EMAIL")
    password = os.getenv("NAVER_WORKS_PASSWORD")
    if not email_addr or not password:
        return "⚠️ NAVER_WORKS_EMAIL, NAVER_WORKS_PASSWORD 환경변수를 설정하세요."

    # Parse: /sendmail to@email.com Subject Here | Body here
    if "|" not in text:
        return "형식: /sendmail <수신자> <제목> | <본문>\n`|` 로 제목과 본문을 구분하세요."

    header_part, body = text.split("|", 1)
    parts = header_part.strip().split(None, 1)
    if len(parts) < 2:
        return "수신자와 제목을 모두 입력하세요."

    to_addr = parts[0]
    subject = parts[1].strip()
    body = body.strip()

    try:
        send_mail(to_addr, subject, body)
        return f"✅ 메일 발송 완료!\n\nTo: {to_addr}\nSubject: {subject}"
    except Exception as e:
        return f"❌ 메일 발송 실패: {e}"


def cmd_wa(text: str) -> str:
    """Send WhatsApp message via Business API."""
    if not text.strip():
        return (
            "사용법: /wa <전화번호> <메시지>\n\n"
            "예: /wa +971501234567 Hello, this is Sun Gallery."
        )

    try:
        from whatsapp_api import send_whatsapp
    except ImportError:
        return "Error: whatsapp_api 모듈을 찾을 수 없습니다."

    token = os.getenv("WHATSAPP_TOKEN")
    phone_id = os.getenv("WHATSAPP_PHONE_ID")
    if not token or not phone_id:
        return (
            "⚠️ WhatsApp이 설정되지 않았습니다.\n\n"
            "환경변수를 설정하세요:\n"
            "`WHATSAPP_TOKEN` — Meta 액세스 토큰\n"
            "`WHATSAPP_PHONE_ID` — 전화번호 ID"
        )

    parts = text.strip().split(None, 1)
    if len(parts) < 2:
        return "전화번호와 메시지를 모두 입력하세요.\n예: /wa +971501234567 Hello"

    phone = parts[0]
    message = parts[1]

    try:
        result = send_whatsapp(phone, message)
        msg_id = result.get("messages", [{}])[0].get("id", "unknown")
        return f"✅ WhatsApp 발송 완료!\n\nTo: {phone}\nMessage ID: {msg_id}"
    except Exception as e:
        return f"❌ WhatsApp 발송 실패: {e}"


# ---------------------------------------------------------------------------
# Telegram Bot (Long Polling)
# ---------------------------------------------------------------------------

class TelegramBot:
    def __init__(self, token: str):
        self.token = token
        self.api_base = TELEGRAM_API.format(token=token)
        self.offset = 0

    def api(self, method: str, **params) -> dict:
        """Call Telegram Bot API."""
        resp = requests.post(f"{self.api_base}/{method}", json=params, timeout=POLL_TIMEOUT + 10)
        resp.raise_for_status()
        return resp.json()

    def send_message(self, chat_id: int, text: str, parse_mode: str = "Markdown") -> bool:
        """Send message, splitting if too long. Fallback to plain text on parse error."""
        chunks = self._split_message(text)
        for chunk in chunks:
            try:
                result = self.api("sendMessage", chat_id=chat_id, text=chunk, parse_mode=parse_mode)
                if not result.get("ok"):
                    # Markdown failed, retry plain
                    self.api("sendMessage", chat_id=chat_id, text=chunk)
            except Exception:
                try:
                    self.api("sendMessage", chat_id=chat_id, text=chunk)
                except Exception as e:
                    print(f"Failed to send message: {e}")
                    return False
        return True

    def _split_message(self, text: str) -> list[str]:
        """Split text into chunks within Telegram's limit."""
        if len(text) <= TELEGRAM_MAX_LENGTH:
            return [text]
        chunks = []
        while text:
            if len(text) <= TELEGRAM_MAX_LENGTH:
                chunks.append(text)
                break
            # Find last newline within limit
            cut = text.rfind("\n", 0, TELEGRAM_MAX_LENGTH)
            if cut == -1:
                cut = TELEGRAM_MAX_LENGTH
            chunks.append(text[:cut])
            text = text[cut:].lstrip("\n")
        return chunks

    def get_updates(self) -> list[dict]:
        """Long-poll for new messages."""
        try:
            result = self.api("getUpdates", offset=self.offset, timeout=POLL_TIMEOUT)
            updates = result.get("result", [])
            if updates:
                self.offset = updates[-1]["update_id"] + 1
            return updates
        except requests.exceptions.Timeout:
            return []
        except Exception as e:
            print(f"Polling error: {e}")
            time.sleep(5)
            return []

    def handle_message(self, message: dict):
        """Process incoming message and send response."""
        chat_id = message["chat"]["id"]
        text = message.get("text", "").strip()

        if not text:
            return

        user = message.get("from", {})
        username = user.get("first_name", "User")
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {username}: {text}")

        # Send "typing" indicator
        try:
            self.api("sendChatAction", chat_id=chat_id, action="typing")
        except Exception:
            pass

        # Route command
        response = self.route(text)

        print(f"[{datetime.now().strftime('%H:%M:%S')}] Bot: ({len(response)} chars)")
        self.send_message(chat_id, response)

    def route(self, text: str) -> str:
        """Route message to appropriate handler."""
        lower = text.lower()

        if lower == "/start" or lower == "/help":
            return cmd_start()
        if lower == "/collectors":
            return cmd_collectors()
        if lower == "/fairs":
            return cmd_fairs()
        if lower == "/scan":
            return cmd_scan()
        if lower == "/inbox":
            return cmd_inbox()
        if lower.startswith("/reply"):
            return cmd_reply(text[len("/reply"):].strip())
        if lower.startswith("/sendmail"):
            return cmd_sendmail(text[len("/sendmail"):].strip())
        if lower.startswith("/wa ") or lower == "/wa":
            return cmd_wa(text[len("/wa"):].strip())

        for mode in ("email", "whatsapp", "marketing", "document", "translate", "fair"):
            if lower.startswith(f"/{mode}"):
                body = text[len(f"/{mode}"):].strip()
                return cmd_mode(mode, body)

        # Free-form question
        return cmd_general(text)

    def run(self):
        """Start long-polling loop."""
        print("=" * 50)
        print("Sun Gallery Telegram Bot started")
        print(f"Polling for messages...")
        print("=" * 50)

        # Set bot commands for menu
        try:
            self.api("setMyCommands", commands=[
                {"command": "start", "description": "봇 소개 + 명령어 목록"},
                {"command": "inbox", "description": "안 읽은 메일 확인"},
                {"command": "reply", "description": "수신 메일에 AI 답장 생성"},
                {"command": "sendmail", "description": "메일 직접 발송"},
                {"command": "wa", "description": "WhatsApp 메시지 발송"},
                {"command": "email", "description": "이메일 드래프트 생성"},
                {"command": "whatsapp", "description": "WhatsApp 답장 생성"},
                {"command": "marketing", "description": "마케팅 콘텐츠 생성"},
                {"command": "document", "description": "갤러리 문서 생성"},
                {"command": "translate", "description": "미술 전문 번역"},
                {"command": "fair", "description": "페어 준비 도우미"},
                {"command": "collectors", "description": "팔로업 필요 고객 목록"},
                {"command": "fairs", "description": "다가오는 페어 일정"},
                {"command": "scan", "description": "데일리 스캔 즉시 실행"},
            ])
            print("Bot commands registered")
        except Exception as e:
            print(f"Warning: could not set commands: {e}")

        while True:
            updates = self.get_updates()
            for update in updates:
                msg = update.get("message")
                if msg:
                    try:
                        self.handle_message(msg)
                    except Exception as e:
                        print(f"Error handling message: {e}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        print("Error: TELEGRAM_BOT_TOKEN 환경변수를 설정하세요.")
        print("  export TELEGRAM_BOT_TOKEN=your-bot-token")
        return

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("Warning: ANTHROPIC_API_KEY 미설정 — Claude 기능이 동작하지 않습니다.")

    bot = TelegramBot(token)
    try:
        bot.run()
    except KeyboardInterrupt:
        print("\nBot stopped.")


if __name__ == "__main__":
    main()
