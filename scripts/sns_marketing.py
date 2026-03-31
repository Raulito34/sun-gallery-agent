"""
Sun Art Center — SNS Marketing Manager

SNS 콘텐츠 생성, 큐 관리, 포스팅을 담당합니다.

Track A (즉시): 콘텐츠 생성 + Telegram 승인 + 큐 관리
Track B (계정 생성 후): Instagram Graph API / X API v2 자동 포스팅

환경변수 (Track B — 나중에):
  INSTAGRAM_ACCESS_TOKEN — Meta Graph API 토큰
  INSTAGRAM_USER_ID      — Instagram 비즈니스 계정 ID
  X_API_KEY / X_API_SECRET / X_ACCESS_TOKEN / X_ACCESS_SECRET — X API
"""

import json
import os
import re
from datetime import date, datetime
from pathlib import Path
from typing import Optional

import requests

ROOT = Path(__file__).resolve().parent.parent
QUEUE_PATH = ROOT / "backend" / "data" / "sns_content_queue.json"
TEMPLATES_PATH = ROOT / "backend" / "data" / "sns_templates.json"


def load_templates() -> dict:
    """Load SNS templates including brand info, hashtags, content types."""
    if not TEMPLATES_PATH.exists():
        return {}
    try:
        return json.loads(TEMPLATES_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def get_hashtags(groups: list[str]) -> str:
    """Get combined hashtags from template groups."""
    templates = load_templates()
    all_tags = templates.get("hashtags", {})
    tags = []
    for g in groups:
        tags.extend(all_tags.get(g, []))
    return " ".join(dict.fromkeys(tags))  # dedupe, preserve order


def get_image_prompt(template_key: str, **kwargs) -> str:
    """Get image prompt template with variable substitution."""
    templates = load_templates()
    prompts = templates.get("image_prompt_templates", {})
    prompt = prompts.get(template_key, "")
    for k, v in kwargs.items():
        prompt = prompt.replace(f"{{{k}}}", str(v))
    return prompt

# ---------------------------------------------------------------------------
# Content Queue
# ---------------------------------------------------------------------------


def load_queue() -> list[dict]:
    if not QUEUE_PATH.exists():
        return []
    try:
        return json.loads(QUEUE_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []


def save_queue(queue: list[dict]):
    QUEUE_PATH.parent.mkdir(parents=True, exist_ok=True)
    QUEUE_PATH.write_text(
        json.dumps(queue, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def add_to_queue(content: dict):
    """승인된 콘텐츠를 큐에 추가."""
    queue = load_queue()
    content.setdefault("status", "queued")
    content.setdefault("created_at", datetime.utcnow().isoformat() + "Z")
    content.setdefault("posted_at", None)
    queue.append(content)
    save_queue(queue)


def get_queued() -> list[dict]:
    """포스팅 대기 중인 콘텐츠."""
    return [c for c in load_queue() if c.get("status") == "queued"]


def get_posted() -> list[dict]:
    """이미 포스팅된 콘텐츠."""
    return [c for c in load_queue() if c.get("status") == "posted"]


def mark_posted(content_id: str, platform: str):
    """콘텐츠를 포스팅 완료로 표시."""
    queue = load_queue()
    for c in queue:
        if c.get("id") == content_id:
            c["status"] = "posted"
            c["posted_at"] = datetime.utcnow().isoformat() + "Z"
            c["posted_platform"] = platform
            break
    save_queue(queue)


def pop_next() -> Optional[dict]:
    """큐에서 다음 포스팅할 콘텐츠를 꺼냄."""
    queued = get_queued()
    if not queued:
        return None
    # 날짜가 가장 빠른 것 우선
    queued.sort(key=lambda c: c.get("scheduled_date", "9999"))
    return queued[0]


# ---------------------------------------------------------------------------
# Content Generation Prompts
# ---------------------------------------------------------------------------

SAC_BRAND = {
    "name_ko": "선아트센터",
    "name_en": "Sun Art Center",
    "location": "서울 종로구 인사동",
    "hours": "화-일 10:00-18:00 | 월요일 휴관",
    "hashtags_base": [
        "#SunArtCenter", "#선아트센터", "#인사동전시",
        "#현대미술", "#ContemporaryArt", "#SeoulArt",
        "#갤러리", "#ArtGallery", "#인사동",
    ],
}


def build_exhibition_post_prompt(exhibition: dict) -> str:
    """전시 홍보 포스트용 Claude 프롬프트."""
    templates = load_templates()
    brand = templates.get("brand", SAC_BRAND)
    hashtags = get_hashtags(["core", "location", "art", "free"])
    img_prompt = get_image_prompt("exhibition", artwork_type=exhibition.get("description", "artwork")[:50])

    return (
        f"Sun Art Center 전시 홍보 Instagram/X 포스트를 작성해줘.\n\n"
        f"전시 정보:\n"
        f"- 제목: {exhibition.get('title', '')}\n"
        f"- 작가: {exhibition.get('artist', '')}\n"
        f"- 기간: {exhibition.get('startDate', '')} ~ {exhibition.get('endDate', '')}\n"
        f"- 층: {exhibition.get('floor', '')}\n"
        f"- 설명: {exhibition.get('description', '')}\n\n"
        f"갤러리 정보:\n"
        f"- 이름: {brand.get('name_en', 'Sun Art Center')} ({brand.get('name_ko', '선아트센터')})\n"
        f"- 위치: {brand.get('location_ko', '서울 종로구 인사동')}\n"
        f"- 운영: {brand.get('hours', '화-일 10:00-18:00')}\n\n"
        f"해시태그 후보: {hashtags}\n\n"
        f"요구사항:\n"
        f"1. 한국어 + 영어 병기 (한국어 먼저, 영어 아래)\n"
        f"2. 이모지 적절히 사용\n"
        f"3. 해시태그 10-15개\n"
        f"4. Instagram용 (최대 2200자)과 X용 (최대 280자) 두 버전 생성\n"
        f"5. '선화랑' 브랜드는 절대 사용하지 말 것. 'Sun Art Center'/'선아트센터'만 사용\n"
        f"6. AI 이미지 생성용 프롬프트 (참고: {img_prompt[:100]})"
    )


def build_space_highlight_prompt(space: dict) -> str:
    """공간 하이라이트 포스트용 프롬프트."""
    return (
        f"Sun Art Center 공간 소개 포스트를 작성해줘.\n\n"
        f"공간 정보:\n"
        f"- 이름: {space.get('name', '')} ({space.get('floorLabel', '')})\n"
        f"- 면적: {space.get('area', '')}㎡\n"
        f"- 높이: {space.get('height', '')}m\n"
        f"- 수용: {space.get('capacity', '')}점\n"
        f"- 설명: {space.get('description', '')}\n"
        f"- 특징: {space.get('features', '')}\n\n"
        f"대관 문의: sungallery1977@gmail.com\n\n"
        f"요구사항:\n"
        f"1. 대관을 고려하는 작가들에게 매력적으로\n"
        f"2. 공간의 물리적 장점 강조\n"
        f"3. 인사동 위치의 문화적 가치 언급\n"
        f"4. Instagram용 + X용 두 버전\n"
        f"5. 해시태그 포함\n"
        f"6. '선화랑' 브랜드 사용 금지. 'Sun Art Center' only"
    )


def build_weekly_calendar_prompt(exhibitions: list[dict]) -> str:
    """이번 주 전시 캘린더 포스트용 프롬프트."""
    ex_list = ""
    for ex in exhibitions:
        ex_list += (
            f"- {ex.get('floor', '')}: {ex.get('artist', '')} "
            f"'{ex.get('title', '')}' ({ex.get('startDate', '')}~{ex.get('endDate', '')})\n"
        )

    return (
        f"Sun Art Center 이번 주 전시 캘린더 포스트를 작성해줘.\n\n"
        f"현재 전시:\n{ex_list}\n"
        f"갤러리: {SAC_BRAND['name_en']} ({SAC_BRAND['name_ko']})\n"
        f"위치: {SAC_BRAND['location']}\n"
        f"운영: {SAC_BRAND['hours']}\n\n"
        f"요구사항:\n"
        f"1. 깔끔한 캘린더 형식\n"
        f"2. Instagram용 + X용 두 버전\n"
        f"3. '이번 주 선아트센터' 느낌으로\n"
        f"4. 해시태그 포함\n"
        f"5. 'Sun Art Center' 브랜드만 사용"
    )


def build_artist_spotlight_prompt(exhibition: dict) -> str:
    """참여 작가 스포트라이트 포스트용 프롬프트."""
    return (
        f"Sun Art Center 참여 작가 스포트라이트 포스트를 작성해줘.\n\n"
        f"작가: {exhibition.get('artist', '')}\n"
        f"전시: '{exhibition.get('title', '')}'\n"
        f"기간: {exhibition.get('startDate', '')} ~ {exhibition.get('endDate', '')}\n"
        f"층: {exhibition.get('floor', '')}\n"
        f"설명: {exhibition.get('description', '')}\n\n"
        f"요구사항:\n"
        f"1. 작가의 작업 세계와 이번 전시의 의미를 조명\n"
        f"2. 관람 유도하는 CTA 포함\n"
        f"3. Instagram용 + X용\n"
        f"4. 해시태그 포함 (작가명 해시태그도)\n"
        f"5. 'Sun Art Center' 브랜드만 사용"
    )


def make_content_id(content_type: str, ref: str = "") -> str:
    """콘텐츠 ID 생성."""
    today = date.today().isoformat()
    ref_clean = ref.lower().replace(" ", "_")[:20]
    return f"post_{today}_{content_type}_{ref_clean}"


def parse_sns_response(claude_response: str) -> dict:
    """Claude 응답에서 Instagram/X 텍스트, 해시태그를 추출."""
    result = {
        "instagram_text": "",
        "x_text": "",
        "hashtags": [],
        "image_prompt": "",
    }

    # Instagram 섹션 추출
    ig_match = re.search(
        r"(?:Instagram|인스타그램)[^\n]*\n(.*?)(?=(?:X |Twitter|트위터|\Z))",
        claude_response, re.DOTALL | re.IGNORECASE
    )
    if ig_match:
        result["instagram_text"] = ig_match.group(1).strip()

    # X 섹션 추출
    x_match = re.search(
        r"(?:X |Twitter|트위터)[^\n]*\n(.*?)(?=(?:이미지|Image|해시|#|\Z))",
        claude_response, re.DOTALL | re.IGNORECASE
    )
    if x_match:
        result["x_text"] = x_match.group(1).strip()

    # 해시태그 추출
    hashtags = re.findall(r"#\w+", claude_response)
    result["hashtags"] = list(dict.fromkeys(hashtags))  # dedupe, preserve order

    # 이미지 프롬프트 추출
    img_match = re.search(
        r"(?:이미지 프롬프트|Image prompt)[:\s]*(.*?)(?:\n\n|\Z)",
        claude_response, re.IGNORECASE
    )
    if img_match:
        result["image_prompt"] = img_match.group(1).strip()

    # Fallback: 전체 텍스트를 instagram으로
    if not result["instagram_text"]:
        result["instagram_text"] = claude_response.strip()
    if not result["x_text"]:
        # X는 280자 제한 — 첫 280자
        result["x_text"] = claude_response.strip()[:280]

    return result


# ---------------------------------------------------------------------------
# Instagram Graph API (Track B)
# ---------------------------------------------------------------------------

def post_to_instagram(image_url: str, caption: str) -> Optional[dict]:
    """Instagram Graph API로 이미지 포스트 게시."""
    token = os.getenv("INSTAGRAM_ACCESS_TOKEN")
    user_id = os.getenv("INSTAGRAM_USER_ID")
    if not token or not user_id:
        return None

    # Step 1: Create media container
    resp = requests.post(
        f"https://graph.facebook.com/v21.0/{user_id}/media",
        params={
            "image_url": image_url,
            "caption": caption,
            "access_token": token,
        },
        timeout=30,
    )
    resp.raise_for_status()
    creation_id = resp.json().get("id")

    # Step 2: Publish
    resp = requests.post(
        f"https://graph.facebook.com/v21.0/{user_id}/media_publish",
        params={
            "creation_id": creation_id,
            "access_token": token,
        },
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


# ---------------------------------------------------------------------------
# X (Twitter) API v2 (Track B)
# ---------------------------------------------------------------------------

def post_to_x(text: str) -> Optional[dict]:
    """X API v2로 트윗 게시."""
    api_key = os.getenv("X_API_KEY")
    api_secret = os.getenv("X_API_SECRET")
    access_token = os.getenv("X_ACCESS_TOKEN")
    access_secret = os.getenv("X_ACCESS_SECRET")

    if not all([api_key, api_secret, access_token, access_secret]):
        return None

    try:
        import tweepy
    except ImportError:
        return None

    client = tweepy.Client(
        consumer_key=api_key,
        consumer_secret=api_secret,
        access_token=access_token,
        access_token_secret=access_secret,
    )
    resp = client.create_tweet(text=text[:280])
    return {"id": resp.data["id"]}


# ---------------------------------------------------------------------------
# CLI test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=== SNS Content Queue ===")
    queued = get_queued()
    posted = get_posted()
    print(f"대기: {len(queued)}건 | 완료: {len(posted)}건")
    for c in queued:
        print(f"  [{c.get('id')}] {c.get('type')} — {c.get('scheduled_date')}")
