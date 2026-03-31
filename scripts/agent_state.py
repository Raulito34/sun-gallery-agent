"""
Sun Gallery — Agent State Manager

에이전트가 이미 처리한 항목을 추적하여 중복 알림을 방지합니다.
agent_state.json에 상태를 저장하고, 봇 재시작 간에도 유지됩니다.
"""

import json
import os
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parent.parent
STATE_PATH = ROOT / "backend" / "data" / "agent_state.json"

_EMPTY_STATE = {
    "version": 1,
    "last_scan_utc": None,
    "acted_items": [],
    "pending_approvals": [],
    "dismissed_items": [],
}


class AgentState:
    """Manage agent state with atomic JSON persistence."""

    def __init__(self, path: Path = STATE_PATH):
        self.path = path
        self._state: dict = self._load()

    # ------------------------------------------------------------------
    # Load / Save
    # ------------------------------------------------------------------

    def _load(self) -> dict:
        if not self.path.exists():
            return dict(_EMPTY_STATE)
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return dict(_EMPTY_STATE)

    def save(self):
        """Atomic write: write to temp file then rename."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(
            dir=self.path.parent, suffix=".tmp", prefix="state_"
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(self._state, f, ensure_ascii=False, indent=2)
            os.replace(tmp, self.path)
        except Exception:
            try:
                os.unlink(tmp)
            except OSError:
                pass
            raise

    def reload(self):
        self._state = self._load()

    # ------------------------------------------------------------------
    # Acted items (completed actions — don't repeat)
    # ------------------------------------------------------------------

    def was_acted_on(self, item_id: str) -> bool:
        acted_ids = {a["id"] for a in self._state["acted_items"]}
        dismissed = set(self._state["dismissed_items"])
        pending_ids = {p["id"] for p in self._state["pending_approvals"]}
        return item_id in acted_ids or item_id in dismissed or item_id in pending_ids

    def mark_acted(self, item_id: str, action: str = "completed"):
        self._state["acted_items"].append({
            "id": item_id,
            "action": action,
            "at": datetime.utcnow().isoformat() + "Z",
        })

    # ------------------------------------------------------------------
    # Pending approvals (waiting for human decision)
    # ------------------------------------------------------------------

    def add_pending(
        self,
        item_id: str,
        task_type: str,
        draft: str,
        channel: str = "email",
        to: str = "",
        metadata: Optional[dict] = None,
        telegram_message_id: Optional[int] = None,
    ):
        self._state["pending_approvals"].append({
            "id": item_id,
            "type": task_type,
            "draft": draft,
            "channel": channel,
            "to": to,
            "metadata": metadata or {},
            "telegram_message_id": telegram_message_id,
            "status": "pending",
            "created_at": datetime.utcnow().isoformat() + "Z",
        })

    def get_pending(self, item_id: str) -> Optional[dict]:
        for p in self._state["pending_approvals"]:
            if p["id"] == item_id and p["status"] == "pending":
                return p
        return None

    def list_pending(self) -> list[dict]:
        return [p for p in self._state["pending_approvals"] if p["status"] == "pending"]

    def approve(self, item_id: str) -> Optional[dict]:
        for p in self._state["pending_approvals"]:
            if p["id"] == item_id and p["status"] == "pending":
                p["status"] = "approved"
                p["approved_at"] = datetime.utcnow().isoformat() + "Z"
                self.mark_acted(item_id, "approved")
                return p
        return None

    def dismiss(self, item_id: str) -> bool:
        for p in self._state["pending_approvals"]:
            if p["id"] == item_id and p["status"] == "pending":
                p["status"] = "dismissed"
                self._state["dismissed_items"].append(item_id)
                return True
        # Also allow dismissing non-pending items
        if item_id not in self._state["dismissed_items"]:
            self._state["dismissed_items"].append(item_id)
            return True
        return False

    # ------------------------------------------------------------------
    # Scan tracking
    # ------------------------------------------------------------------

    @property
    def last_scan(self) -> Optional[str]:
        return self._state.get("last_scan_utc")

    def update_scan_time(self):
        self._state["last_scan_utc"] = datetime.utcnow().isoformat() + "Z"

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    def cleanup_old(self, days: int = 7):
        """Remove acted/dismissed items older than N days."""
        cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat() + "Z"

        self._state["acted_items"] = [
            a for a in self._state["acted_items"]
            if a.get("at", "") > cutoff
        ]
        self._state["pending_approvals"] = [
            p for p in self._state["pending_approvals"]
            if p.get("created_at", "") > cutoff or p["status"] == "pending"
        ]


def make_task_id(task_type: str, entity: str, date_str: str = "") -> str:
    """Generate deterministic task ID."""
    from datetime import date as _date
    if not date_str:
        date_str = _date.today().isoformat()
    entity_clean = entity.lower().replace(" ", "_").replace("'", "")
    return f"{task_type}_{entity_clean}_{date_str}"
