"""
Sun Art Center — Website API Client

SAC Express 백엔드(Railway 배포)의 REST API를 호출하여
대관 신청, 전시, 뉴스, 문의 등을 관리합니다.

환경변수:
  SAC_API_URL    — SAC 백엔드 URL (예: https://your-app.railway.app)
  SAC_ADMIN_CODE — 관리자 인증 코드 (x-admin-code 헤더)
"""

import os
from typing import Optional

import requests

DEFAULT_TIMEOUT = 15


class SACWebsiteClient:
    """SAC Express API client."""

    def __init__(
        self,
        api_url: Optional[str] = None,
        admin_code: Optional[str] = None,
    ):
        self.api_url = (api_url or os.getenv("SAC_API_URL", "")).rstrip("/")
        self.admin_code = admin_code or os.getenv("SAC_ADMIN_CODE", "")

    def _headers(self, admin: bool = False) -> dict:
        h = {"Content-Type": "application/json"}
        if admin and self.admin_code:
            h["x-admin-code"] = self.admin_code
        return h

    def _get(self, path: str, admin: bool = False, params: Optional[dict] = None) -> list | dict:
        resp = requests.get(
            f"{self.api_url}{path}",
            headers=self._headers(admin),
            params=params,
            timeout=DEFAULT_TIMEOUT,
        )
        resp.raise_for_status()
        return resp.json()

    def _post(self, path: str, data: dict, admin: bool = False) -> dict:
        resp = requests.post(
            f"{self.api_url}{path}",
            headers=self._headers(admin),
            json=data,
            timeout=DEFAULT_TIMEOUT,
        )
        resp.raise_for_status()
        return resp.json()

    def _patch(self, path: str, data: dict, admin: bool = True) -> dict:
        resp = requests.patch(
            f"{self.api_url}{path}",
            headers=self._headers(admin),
            json=data,
            timeout=DEFAULT_TIMEOUT,
        )
        resp.raise_for_status()
        return resp.json()

    def _delete(self, path: str, admin: bool = True) -> bool:
        resp = requests.delete(
            f"{self.api_url}{path}",
            headers=self._headers(admin),
            timeout=DEFAULT_TIMEOUT,
        )
        return resp.ok

    # ------------------------------------------------------------------
    # Rentals (대관)
    # ------------------------------------------------------------------

    def get_rentals(self) -> list[dict]:
        """전체 대관 신청 목록 (admin)."""
        return self._get("/api/rentals", admin=True)

    def get_rental_status(self) -> list[dict]:
        """공개 대관 상태 목록."""
        return self._get("/api/rentals/status")

    def update_rental(self, rental_id: int, status: str) -> dict:
        """대관 상태 업데이트 (approved/rejected/cancelled)."""
        return self._patch(f"/api/rentals/{rental_id}", {"status": status})

    def delete_rental(self, rental_id: int) -> bool:
        return self._delete(f"/api/rentals/{rental_id}")

    # ------------------------------------------------------------------
    # Exhibitions (전시)
    # ------------------------------------------------------------------

    def get_exhibitions(self, status: Optional[str] = None) -> list[dict]:
        params = {"status": status} if status else None
        return self._get("/api/exhibitions", params=params)

    def get_exhibition(self, exhibition_id: int) -> dict:
        return self._get(f"/api/exhibitions/{exhibition_id}")

    def create_exhibition(self, data: dict) -> dict:
        return self._post("/api/exhibitions", data, admin=True)

    def update_exhibition(self, exhibition_id: int, data: dict) -> dict:
        return self._patch(f"/api/exhibitions/{exhibition_id}", data)

    # ------------------------------------------------------------------
    # News (뉴스)
    # ------------------------------------------------------------------

    def get_news(self, category: Optional[str] = None) -> list[dict]:
        params = {"category": category} if category else None
        return self._get("/api/news", params=params)

    def create_news(self, data: dict) -> dict:
        return self._post("/api/news", data, admin=True)

    # ------------------------------------------------------------------
    # Spaces & Pricing (공간/가격)
    # ------------------------------------------------------------------

    def get_spaces(self) -> list[dict]:
        return self._get("/api/spaces")

    def get_pricing(self) -> list[dict]:
        return self._get("/api/pricing")

    # ------------------------------------------------------------------
    # Contact (문의)
    # ------------------------------------------------------------------

    def submit_contact(self, data: dict) -> dict:
        return self._post("/api/contact", data)

    # ------------------------------------------------------------------
    # Site Images
    # ------------------------------------------------------------------

    def get_site_images(self) -> list[dict]:
        return self._get("/api/site-images")


# ---------------------------------------------------------------------------
# Convenience singleton
# ---------------------------------------------------------------------------

_client: Optional[SACWebsiteClient] = None


def get_sac_client() -> SACWebsiteClient:
    global _client
    if _client is None:
        _client = SACWebsiteClient()
    return _client


# ---------------------------------------------------------------------------
# CLI test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    client = SACWebsiteClient()
    if not client.api_url:
        print("SAC_API_URL 환경변수를 설정하세요.")
        print("  export SAC_API_URL=https://your-app.railway.app")
    else:
        print(f"API: {client.api_url}")
        try:
            rentals = client.get_rental_status()
            print(f"\n대관 현황: {len(rentals)}건")
            for r in rentals:
                print(f"  {r.get('spaceName')} | {r.get('startDate')}~{r.get('endDate')} | {r.get('status')}")
        except Exception as e:
            print(f"Error: {e}")

        try:
            exhibitions = client.get_exhibitions()
            print(f"\n전시: {len(exhibitions)}건")
            for ex in exhibitions:
                print(f"  {ex.get('title')} — {ex.get('artist')} ({ex.get('status')})")
        except Exception as e:
            print(f"Error: {e}")
