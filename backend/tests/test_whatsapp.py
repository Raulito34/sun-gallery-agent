import sys
from pathlib import Path
from unittest.mock import patch, AsyncMock

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).parent.parent))

from main import app

client = TestClient(app)


class TestWhatsAppEndpoint:
    @patch("routers.whatsapp.generate_response", new_callable=AsyncMock)
    def test_whatsapp_reply_success(self, mock_generate):
        mock_generate.return_value = "Hi Ahmed! Great to hear from you. We have new Youngji Lee pieces available. Would love to show you at Art Central HK, booth B2. Let's meet!"
        response = client.post(
            "/api/whatsapp-reply",
            json={
                "mode": "whatsapp",
                "message": "Ahmed asked about new Youngji Lee works",
                "recipient": "Ahmed",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["mode"] == "whatsapp"
        assert "content" in data

    @patch("routers.whatsapp.generate_response", new_callable=AsyncMock)
    def test_whatsapp_reply_minimal(self, mock_generate):
        mock_generate.return_value = "Thank you for your interest. Let me get back to you shortly."
        response = client.post(
            "/api/whatsapp-reply",
            json={"mode": "whatsapp", "message": "Reply to collector inquiry"},
        )
        assert response.status_code == 200
