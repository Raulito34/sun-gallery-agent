"""
Sun Gallery — Agentic Telegram Bot

에이전틱 AI 어시스턴트: 능동적으로 업무를 찾고, 드래프트를 생성하고,
승인을 요청하고, 실행합니다.

기능:
  - Sun Gallery 업무 (이메일, WhatsApp, 마케팅, 번역, 페어)
  - Sun Art Center 대관 신청 실시간 감시 + 관리
  - SNS 마케팅 콘텐츠 자동 생성 + 큐 관리
  - 30분마다 능동 스캔 (collector followup, fair milestone, 대관, SNS)
  - Telegram 인라인 키보드로 승인/거절 워크플로

환경변수:
  ANTHROPIC_API_KEY    — Claude API 키 (필수)
  TELEGRAM_BOT_TOKEN   — Telegram Bot API 토큰 (필수)
  TELEGRAM_CHAT_ID     — 에이전트 알림 발송 대상 (필수)
  SAC_API_URL          — SAC Express 백엔드 URL (선택)
  SAC_ADMIN_CODE       — SAC 관리자 인증 코드 (선택)
  NAVER_WORKS_EMAIL    — 네이버 웍스 이메일 (선택)
  NAVER_WORKS_PASSWORD — 네이버 웍스 외부 앱 비밀번호 (선택)
  WHATSAPP_TOKEN       — WhatsApp Business API 토큰 (선택)
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
    "sac": (
        "You are Sun Art Center(선아트센터) AI assistant.\n"
        "SAC is a rental/invited exhibition space SEPARATE from Sun Gallery.\n"
        "- 대관전시: artists pay rental fee for exhibition space\n"
        "- 초대전시: emerging/experimental artists invited by SAC\n"
        "- ALWAYS use 'Sun Art Center' / '선아트센터', NEVER '선화랑' / 'Sun Gallery'\n"
        "- Tone: supportive, professional, encouraging to emerging artists\n"
        "- Location: 서울 종로구 인사동 (B1-4F, 5개 전시 공간)\n"
        "- Contact: sungallery1977@gmail.com / +82 2-734-0458\n"
        "- Sender: Joonwha Lee, Manager, Sun Art Center | Seoul, Korea"
    ),
    "sns": (
        "You are creating SNS (Instagram/X) content for Sun Art Center.\n"
        "- Create BOTH Korean and English versions\n"
        "- Use appropriate emojis\n"
        "- Include 10-15 hashtags\n"
        "- Instagram version: up to 2200 chars\n"
        "- X version: up to 280 chars\n"
        "- ALWAYS use 'Sun Art Center' branding, NEVER '선화랑'\n"
        "- Include AI image generation prompt in English (1 line)\n"
        "- Tone: contemporary art, culturally rich, inviting"
    ),
}


def call_claude(mode: str, user_message: str, brand: str = "sun_gallery") -> str:
    """Call Claude API with gallery context and mode-specific prompt.

    Args:
        mode: Prompt mode (email, sac, sns, general, etc.)
        user_message: User's request
        brand: "sun_gallery" or "sac" — controls branding in prompts
    """
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return "Error: ANTHROPIC_API_KEY가 설정되지 않았습니다."

    try:
        import anthropic
    except ImportError:
        return "Error: anthropic 패키지가 설치되지 않았습니다. pip install anthropic"

    context = load_context_filtered()
    mode_prompt = MODE_SYSTEM_PROMPTS.get(mode, MODE_SYSTEM_PROMPTS["general"])

    brand_note = ""
    if brand == "sac":
        brand_note = (
            "\n\nIMPORTANT: This is for Sun Art Center (선아트센터), "
            "NOT Sun Gallery (선화랑). Never mix the brands."
        )

    system_prompt = f"{context}\n\n---\n\n{mode_prompt}{brand_note}"

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
        "🏛 *Sun Art Center (대관):*\n"
        "/rentals — 전체 대관 신청\n"
        "/rental_pending — 대기 중 신청\n"
        "/rental_approve `<id>` — 대관 승인\n"
        "/exhibitions — SAC 전시 목록\n\n"
        "📱 *SNS 마케팅:*\n"
        "/sns — 마케팅 현황\n"
        "/sns_generate `<주제>` — 콘텐츠 생성\n"
        "/sns_queue — 콘텐츠 큐\n\n"
        "📊 *조회:*\n"
        "/collectors — 팔로업 필요 고객\n"
        "/fairs — 다가오는 페어 일정\n"
        "/scan — 데일리 스캔\n\n"
        "🤖 *Agent:*\n"
        "/agent — 에이전트 상태\n"
        "/pending — 승인 대기 목록\n"
        "/pause /resume — 자동 스캔 on/off\n\n"
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
# SAC Website commands
# ---------------------------------------------------------------------------

def _get_sac_client():
    try:
        from sac_website_api import get_sac_client
        client = get_sac_client()
        if not client.api_url:
            return None
        return client
    except ImportError:
        return None


def cmd_rentals() -> str:
    """List all rental applications from SAC website."""
    client = _get_sac_client()
    if not client:
        return "⚠️ SAC_API_URL 환경변수를 설정하세요."
    try:
        rentals = client.get_rentals()
    except Exception as e:
        return f"SAC API 오류: {e}"

    if not rentals:
        return "📋 대관 신청이 없습니다."

    by_status = {}
    for r in rentals:
        s = r.get("status", "unknown")
        by_status.setdefault(s, []).append(r)

    lines = [f"📋 *SAC 대관 신청* ({len(rentals)}건)\n"]
    status_emoji = {"pending": "🟡", "approved": "🟢", "rejected": "🔴", "cancelled": "⚫"}

    for status in ["pending", "approved", "rejected", "cancelled"]:
        items = by_status.get(status, [])
        if not items:
            continue
        emoji = status_emoji.get(status, "⚪")
        lines.append(f"\n{emoji} *{status.upper()}* ({len(items)}건)")
        for r in items:
            lines.append(
                f"  #{r['id']} {r.get('applicantName', '')} "
                f"| {r.get('spaceName', '')} "
                f"| {r.get('startDate', '')}~{r.get('endDate', '')}"
            )
    return "\n".join(lines)


def cmd_rental_pending() -> str:
    """List pending rental applications only."""
    client = _get_sac_client()
    if not client:
        return "⚠️ SAC_API_URL 환경변수를 설정하세요."
    try:
        rentals = client.get_rentals()
    except Exception as e:
        return f"SAC API 오류: {e}"

    pending = [r for r in rentals if r.get("status") == "pending"]
    if not pending:
        return "✅ 대기 중인 대관 신청이 없습니다."

    lines = [f"🟡 *대기 중 대관 신청* ({len(pending)}건)\n"]
    for r in pending:
        lines.append(
            f"*#{r['id']}* {r.get('applicantName', '')}\n"
            f"  공간: {r.get('spaceName', '')} | 기간: {r.get('startDate', '')}~{r.get('endDate', '')}\n"
            f"  목적: {r.get('purpose', '')}\n"
            f"  승인: `/rental_approve {r['id']}`  거절: `/rental_reject {r['id']}`\n"
        )
    return "\n".join(lines)


def cmd_rental_action(text: str, action: str) -> str:
    """Approve or reject a rental."""
    client = _get_sac_client()
    if not client:
        return "⚠️ SAC_API_URL 환경변수를 설정하세요."
    if not text.strip():
        return f"사용법: /rental_{action} <신청번호>"
    try:
        rental_id = int(text.strip())
    except ValueError:
        return "신청번호를 입력하세요."
    try:
        result = client.update_rental(rental_id, "approved" if action == "approve" else "rejected")
        emoji = "✅" if action == "approve" else "❌"
        return f"{emoji} 대관 신청 #{rental_id} {'승인' if action == 'approve' else '거절'} 완료!"
    except Exception as e:
        return f"오류: {e}"


def cmd_sac_exhibitions() -> str:
    """List SAC exhibitions."""
    client = _get_sac_client()
    if not client:
        return "⚠️ SAC_API_URL 환경변수를 설정하세요."
    try:
        exhibitions = client.get_exhibitions()
    except Exception as e:
        return f"SAC API 오류: {e}"

    if not exhibitions:
        return "🖼 현재 등록된 전시가 없습니다."

    lines = [f"🖼 *SAC 전시* ({len(exhibitions)}건)\n"]
    for ex in exhibitions:
        status_emoji = {"current": "🟢", "upcoming": "🔵", "past": "⚫"}.get(ex.get("status", ""), "⚪")
        lines.append(
            f"{status_emoji} *{ex.get('title', '')}* — {ex.get('artist', '')}\n"
            f"  {ex.get('floor', '')} | {ex.get('startDate', '')}~{ex.get('endDate', '')}"
        )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# SNS Marketing commands
# ---------------------------------------------------------------------------

def cmd_sns() -> str:
    """SNS marketing status overview."""
    try:
        from sns_marketing import get_queued, get_posted
    except ImportError:
        return "Error: sns_marketing 모듈을 찾을 수 없습니다."

    queued = get_queued()
    posted = get_posted()

    weekday_schedule = {0: "📅 월: 이번 주 전시 캘린더", 2: "🎨 수: 작가 스포트라이트", 4: "🏛 금: 공간 하이라이트"}
    today_wd = date.today().weekday()
    today_task = weekday_schedule.get(today_wd, "오늘은 정기 포스팅 없음")

    return (
        f"📱 *SNS 마케팅 현황*\n\n"
        f"대기 콘텐츠: {len(queued)}건\n"
        f"포스팅 완료: {len(posted)}건\n\n"
        f"*오늘의 스케줄:*\n{today_task}\n\n"
        f"*주간 스케줄:*\n"
        f"📅 월: 이번 주 전시 캘린더\n"
        f"🎨 수: 작가 스포트라이트\n"
        f"🏛 금: 공간 하이라이트\n\n"
        f"명령어:\n"
        f"`/sns_generate <주제>` — 콘텐츠 즉시 생성\n"
        f"`/sns_queue` — 대기 콘텐츠 목록\n"
    )


def cmd_sns_generate(text: str) -> str:
    """Generate SNS content on a given topic."""
    if not text.strip():
        return "사용법: /sns_generate <주제>\n\n예: /sns_generate 이번 주 전시 캘린더"
    return call_claude("sns", text, brand="sac")


def cmd_sns_queue() -> str:
    """List queued SNS content."""
    try:
        from sns_marketing import get_queued
    except ImportError:
        return "Error: sns_marketing 모듈을 찾을 수 없습니다."

    queued = get_queued()
    if not queued:
        return "📱 대기 중인 SNS 콘텐츠가 없습니다."

    lines = [f"📱 *SNS 콘텐츠 큐* ({len(queued)}건)\n"]
    for c in queued:
        lines.append(
            f"• *{c.get('id', '')}*\n"
            f"  유형: {c.get('type', '')} | 예정: {c.get('scheduled_date', 'TBD')}\n"
            f"  텍스트: {(c.get('instagram_text') or c.get('text_ko', ''))[:80]}...\n"
        )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Agent Loop — Proactive Scanning
# ---------------------------------------------------------------------------

class AgentLoop:
    """Proactive agent that scans for actionable items every SCAN_INTERVAL."""

    SCAN_INTERVAL = 1800  # 30 minutes

    def __init__(self):
        self.last_scan = 0.0
        self.paused = False

    def maybe_run_scan(self, bot: "TelegramBot"):
        """Run scan if interval has elapsed. Called from main polling loop."""
        if self.paused:
            return
        now = time.time()
        if now - self.last_scan < self.SCAN_INTERVAL:
            return
        self.last_scan = now
        try:
            self._run_scan(bot)
        except Exception as e:
            print(f"[AgentLoop] Scan error: {e}")

    def _run_scan(self, bot: "TelegramBot"):
        from agent_state import AgentState, make_task_id

        chat_id = os.getenv("TELEGRAM_CHAT_ID")
        if not chat_id:
            return
        chat_id = int(chat_id)

        state = AgentState()
        today = date.today()
        tasks_found = 0

        # --- Scan 1: Collector follow-ups ---
        tasks_found += self._scan_collector_followups(bot, state, today, chat_id)

        # --- Scan 2: Fair milestones ---
        tasks_found += self._scan_fair_milestones(bot, state, today, chat_id)

        # --- Scan 3: SAC new rentals ---
        tasks_found += self._scan_sac_rentals(bot, state, today, chat_id)

        # --- Scan 4: SNS marketing schedule ---
        tasks_found += self._scan_sns_schedule(bot, state, today, chat_id)

        state.update_scan_time()
        state.cleanup_old(days=7)
        state.save()

        if tasks_found:
            print(f"[AgentLoop] Scan complete: {tasks_found} new items")

    def _scan_collector_followups(self, bot, state, today, chat_id) -> int:
        from agent_state import make_task_id
        collectors = load_json(COLLECTORS_PATH)
        count = 0
        followup_statuses = {"interested", "pending_followup", "vip"}

        for c in collectors:
            status = (c.get("status") or "").lower()
            if status not in followup_statuses:
                continue
            last = c.get("last_contact")
            if not last:
                continue
            try:
                days = (today - datetime.strptime(last, "%Y-%m-%d").date()).days
            except ValueError:
                continue
            if days < 7:
                continue

            task_id = make_task_id("followup", c["name"], today.isoformat())
            if state.was_acted_on(task_id):
                continue

            interests = ", ".join(c.get("interests", []))
            draft = call_claude("email", (
                f"Write a follow-up email to collector {c['name']} ({c.get('region', '')}).\n"
                f"Interests: {interests}\n"
                f"Last contact: {last} ({days} days ago)\n"
                f"Be warm and reference their interests."
            ))

            msg = (
                f"👤 *팔로업 필요*\n\n"
                f"*{c['name']}* [{c.get('region', '')}]\n"
                f"관심: {interests}\n"
                f"마지막 연락: {last} ({days}일 전)\n\n"
                f"---\n{draft[:1500]}\n---"
            )
            bot.send_with_keyboard(chat_id, msg, task_id)
            state.add_pending(task_id, "collector_followup", draft, "email", metadata={"collector": c["name"]})
            count += 1
        return count

    def _scan_fair_milestones(self, bot, state, today, chat_id) -> int:
        from agent_state import make_task_id
        fairs = load_json(FAIRS_PATH)
        count = 0

        for f in fairs:
            start = parse_fair_start_date(f.get("dates", ""))
            if not start:
                continue
            days_until = (start - today).days
            if days_until not in (14, 7, 3, 1):
                continue

            task_id = make_task_id(f"fair_d{days_until}", f["name"], today.isoformat())
            if state.was_acted_on(task_id):
                continue

            milestone = {14: "2주 전", 7: "1주 전", 3: "3일 전", 1: "내일"}[days_until]
            booth = f.get("booth", "TBD")
            artists = ", ".join(f.get("artists", []))

            msg = (
                f"🎪 *페어 D-{days_until}* ({milestone})\n\n"
                f"*{f['name']}*\n"
                f"Booth: {booth} | {f.get('dates', '')}\n"
                f"작가: {artists}\n"
            )
            bot.send_message(chat_id, msg)
            state.mark_acted(task_id, f"fair_milestone_d{days_until}")
            count += 1
        return count

    def _scan_sac_rentals(self, bot, state, today, chat_id) -> int:
        from agent_state import make_task_id
        client = _get_sac_client()
        if not client:
            return 0

        try:
            rentals = client.get_rentals()
        except Exception:
            return 0

        count = 0
        for r in rentals:
            if r.get("status") != "pending":
                continue
            task_id = make_task_id("rental", str(r["id"]), today.isoformat())
            if state.was_acted_on(task_id):
                continue

            summary = call_claude("sac", (
                f"새 대관 신청을 검토해줘:\n"
                f"신청자: {r.get('applicantName', '')} ({r.get('organization', '')})\n"
                f"공간: {r.get('spaceName', '')}\n"
                f"기간: {r.get('startDate', '')} ~ {r.get('endDate', '')}\n"
                f"목적: {r.get('purpose', '')}\n"
                f"메시지: {r.get('message', '')}\n\n"
                f"일정 충돌 여부, 추천 의견을 간단히 한국어로 작성해줘."
            ), brand="sac")

            msg = (
                f"📋 *새 대관 신청*\n\n"
                f"신청자: {r.get('applicantName', '')}\n"
                f"소속: {r.get('organization', '') or '개인'}\n"
                f"공간: {r.get('spaceName', '')} | "
                f"기간: {r.get('startDate', '')}~{r.get('endDate', '')}\n"
                f"목적: {r.get('purpose', '')}\n\n"
                f"💡 *AI 검토:*\n{summary[:800]}"
            )
            bot.send_with_keyboard(
                chat_id, msg, task_id,
                buttons=[
                    ("✅ 승인", f"rental_approve:{r['id']}"),
                    ("❌ 거절", f"rental_reject:{r['id']}"),
                ],
            )
            state.add_pending(task_id, "rental_review", summary, metadata={"rental_id": r["id"]})
            count += 1
        return count

    def _scan_sns_schedule(self, bot, state, today, chat_id) -> int:
        from agent_state import make_task_id
        weekday = today.weekday()
        if weekday not in (0, 2, 4):  # 월, 수, 금
            return 0

        task_id = make_task_id("sns", str(weekday), today.isoformat())
        if state.was_acted_on(task_id):
            return 0

        # Get exhibitions from SAC API for content
        client = _get_sac_client()
        exhibitions = []
        if client:
            try:
                exhibitions = client.get_exhibitions("current")
            except Exception:
                pass

        if weekday == 0:
            content_type = "weekly_calendar"
            if exhibitions:
                from sns_marketing import build_weekly_calendar_prompt
                prompt = build_weekly_calendar_prompt(exhibitions)
            else:
                prompt = "이번 주 Sun Art Center 전시 캘린더 포스트를 작성해줘. 현재 전시 정보가 없으면 공간 소개 중심으로."
        elif weekday == 2:
            content_type = "artist_spotlight"
            if exhibitions:
                from sns_marketing import build_artist_spotlight_prompt
                prompt = build_artist_spotlight_prompt(exhibitions[0])
            else:
                prompt = "Sun Art Center의 신진 작가 지원 프로그램을 소개하는 포스트를 작성해줘."
        else:  # 금
            content_type = "space_highlight"
            spaces = []
            if client:
                try:
                    spaces = client.get_spaces()
                except Exception:
                    pass
            if spaces:
                from sns_marketing import build_space_highlight_prompt
                import random
                prompt = build_space_highlight_prompt(random.choice(spaces))
            else:
                prompt = "Sun Art Center의 인사동 전시 공간을 소개하는 포스트를 작성해줘. B1-4F 5개 층."

        draft = call_claude("sns", prompt, brand="sac")

        msg = (
            f"📱 *SNS 콘텐츠 미리보기*\n"
            f"유형: {content_type}\n\n"
            f"---\n{draft[:2000]}\n---"
        )
        bot.send_with_keyboard(
            chat_id, msg, task_id,
            buttons=[
                ("✅ 승인 & 큐 추가", f"sns_approve:{task_id}"),
                ("❌ 건너뛰기", f"dismiss:{task_id}"),
            ],
        )
        state.add_pending(task_id, "sns_content", draft, metadata={"content_type": content_type})
        return 1


# ---------------------------------------------------------------------------
# Agent status commands
# ---------------------------------------------------------------------------

def cmd_agent_status() -> str:
    """Show agent loop status."""
    try:
        from agent_state import AgentState
    except ImportError:
        return "Error: agent_state 모듈을 찾을 수 없습니다."

    state = AgentState()
    pending = state.list_pending()
    last = state.last_scan or "아직 스캔 안 함"

    return (
        f"🤖 *Agent 상태*\n\n"
        f"마지막 스캔: {last}\n"
        f"승인 대기: {len(pending)}건\n"
        f"처리 완료: {len(state._state.get('acted_items', []))}건\n"
        f"거절: {len(state._state.get('dismissed_items', []))}건"
    )


def cmd_pending() -> str:
    """List pending approvals."""
    try:
        from agent_state import AgentState
    except ImportError:
        return "Error: agent_state 모듈을 찾을 수 없습니다."

    state = AgentState()
    pending = state.list_pending()
    if not pending:
        return "✅ 승인 대기 항목이 없습니다."

    lines = [f"⏳ *승인 대기* ({len(pending)}건)\n"]
    for p in pending:
        lines.append(
            f"• `{p['id']}`\n"
            f"  유형: {p['type']} | 생성: {p.get('created_at', '')[:10]}\n"
        )
    lines.append("\n`/approve <id>` 또는 `/dismiss <id>`로 처리")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Telegram Bot (Long Polling)
# ---------------------------------------------------------------------------

class TelegramBot:
    def __init__(self, token: str):
        self.token = token
        self.api_base = TELEGRAM_API.format(token=token)
        self.offset = 0
        self.agent = AgentLoop()

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

    def send_with_keyboard(
        self, chat_id: int, text: str, task_id: str,
        buttons: list[tuple[str, str]] | None = None,
    ) -> int | None:
        """Send message with inline keyboard buttons. Returns message_id."""
        if buttons is None:
            buttons = [
                ("✅ 승인 & 발송", f"approve:{task_id}"),
                ("❌ 거절", f"dismiss:{task_id}"),
            ]

        keyboard = {
            "inline_keyboard": [
                [{"text": label, "callback_data": data} for label, data in buttons]
            ]
        }

        chunks = self._split_message(text)
        msg_id = None
        for i, chunk in enumerate(chunks):
            params = {"chat_id": chat_id, "text": chunk}
            # Attach keyboard only to last chunk
            if i == len(chunks) - 1:
                params["reply_markup"] = keyboard
            try:
                result = self.api("sendMessage", **params)
                if result.get("ok"):
                    msg_id = result["result"]["message_id"]
            except Exception:
                try:
                    result = self.api("sendMessage", chat_id=chat_id, text=chunk)
                    if result.get("ok"):
                        msg_id = result["result"]["message_id"]
                except Exception as e:
                    print(f"Failed to send keyboard message: {e}")
        return msg_id

    def handle_callback(self, callback: dict):
        """Process inline keyboard button clicks."""
        cb_id = callback.get("id", "")
        data = callback.get("data", "")
        chat_id = callback.get("message", {}).get("chat", {}).get("id")
        msg_id = callback.get("message", {}).get("message_id")

        if not data or not chat_id:
            return

        print(f"[{datetime.now().strftime('%H:%M:%S')}] Callback: {data}")

        # Answer callback to remove loading indicator
        try:
            self.api("answerCallbackQuery", callback_query_id=cb_id)
        except Exception:
            pass

        # Parse callback data
        if ":" in data:
            action, payload = data.split(":", 1)
        else:
            action, payload = data, ""

        if action == "approve":
            self._handle_approve(chat_id, msg_id, payload)
        elif action == "dismiss":
            self._handle_dismiss(chat_id, msg_id, payload)
        elif action == "rental_approve":
            self._handle_rental_action(chat_id, msg_id, payload, "approved")
        elif action == "rental_reject":
            self._handle_rental_action(chat_id, msg_id, payload, "rejected")
        elif action == "sns_approve":
            self._handle_sns_approve(chat_id, msg_id, payload)

    def _handle_approve(self, chat_id, msg_id, task_id):
        from agent_state import AgentState
        state = AgentState()
        pending = state.get_pending(task_id)
        if not pending:
            self.send_message(chat_id, "⚠️ 이 항목은 이미 처리되었거나 만료되었습니다.")
            return

        state.approve(task_id)
        state.save()

        # Edit original message to show approved
        try:
            self.api("editMessageReplyMarkup", chat_id=chat_id, message_id=msg_id, reply_markup={"inline_keyboard": []})
        except Exception:
            pass

        self.send_message(chat_id, f"✅ 승인 완료: `{task_id}`")

    def _handle_dismiss(self, chat_id, msg_id, task_id):
        from agent_state import AgentState
        state = AgentState()
        state.dismiss(task_id)
        state.save()

        try:
            self.api("editMessageReplyMarkup", chat_id=chat_id, message_id=msg_id, reply_markup={"inline_keyboard": []})
        except Exception:
            pass

        self.send_message(chat_id, f"❌ 거절됨: `{task_id}`")

    def _handle_rental_action(self, chat_id, msg_id, rental_id_str, status):
        client = _get_sac_client()
        if not client:
            self.send_message(chat_id, "⚠️ SAC API 연결 실패")
            return

        try:
            rental_id = int(rental_id_str)
            client.update_rental(rental_id, status)
        except Exception as e:
            self.send_message(chat_id, f"오류: {e}")
            return

        try:
            self.api("editMessageReplyMarkup", chat_id=chat_id, message_id=msg_id, reply_markup={"inline_keyboard": []})
        except Exception:
            pass

        emoji = "✅" if status == "approved" else "❌"
        label = "승인" if status == "approved" else "거절"
        self.send_message(chat_id, f"{emoji} 대관 #{rental_id} {label} 완료!")

        # If approved, offer to generate approval email
        if status == "approved":
            try:
                rentals = client.get_rentals()
                rental = next((r for r in rentals if r["id"] == rental_id), None)
                if rental and rental.get("email"):
                    draft = call_claude("sac", (
                        f"대관 승인 이메일을 작성해줘.\n"
                        f"수신자: {rental.get('applicantName', '')} <{rental['email']}>\n"
                        f"공간: {rental.get('spaceName', '')}\n"
                        f"기간: {rental.get('startDate', '')} ~ {rental.get('endDate', '')}\n"
                        f"Sun Art Center 매니저 Joonwha Lee 이름으로."
                    ), brand="sac")
                    self.send_message(chat_id, f"📧 *승인 이메일 드래프트*\n\n{draft[:2000]}")
            except Exception:
                pass

    def _handle_sns_approve(self, chat_id, msg_id, task_id):
        from agent_state import AgentState
        state = AgentState()
        pending = state.get_pending(task_id)
        if not pending:
            self.send_message(chat_id, "⚠️ 이 항목은 이미 처리되었습니다.")
            return

        # Add to SNS queue
        try:
            from sns_marketing import add_to_queue, make_content_id, parse_sns_response
            parsed = parse_sns_response(pending.get("draft", ""))
            content = {
                "id": make_content_id(pending.get("metadata", {}).get("content_type", "post")),
                "type": pending.get("metadata", {}).get("content_type", "post"),
                "platform": ["instagram", "x"],
                "instagram_text": parsed["instagram_text"],
                "x_text": parsed["x_text"],
                "hashtags": parsed["hashtags"],
                "image_prompt": parsed["image_prompt"],
                "image_url": None,
                "status": "queued",
                "scheduled_date": date.today().isoformat(),
            }
            add_to_queue(content)
        except Exception as e:
            self.send_message(chat_id, f"큐 추가 오류: {e}")
            return

        state.approve(task_id)
        state.save()

        try:
            self.api("editMessageReplyMarkup", chat_id=chat_id, message_id=msg_id, reply_markup={"inline_keyboard": []})
        except Exception:
            pass

        self.send_message(
            chat_id,
            f"✅ SNS 콘텐츠 큐에 추가됨!\n\n"
            f"📸 이미지가 필요하면 보내주세요.\n"
            f"이미지 프롬프트: {parsed.get('image_prompt', 'N/A')[:200]}"
        )

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

        # --- SAC Website ---
        if lower == "/rentals":
            return cmd_rentals()
        if lower == "/rental_pending":
            return cmd_rental_pending()
        if lower.startswith("/rental_approve"):
            return cmd_rental_action(text[len("/rental_approve"):].strip(), "approve")
        if lower.startswith("/rental_reject"):
            return cmd_rental_action(text[len("/rental_reject"):].strip(), "reject")
        if lower == "/exhibitions":
            return cmd_sac_exhibitions()

        # --- SNS Marketing ---
        if lower == "/sns":
            return cmd_sns()
        if lower.startswith("/sns_generate"):
            return cmd_sns_generate(text[len("/sns_generate"):].strip())
        if lower == "/sns_queue":
            return cmd_sns_queue()

        # --- Agent ---
        if lower == "/agent":
            return cmd_agent_status()
        if lower == "/pending":
            return cmd_pending()
        if lower.startswith("/approve"):
            task_id = text[len("/approve"):].strip()
            if task_id:
                from agent_state import AgentState
                state = AgentState()
                result = state.approve(task_id)
                state.save()
                return f"✅ 승인: `{task_id}`" if result else f"⚠️ `{task_id}` 를 찾을 수 없습니다."
            return "사용법: /approve <task_id>"
        if lower.startswith("/dismiss"):
            task_id = text[len("/dismiss"):].strip()
            if task_id:
                from agent_state import AgentState
                state = AgentState()
                state.dismiss(task_id)
                state.save()
                return f"❌ 거절: `{task_id}`"
            return "사용법: /dismiss <task_id>"
        if lower == "/pause":
            self.agent.paused = True
            return "⏸ Agent 스캔 일시정지됨. `/resume`으로 재개."
        if lower == "/resume":
            self.agent.paused = False
            return "▶️ Agent 스캔 재개됨."

        # --- Existing commands ---
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
                {"command": "rentals", "description": "SAC 대관 신청 목록"},
                {"command": "rental_pending", "description": "대기 중 대관 신청"},
                {"command": "exhibitions", "description": "SAC 전시 목록"},
                {"command": "sns", "description": "SNS 마케팅 현황"},
                {"command": "sns_generate", "description": "SNS 콘텐츠 생성"},
                {"command": "sns_queue", "description": "SNS 콘텐츠 큐"},
                {"command": "agent", "description": "에이전트 상태"},
                {"command": "pending", "description": "승인 대기 목록"},
                {"command": "inbox", "description": "안 읽은 메일 확인"},
                {"command": "email", "description": "이메일 드래프트 생성"},
                {"command": "collectors", "description": "팔로업 필요 고객"},
                {"command": "fairs", "description": "다가오는 페어 일정"},
                {"command": "scan", "description": "데일리 스캔"},
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
                cb = update.get("callback_query")
                if cb:
                    try:
                        self.handle_callback(cb)
                    except Exception as e:
                        print(f"Error handling callback: {e}")

            # Proactive agent scan (every 30 minutes)
            self.agent.maybe_run_scan(self)


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
