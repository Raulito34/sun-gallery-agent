import sys
from pathlib import Path
from unittest.mock import patch, AsyncMock

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).parent.parent))

from main import app

client = TestClient(app)


class TestEmailEndpoint:
    @patch("routers.email.generate_response", new_callable=AsyncMock)
    def test_email_draft_success(self, mock_generate):
        mock_generate.return_value = "Subject: Follow-up\n\nDear Ahmed,\n\nThank you."
        response = client.post(
            "/api/email-draft",
            json={
                "mode": "email",
                "message": "Write a follow-up email to Ahmed about Youngji Lee paintings",
                "recipient": "Ahmed",
                "sender": "Joonwha Lee",
                "language": "en",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["mode"] == "email"
        assert "content" in data
        assert data["metadata"]["recipient"] == "Ahmed"

    @patch("routers.email.generate_response", new_callable=AsyncMock)
    def test_email_draft_minimal_request(self, mock_generate):
        mock_generate.return_value = "Subject: Inquiry\n\nHello."
        response = client.post(
            "/api/email-draft",
            json={"mode": "email", "message": "Draft an inquiry email"},
        )
        assert response.status_code == 200


class TestHealthEndpoint:
    def test_health_check(self):
        response = client.get("/api/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"
