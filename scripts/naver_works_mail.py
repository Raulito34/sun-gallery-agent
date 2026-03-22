"""
Sun Gallery — Naver Works Mail Integration

네이버 웍스(LINE WORKS) 메일 수신/발신 모듈.
IMAP으로 새 메일을 읽고, SMTP로 메일을 보냅니다.

환경변수:
  NAVER_WORKS_EMAIL    — 네이버 웍스 이메일 (예: joonwha@sungallery.com)
  NAVER_WORKS_PASSWORD — 외부 앱 비밀번호 (네이버 웍스 설정 > 보안 > 외부 앱 비밀번호)

네이버 웍스 관리자 설정 필요:
  1. 관리자 > 보안 > 서비스 권한 > 메일 > IMAP/SMTP 사용 허용
  2. 사용자 > 설정 > 보안 > 외부 앱 비밀번호 생성
  3. Standard 또는 Standard Plus 요금제 필요
"""

import email
import email.header
import email.utils
import imaplib
import os
import smtplib
from dataclasses import dataclass, field
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from html.parser import HTMLParser
from typing import Optional

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
IMAP_SERVER = "imap.worksmobile.com"
IMAP_PORT = 993
SMTP_SERVER = "smtp.worksmobile.com"
SMTP_PORT = 587

# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class IncomingEmail:
    """Parsed incoming email."""
    uid: str
    sender: str
    sender_name: str
    subject: str
    body: str
    date: str
    to: str = ""
    cc: str = ""
    is_read: bool = False


@dataclass
class OutgoingEmail:
    """Email to be sent."""
    to: str
    subject: str
    body: str
    cc: str = ""
    bcc: str = ""
    is_html: bool = False


# ---------------------------------------------------------------------------
# HTML to text helper
# ---------------------------------------------------------------------------

class _HTMLStripper(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts: list[str] = []
        self._skip = False

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self._skip = True
        elif tag in ("br", "p", "div", "li", "tr"):
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            self._skip = False

    def handle_data(self, data):
        if not self._skip:
            self.parts.append(data)

    def get_text(self) -> str:
        return "".join(self.parts).strip()


def html_to_text(html: str) -> str:
    stripper = _HTMLStripper()
    stripper.feed(html)
    return stripper.get_text()


# ---------------------------------------------------------------------------
# Decode helpers
# ---------------------------------------------------------------------------

def decode_header_value(raw: str) -> str:
    """Decode RFC 2047 encoded header value."""
    if not raw:
        return ""
    parts = email.header.decode_header(raw)
    decoded = []
    for data, charset in parts:
        if isinstance(data, bytes):
            decoded.append(data.decode(charset or "utf-8", errors="replace"))
        else:
            decoded.append(data)
    return " ".join(decoded)


def extract_body(msg: email.message.Message) -> str:
    """Extract text body from email message."""
    if msg.is_multipart():
        text_part = None
        html_part = None
        for part in msg.walk():
            ct = part.get_content_type()
            if ct == "text/plain" and not text_part:
                text_part = part
            elif ct == "text/html" and not html_part:
                html_part = part
        # Prefer plain text
        target = text_part or html_part
        if target:
            payload = target.get_payload(decode=True)
            charset = target.get_content_charset() or "utf-8"
            text = payload.decode(charset, errors="replace")
            if target.get_content_type() == "text/html":
                return html_to_text(text)
            return text
        return ""
    else:
        payload = msg.get_payload(decode=True)
        if not payload:
            return ""
        charset = msg.get_content_charset() or "utf-8"
        text = payload.decode(charset, errors="replace")
        if msg.get_content_type() == "text/html":
            return html_to_text(text)
        return text


# ---------------------------------------------------------------------------
# IMAP — Read emails
# ---------------------------------------------------------------------------

class NaverWorksMailReader:
    """Read emails from Naver Works via IMAP."""

    def __init__(
        self,
        email_addr: Optional[str] = None,
        password: Optional[str] = None,
    ):
        self.email_addr = email_addr or os.getenv("NAVER_WORKS_EMAIL", "")
        self.password = password or os.getenv("NAVER_WORKS_PASSWORD", "")
        self._conn: Optional[imaplib.IMAP4_SSL] = None

    def connect(self):
        """Connect and login to IMAP server."""
        self._conn = imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT)
        self._conn.login(self.email_addr, self.password)

    def disconnect(self):
        """Logout and close connection."""
        if self._conn:
            try:
                self._conn.logout()
            except Exception:
                pass
            self._conn = None

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, *args):
        self.disconnect()

    def fetch_unread(self, folder: str = "INBOX", limit: int = 10) -> list[IncomingEmail]:
        """Fetch unread emails from the given folder."""
        if not self._conn:
            raise RuntimeError("Not connected. Use connect() or context manager.")

        self._conn.select(folder, readonly=True)
        _, data = self._conn.search(None, "UNSEEN")
        uids = data[0].split()

        if not uids:
            return []

        # Take most recent N
        uids = uids[-limit:]
        emails = []

        for uid in uids:
            _, msg_data = self._conn.fetch(uid, "(RFC822)")
            if not msg_data or not msg_data[0]:
                continue
            raw = msg_data[0][1]
            msg = email.message_from_bytes(raw)

            sender_raw = msg.get("From", "")
            sender_name, sender_addr = email.utils.parseaddr(sender_raw)

            emails.append(IncomingEmail(
                uid=uid.decode(),
                sender=sender_addr,
                sender_name=decode_header_value(sender_name) or sender_addr,
                subject=decode_header_value(msg.get("Subject", "")),
                body=extract_body(msg)[:3000],  # Truncate for Claude
                date=msg.get("Date", ""),
                to=decode_header_value(msg.get("To", "")),
                cc=decode_header_value(msg.get("Cc", "")),
            ))

        return emails

    def fetch_recent(self, folder: str = "INBOX", limit: int = 5) -> list[IncomingEmail]:
        """Fetch most recent emails regardless of read status."""
        if not self._conn:
            raise RuntimeError("Not connected.")

        self._conn.select(folder, readonly=True)
        _, data = self._conn.search(None, "ALL")
        uids = data[0].split()

        if not uids:
            return []

        uids = uids[-limit:]
        emails = []

        for uid in uids:
            _, msg_data = self._conn.fetch(uid, "(RFC822 FLAGS)")
            if not msg_data or not msg_data[0]:
                continue
            raw = msg_data[0][1]
            msg = email.message_from_bytes(raw)

            # Check flags for read status
            flag_data = msg_data[0][0].decode() if isinstance(msg_data[0][0], bytes) else ""
            is_read = "\\Seen" in flag_data

            sender_raw = msg.get("From", "")
            sender_name, sender_addr = email.utils.parseaddr(sender_raw)

            emails.append(IncomingEmail(
                uid=uid.decode(),
                sender=sender_addr,
                sender_name=decode_header_value(sender_name) or sender_addr,
                subject=decode_header_value(msg.get("Subject", "")),
                body=extract_body(msg)[:3000],
                date=msg.get("Date", ""),
                to=decode_header_value(msg.get("To", "")),
                cc=decode_header_value(msg.get("Cc", "")),
                is_read=is_read,
            ))

        return emails


# ---------------------------------------------------------------------------
# SMTP — Send emails
# ---------------------------------------------------------------------------

class NaverWorksMailSender:
    """Send emails via Naver Works SMTP."""

    def __init__(
        self,
        email_addr: Optional[str] = None,
        password: Optional[str] = None,
        sender_name: str = "Joonwha Lee",
    ):
        self.email_addr = email_addr or os.getenv("NAVER_WORKS_EMAIL", "")
        self.password = password or os.getenv("NAVER_WORKS_PASSWORD", "")
        self.sender_name = sender_name

    def send(self, outgoing: OutgoingEmail) -> bool:
        """Send an email. Returns True on success."""
        msg = MIMEMultipart("alternative")
        msg["From"] = f"{self.sender_name} <{self.email_addr}>"
        msg["To"] = outgoing.to
        msg["Subject"] = outgoing.subject

        if outgoing.cc:
            msg["Cc"] = outgoing.cc

        content_type = "html" if outgoing.is_html else "plain"
        msg.attach(MIMEText(outgoing.body, content_type, "utf-8"))

        recipients = [outgoing.to]
        if outgoing.cc:
            recipients.extend(r.strip() for r in outgoing.cc.split(","))
        if outgoing.bcc:
            recipients.extend(r.strip() for r in outgoing.bcc.split(","))

        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(self.email_addr, self.password)
            server.sendmail(self.email_addr, recipients, msg.as_string())

        return True


# ---------------------------------------------------------------------------
# Convenience functions
# ---------------------------------------------------------------------------

def check_new_mail(limit: int = 5) -> list[IncomingEmail]:
    """Quick helper to check for unread mail."""
    email_addr = os.getenv("NAVER_WORKS_EMAIL")
    password = os.getenv("NAVER_WORKS_PASSWORD")
    if not email_addr or not password:
        raise ValueError(
            "NAVER_WORKS_EMAIL, NAVER_WORKS_PASSWORD 환경변수를 설정하세요."
        )

    with NaverWorksMailReader(email_addr, password) as reader:
        return reader.fetch_unread(limit=limit)


def send_mail(to: str, subject: str, body: str, cc: str = "") -> bool:
    """Quick helper to send an email."""
    email_addr = os.getenv("NAVER_WORKS_EMAIL")
    password = os.getenv("NAVER_WORKS_PASSWORD")
    if not email_addr or not password:
        raise ValueError(
            "NAVER_WORKS_EMAIL, NAVER_WORKS_PASSWORD 환경변수를 설정하세요."
        )

    sender = NaverWorksMailSender(email_addr, password)
    return sender.send(OutgoingEmail(to=to, subject=subject, body=body, cc=cc))


# ---------------------------------------------------------------------------
# CLI test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "send":
        # python naver_works_mail.py send "to@email.com" "Subject" "Body"
        if len(sys.argv) < 5:
            print("Usage: python naver_works_mail.py send <to> <subject> <body>")
            sys.exit(1)
        ok = send_mail(sys.argv[2], sys.argv[3], sys.argv[4])
        print("Sent!" if ok else "Failed!")
    else:
        # Default: check unread
        emails = check_new_mail()
        if not emails:
            print("No unread emails.")
        for e in emails:
            print(f"\n{'='*50}")
            print(f"From: {e.sender_name} <{e.sender}>")
            print(f"Subject: {e.subject}")
            print(f"Date: {e.date}")
            print(f"Body: {e.body[:200]}...")
