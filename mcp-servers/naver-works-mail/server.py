#!/usr/bin/env python3
"""
Naver Works Mail MCP Server

Claude Code에서 직접 네이버 웍스 이메일을 읽고 보낼 수 있는 MCP 서버.

Tools:
  - check_inbox: 안 읽은 메일 확인
  - read_email: 특정 메일 상세 읽기
  - search_email: 키워드로 메일 검색
  - send_email: 이메일 발송
  - reply_email: 수신 메일에 답장
  - list_recent: 최근 메일 목록

환경변수:
  NAVER_WORKS_EMAIL    — 네이버 웍스 이메일 주소
  NAVER_WORKS_PASSWORD — 외부 앱 비밀번호
"""

import email
import email.header
import email.utils
import imaplib
import json
import os
import smtplib
import sys
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from html.parser import HTMLParser

IMAP_SERVER = "imap.worksmobile.com"
IMAP_PORT = 993
SMTP_SERVER = "smtp.worksmobile.com"
SMTP_PORT = 587

# ---------------------------------------------------------------------------
# Email helpers (from naver_works_mail.py, inlined for standalone MCP)
# ---------------------------------------------------------------------------

class _HTMLStripper(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []
        self._skip = False
    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"): self._skip = True
        elif tag in ("br", "p", "div", "li", "tr"): self.parts.append("\n")
    def handle_endtag(self, tag):
        if tag in ("script", "style"): self._skip = False
    def handle_data(self, data):
        if not self._skip: self.parts.append(data)
    def get_text(self): return "".join(self.parts).strip()

def html_to_text(html):
    s = _HTMLStripper(); s.feed(html); return s.get_text()

def decode_header_value(raw):
    if not raw: return ""
    parts = email.header.decode_header(raw)
    decoded = []
    for data, charset in parts:
        if isinstance(data, bytes):
            decoded.append(data.decode(charset or "utf-8", errors="replace"))
        else:
            decoded.append(data)
    return " ".join(decoded)

def extract_body(msg):
    if msg.is_multipart():
        text_part = html_part = None
        for part in msg.walk():
            ct = part.get_content_type()
            if ct == "text/plain" and not text_part: text_part = part
            elif ct == "text/html" and not html_part: html_part = part
        target = text_part or html_part
        if target:
            payload = target.get_payload(decode=True)
            charset = target.get_content_charset() or "utf-8"
            text = payload.decode(charset, errors="replace")
            return html_to_text(text) if target.get_content_type() == "text/html" else text
        return ""
    payload = msg.get_payload(decode=True)
    if not payload: return ""
    charset = msg.get_content_charset() or "utf-8"
    text = payload.decode(charset, errors="replace")
    return html_to_text(text) if msg.get_content_type() == "text/html" else text

def parse_email(raw_bytes):
    msg = email.message_from_bytes(raw_bytes)
    sender_raw = msg.get("From", "")
    sender_name, sender_addr = email.utils.parseaddr(sender_raw)
    return {
        "sender": sender_addr,
        "sender_name": decode_header_value(sender_name) or sender_addr,
        "subject": decode_header_value(msg.get("Subject", "")),
        "date": msg.get("Date", ""),
        "to": decode_header_value(msg.get("To", "")),
        "cc": decode_header_value(msg.get("Cc", "")),
        "body": extract_body(msg)[:5000],
    }

# ---------------------------------------------------------------------------
# MCP Tool implementations
# ---------------------------------------------------------------------------

def tool_check_inbox(limit=10):
    """안 읽은 메일을 확인합니다."""
    conn = imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT)
    conn.login(os.environ["NAVER_WORKS_EMAIL"], os.environ["NAVER_WORKS_PASSWORD"])
    conn.select("INBOX", readonly=True)
    _, data = conn.search(None, "UNSEEN")
    uids = data[0].split()
    if not uids:
        conn.logout()
        return {"count": 0, "emails": [], "message": "안 읽은 메일이 없습니다."}

    uids = uids[-limit:]
    emails = []
    for uid in uids:
        _, msg_data = conn.fetch(uid, "(RFC822)")
        if msg_data and msg_data[0]:
            parsed = parse_email(msg_data[0][1])
            parsed["uid"] = uid.decode()
            parsed["body"] = parsed["body"][:500] + "..." if len(parsed["body"]) > 500 else parsed["body"]
            emails.append(parsed)
    conn.logout()
    return {"count": len(emails), "emails": emails}


def tool_read_email(uid):
    """특정 메일의 전체 내용을 읽습니다."""
    conn = imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT)
    conn.login(os.environ["NAVER_WORKS_EMAIL"], os.environ["NAVER_WORKS_PASSWORD"])
    conn.select("INBOX", readonly=True)
    _, msg_data = conn.fetch(str(uid).encode(), "(RFC822)")
    conn.logout()
    if not msg_data or not msg_data[0]:
        return {"error": f"메일 UID {uid}를 찾을 수 없습니다."}
    parsed = parse_email(msg_data[0][1])
    parsed["uid"] = str(uid)
    return parsed


def tool_search_email(keyword, limit=10):
    """키워드로 메일을 검색합니다."""
    conn = imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT)
    conn.login(os.environ["NAVER_WORKS_EMAIL"], os.environ["NAVER_WORKS_PASSWORD"])
    conn.select("INBOX", readonly=True)
    _, data = conn.search(None, f'(OR SUBJECT "{keyword}" FROM "{keyword}")')
    uids = data[0].split()
    if not uids:
        conn.logout()
        return {"count": 0, "emails": [], "message": f"'{keyword}' 검색 결과 없음."}

    uids = uids[-limit:]
    emails = []
    for uid in uids:
        _, msg_data = conn.fetch(uid, "(RFC822)")
        if msg_data and msg_data[0]:
            parsed = parse_email(msg_data[0][1])
            parsed["uid"] = uid.decode()
            parsed["body"] = parsed["body"][:300] + "..."
            emails.append(parsed)
    conn.logout()
    return {"count": len(emails), "emails": emails}


def tool_list_recent(limit=10):
    """최근 메일을 시간순으로 보여줍니다."""
    conn = imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT)
    conn.login(os.environ["NAVER_WORKS_EMAIL"], os.environ["NAVER_WORKS_PASSWORD"])
    conn.select("INBOX", readonly=True)
    _, data = conn.search(None, "ALL")
    uids = data[0].split()
    if not uids:
        conn.logout()
        return {"count": 0, "emails": []}

    uids = uids[-limit:]
    emails = []
    for uid in uids:
        _, msg_data = conn.fetch(uid, "(RFC822 FLAGS)")
        if msg_data and msg_data[0]:
            parsed = parse_email(msg_data[0][1])
            parsed["uid"] = uid.decode()
            flag_data = msg_data[0][0].decode() if isinstance(msg_data[0][0], bytes) else ""
            parsed["is_read"] = "\\Seen" in flag_data
            parsed["body"] = parsed["body"][:200] + "..."
            emails.append(parsed)
    conn.logout()
    return {"count": len(emails), "emails": emails}


def tool_send_email(to, subject, body, cc=""):
    """이메일을 발송합니다."""
    addr = os.environ["NAVER_WORKS_EMAIL"]
    pwd = os.environ["NAVER_WORKS_PASSWORD"]

    msg = MIMEMultipart("alternative")
    msg["From"] = f"Joonwha Lee <{addr}>"
    msg["To"] = to
    msg["Subject"] = subject
    if cc:
        msg["Cc"] = cc
    msg.attach(MIMEText(body, "plain", "utf-8"))

    recipients = [to]
    if cc:
        recipients.extend(r.strip() for r in cc.split(","))

    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
        server.starttls()
        server.login(addr, pwd)
        server.sendmail(addr, recipients, msg.as_string())

    return {"success": True, "to": to, "subject": subject, "message": "발송 완료!"}


def tool_reply_email(uid, body):
    """수신 메일에 답장합니다."""
    # First read the original
    original = tool_read_email(uid)
    if "error" in original:
        return original

    to = original["sender"]
    subject = f"Re: {original['subject']}"
    return tool_send_email(to, subject, body)


# ---------------------------------------------------------------------------
# MCP Protocol (JSON-RPC over stdio)
# ---------------------------------------------------------------------------

TOOLS = [
    {
        "name": "check_inbox",
        "description": "안 읽은 메일을 확인합니다. 새 메일이 있는지, 누구에게서 왔는지, 제목이 무엇인지 보여줍니다.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "description": "확인할 최대 메일 수 (기본: 10)", "default": 10}
            },
        },
    },
    {
        "name": "read_email",
        "description": "특정 메일의 전체 내용을 읽습니다. UID로 식별합니다.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "uid": {"type": "string", "description": "메일 UID (check_inbox에서 확인)"}
            },
            "required": ["uid"],
        },
    },
    {
        "name": "search_email",
        "description": "보낸 사람 이름/주소 또는 제목 키워드로 메일을 검색합니다.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "keyword": {"type": "string", "description": "검색 키워드 (이름, 이메일, 제목)"},
                "limit": {"type": "integer", "description": "최대 결과 수", "default": 10}
            },
            "required": ["keyword"],
        },
    },
    {
        "name": "list_recent",
        "description": "최근 메일을 시간순으로 보여줍니다. 읽음/안읽음 상태 포함.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "description": "확인할 최대 메일 수", "default": 10}
            },
        },
    },
    {
        "name": "send_email",
        "description": "이메일을 발송합니다. Sun Gallery 매니저 Joonwha Lee 이름으로 보냅니다.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "to": {"type": "string", "description": "수신자 이메일 주소"},
                "subject": {"type": "string", "description": "제목"},
                "body": {"type": "string", "description": "본문"},
                "cc": {"type": "string", "description": "참조 (선택)", "default": ""}
            },
            "required": ["to", "subject", "body"],
        },
    },
    {
        "name": "reply_email",
        "description": "수신 메일에 답장합니다. 원본 메일의 UID와 답장 본문을 입력합니다.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "uid": {"type": "string", "description": "답장할 메일 UID"},
                "body": {"type": "string", "description": "답장 본문"}
            },
            "required": ["uid", "body"],
        },
    },
]

TOOL_HANDLERS = {
    "check_inbox": lambda args: tool_check_inbox(args.get("limit", 10)),
    "read_email": lambda args: tool_read_email(args["uid"]),
    "search_email": lambda args: tool_search_email(args["keyword"], args.get("limit", 10)),
    "list_recent": lambda args: tool_list_recent(args.get("limit", 10)),
    "send_email": lambda args: tool_send_email(args["to"], args["subject"], args["body"], args.get("cc", "")),
    "reply_email": lambda args: tool_reply_email(args["uid"], args["body"]),
}


def handle_request(request):
    method = request.get("method", "")
    req_id = request.get("id")

    if method == "initialize":
        return {
            "jsonrpc": "2.0", "id": req_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "naver-works-mail", "version": "1.0.0"},
            },
        }

    if method == "notifications/initialized":
        return None  # No response for notifications

    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": req_id, "result": {"tools": TOOLS}}

    if method == "tools/call":
        tool_name = request.get("params", {}).get("name", "")
        arguments = request.get("params", {}).get("arguments", {})
        handler = TOOL_HANDLERS.get(tool_name)

        if not handler:
            return {
                "jsonrpc": "2.0", "id": req_id,
                "result": {"content": [{"type": "text", "text": f"Unknown tool: {tool_name}"}], "isError": True},
            }

        # Check env vars
        if not os.environ.get("NAVER_WORKS_EMAIL") or not os.environ.get("NAVER_WORKS_PASSWORD"):
            return {
                "jsonrpc": "2.0", "id": req_id,
                "result": {
                    "content": [{"type": "text", "text": "NAVER_WORKS_EMAIL, NAVER_WORKS_PASSWORD 환경변수를 설정하세요."}],
                    "isError": True,
                },
            }

        try:
            result = handler(arguments)
            return {
                "jsonrpc": "2.0", "id": req_id,
                "result": {"content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False, indent=2)}]},
            }
        except Exception as e:
            return {
                "jsonrpc": "2.0", "id": req_id,
                "result": {"content": [{"type": "text", "text": f"Error: {e}"}], "isError": True},
            }

    return {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32601, "message": f"Unknown method: {method}"}}


def main():
    """MCP stdio server loop."""
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            request = json.loads(line)
        except json.JSONDecodeError:
            continue

        response = handle_request(request)
        if response:
            sys.stdout.write(json.dumps(response) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
