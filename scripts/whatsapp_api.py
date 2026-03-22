"""
Sun Gallery — WhatsApp Business Cloud API Integration

Meta WhatsApp Business Cloud API를 통해 메시지를 수신/발신합니다.

환경변수:
  WHATSAPP_TOKEN       — Meta 액세스 토큰 (영구 시스템 사용자 토큰 권장)
  WHATSAPP_PHONE_ID    — WhatsApp 비즈니스 전화번호 ID
  WHATSAPP_VERIFY_TOKEN — Webhook 검증 토큰 (직접 설정하는 임의 문자열)

Meta 설정 절차:
  1. https://developers.facebook.com → 앱 만들기 → WhatsApp 추가
  2. WhatsApp > API 설정 > 임시 액세스 토큰 복사 (테스트용)
  3. 영구 토큰: 비즈니스 설정 > 시스템 사용자 > 토큰 생성
  4. 전화번호 ID: WhatsApp > API 설정 > 전화번호 ID 복사
  5. Webhook 설정: 콜백 URL + 검증 토큰 등록
"""

import json
import os
from dataclasses import dataclass
from typing import Optional

import requests

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
GRAPH_API_VERSION = "v21.0"
GRAPH_API_BASE = f"https://graph.facebook.com/{GRAPH_API_VERSION}"


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class WhatsAppMessage:
    """Incoming WhatsApp message."""
    from_number: str
    from_name: str
    message_id: str
    text: str
    timestamp: str
    message_type: str = "text"  # text, image, document, etc.


@dataclass
class WhatsAppOutgoing:
    """Outgoing WhatsApp message."""
    to: str  # Phone number with country code (e.g., +971501234567)
    text: str


# ---------------------------------------------------------------------------
# WhatsApp Client
# ---------------------------------------------------------------------------

class WhatsAppClient:
    """Send and process WhatsApp Business messages."""

    def __init__(
        self,
        token: Optional[str] = None,
        phone_id: Optional[str] = None,
    ):
        self.token = token or os.getenv("WHATSAPP_TOKEN", "")
        self.phone_id = phone_id or os.getenv("WHATSAPP_PHONE_ID", "")
        self.base_url = f"{GRAPH_API_BASE}/{self.phone_id}"

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }

    def send_text(self, to: str, text: str) -> dict:
        """Send a text message.

        Args:
            to: Phone number with country code (no +, e.g., 971501234567)
            text: Message text
        Returns:
            API response dict
        """
        # Strip + and spaces
        to_clean = to.replace("+", "").replace(" ", "").replace("-", "")

        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to_clean,
            "type": "text",
            "text": {"body": text},
        }

        resp = requests.post(
            f"{self.base_url}/messages",
            headers=self._headers(),
            json=payload,
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()

    def mark_as_read(self, message_id: str) -> bool:
        """Mark a message as read."""
        payload = {
            "messaging_product": "whatsapp",
            "status": "read",
            "message_id": message_id,
        }
        try:
            resp = requests.post(
                f"{self.base_url}/messages",
                headers=self._headers(),
                json=payload,
                timeout=10,
            )
            return resp.ok
        except Exception:
            return False

    @staticmethod
    def parse_webhook(payload: dict) -> list[WhatsAppMessage]:
        """Parse incoming webhook payload into messages.

        Args:
            payload: Raw webhook JSON from Meta
        Returns:
            List of parsed messages
        """
        messages = []

        for entry in payload.get("entry", []):
            for change in entry.get("changes", []):
                value = change.get("value", {})

                # Build contact name lookup
                contacts = {}
                for c in value.get("contacts", []):
                    wa_id = c.get("wa_id", "")
                    name = c.get("profile", {}).get("name", wa_id)
                    contacts[wa_id] = name

                for msg in value.get("messages", []):
                    msg_type = msg.get("type", "text")
                    text = ""

                    if msg_type == "text":
                        text = msg.get("text", {}).get("body", "")
                    elif msg_type == "image":
                        text = msg.get("image", {}).get("caption", "[Image]")
                    elif msg_type == "document":
                        text = msg.get("document", {}).get("caption", "[Document]")
                    elif msg_type == "reaction":
                        text = msg.get("reaction", {}).get("emoji", "")
                    else:
                        text = f"[{msg_type}]"

                    from_number = msg.get("from", "")
                    messages.append(WhatsAppMessage(
                        from_number=from_number,
                        from_name=contacts.get(from_number, from_number),
                        message_id=msg.get("id", ""),
                        text=text,
                        timestamp=msg.get("timestamp", ""),
                        message_type=msg_type,
                    ))

        return messages


# ---------------------------------------------------------------------------
# Webhook handler (FastAPI)
# ---------------------------------------------------------------------------

def create_webhook_router():
    """Create a FastAPI router for WhatsApp webhook.

    Usage in main.py:
        from scripts.whatsapp_api import create_webhook_router
        app.include_router(create_webhook_router())
    """
    from fastapi import APIRouter, Query, Request
    from fastapi.responses import PlainTextResponse

    router = APIRouter(prefix="/api/whatsapp-webhook", tags=["whatsapp"])
    verify_token = os.getenv("WHATSAPP_VERIFY_TOKEN", "sun-gallery-verify")

    # Store for incoming messages (in production, use a database)
    incoming_queue: list[WhatsAppMessage] = []

    @router.get("")
    async def verify(
        hub_mode: str = Query(None, alias="hub.mode"),
        hub_token: str = Query(None, alias="hub.verify_token"),
        hub_challenge: str = Query(None, alias="hub.challenge"),
    ):
        """Webhook verification endpoint (GET)."""
        if hub_mode == "subscribe" and hub_token == verify_token:
            return PlainTextResponse(hub_challenge)
        return PlainTextResponse("Forbidden", status_code=403)

    @router.post("")
    async def receive(request: Request):
        """Receive incoming WhatsApp messages (POST)."""
        payload = await request.json()
        messages = WhatsAppClient.parse_webhook(payload)

        for msg in messages:
            incoming_queue.append(msg)
            print(f"[WhatsApp] {msg.from_name} ({msg.from_number}): {msg.text}")

        return {"status": "ok"}

    @router.get("/messages")
    async def list_messages(limit: int = 10):
        """List recent incoming messages."""
        return {"messages": [
            {
                "from": m.from_number,
                "name": m.from_name,
                "text": m.text,
                "timestamp": m.timestamp,
                "type": m.message_type,
            }
            for m in incoming_queue[-limit:]
        ]}

    return router


# ---------------------------------------------------------------------------
# Convenience functions
# ---------------------------------------------------------------------------

def send_whatsapp(to: str, text: str) -> dict:
    """Quick helper to send a WhatsApp message."""
    token = os.getenv("WHATSAPP_TOKEN")
    phone_id = os.getenv("WHATSAPP_PHONE_ID")
    if not token or not phone_id:
        raise ValueError(
            "WHATSAPP_TOKEN, WHATSAPP_PHONE_ID 환경변수를 설정하세요."
        )
    client = WhatsAppClient(token, phone_id)
    return client.send_text(to, text)


# ---------------------------------------------------------------------------
# CLI test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 3:
        print("Usage: python whatsapp_api.py <phone_number> <message>")
        print("Example: python whatsapp_api.py +971501234567 'Hello from Sun Gallery'")
        sys.exit(1)

    result = send_whatsapp(sys.argv[1], sys.argv[2])
    print(f"Sent: {json.dumps(result, indent=2)}")
