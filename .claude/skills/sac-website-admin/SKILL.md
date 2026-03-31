---
description: "Sun Art Center 홈페이지 어드민. 전시/공간 이미지 업데이트, 공지사항 작성, 전시 정보 관리. 마케팅 에이전트와 연동."
---

# SAC Website Admin Skill

Sun Art Center 홈페이지(rauliton34-qq16.vercel.app)의 콘텐츠를 관리합니다.
전시 이미지 교체, 공간 사진 업데이트, 공지사항 작성, 전시 등록/수정을 처리합니다.

> **마케팅 에이전트와 항상 연동**: 홈페이지 콘텐츠가 변경되면 SNS 포스팅 소재도 함께 업데이트해야 합니다.

## 사용법

홈페이지 관리, 이미지 업데이트, 공지 작성 요청 시 활성화됩니다.

- `/site_images` — 현재 홈페이지 이미지 목록
- `/update_image <key> <url>` — 이미지 교체
- `/news_list` — 공지사항 목록
- `/news_write <제목> | <내용>` — 공지 작성
- `/exhibition_add` — 새 전시 등록
- `/site_sync` — 전시 변경 → SNS 콘텐츠 자동 생성 트리거

## 웹사이트 구조

```
rauliton34-qq16.vercel.app/
├── /                          ← 홈 (SiteImage로 메인 이미지 관리)
├── /about                     ← 소개
│   ├── /about/greeting        ← 인사말
│   ├── /about/visitor-info    ← 관람 안내
│   ├── /about/architecture    ← 건축
│   └── /about/location        ← 찾아오는 길
├── /exhibition                ← 전시 목록 (Exhibition 모델)
│   └── /exhibition/:id        ← 전시 상세
├── /spaces                    ← 공간 소개 (Space 모델)
│   └── /spaces/:floor         ← 층별 상세
├── /rental                    ← 대관 안내
│   ├── /rental/procedure      ← 대관 절차
│   ├── /rental/pricing        ← 대관료
│   ├── /rental/apply          ← 대관 신청 (Rental 모델)
│   ├── /rental/status         ← 신청 현황
│   └── /rental/list           ← 신청 목록
├── /news                      ← 공지사항 (News 모델)
├── /contact                   ← 문의 (Contact 모델)
└── /admin                     ← 관리자
    ├── /admin/homepage         ← 홈페이지 관리
    └── /admin/rentals          ← 대관 관리
```

## API 엔드포인트 (어드민)

### 이미지 관리

| Method | Endpoint | 설명 |
|--------|----------|------|
| GET | `/api/site-images` | 홈페이지 이미지 목록 |
| PATCH | `/api/site-images/:key` | 이미지 URL/라벨 수정 |
| POST | `/api/site-images` | 새 이미지 등록 |
| DELETE | `/api/site-images/:key` | 이미지 삭제 |

SiteImage 모델:
```
{ key: string (unique), imageUrl: string, label: string }
```

### 전시 이미지 업데이트

| Method | Endpoint | 설명 |
|--------|----------|------|
| PATCH | `/api/exhibitions/:id` | `{ imageUrl: "new-url" }` |

Exhibition 모델:
```
{ id, title, artist, description, startDate, endDate, floor, imageUrl, status, details }
```

### 공지사항

| Method | Endpoint | 설명 |
|--------|----------|------|
| GET | `/api/news` | 목록 (category 필터 가능) |
| POST | `/api/news` | 새 공지 `{ title, content, category }` |
| PATCH | `/api/news/:id` | 수정 |
| DELETE | `/api/news/:id` | 삭제 |

category 예시: "공지", "전시", "이벤트", "보도자료"

### 인증
모든 admin 엔드포인트는 `x-admin-code` 헤더 필요.

## 이미지 업데이트 워크플로

### 전시 이미지 교체
```
1. 사용자가 Telegram으로 이미지 URL 또는 사진 전송
2. 어드민 에이전트가 해당 전시의 imageUrl 업데이트
   → PATCH /api/exhibitions/:id { imageUrl: "..." }
3. [자동] 마케팅 에이전트에 알림:
   "전시 #{id} 이미지 업데이트됨 → SNS 콘텐츠 재생성 필요"
4. 마케팅 에이전트가 새 이미지로 포스트 생성
```

### 공간(층) 이미지 교체
```
1. 사용자가 층별 실제 사진 전송
2. 어드민 에이전트가 SiteImage 업데이트
   → PATCH /api/site-images/:key { imageUrl: "..." }
3. [자동] 마케팅 에이전트에 알림:
   "공간 이미지 업데이트됨 → Space Highlight 포스트 소재 갱신"
```

### 이미지 호스팅
이미지 URL은 외부 호스팅 서비스 사용:
- **추천**: Cloudinary (무료 25GB), Imgur, ImgBB
- 사용자가 Telegram으로 사진 전송 → 봇이 호스팅 서비스에 업로드 → URL 획득 → API 호출

## 공지사항 작성 워크플로

### 전시 오프닝 공지
```
1. 새 전시 등록 또는 오프닝 D-7 감지
2. 어드민 에이전트가 Claude로 공지문 생성:
   - 제목, 작가, 기간, 층, 관람 안내
   - 오프닝 리셉션 정보 (있으면)
3. Telegram으로 미리보기 + [게시] 버튼
4. 승인 시 → POST /api/news
5. [자동] 마케팅 에이전트에 알림:
   "새 공지 게시됨 → SNS 공유 포스트 생성"
```

### 공지 카테고리별 템플릿

**전시 공지:**
```
[Sun Art Center] {작가} 개인전 '{전시명}' 안내

Sun Art Center에서 {작가} 작가의 개인전 '{전시명}'을 개최합니다.

■ 전시 정보
- 전시명: {전시명}
- 작가: {작가}
- 기간: {시작일} - {종료일}
- 장소: Sun Art Center {층}
- 관람시간: 화-일 10:00-18:00 (월요일 휴관)
- 관람료: 무료

■ 오프닝 리셉션
- 일시: {날짜} {시간}
- 작가와의 대화: {시간}

많은 관심과 방문 부탁드립니다.
```

**운영 공지:**
```
[Sun Art Center] {제목}

안녕하세요, Sun Art Center입니다.

{본문}

문의: sungallery1977@gmail.com / 02-734-0458
```

**휴관 공지:**
```
[Sun Art Center] 휴관 안내

{날짜} {사유}로 인해 휴관합니다.
정상 운영은 {재개일}부터입니다.

불편을 끼쳐 드려 죄송합니다.
```

## 마케팅 에이전트 연동 프로토콜

어드민 에이전트와 마케팅 에이전트는 `agent_state.json`의 pending_approvals를 통해 소통합니다.

### 어드민 → 마케팅 트리거

| 이벤트 | task_type | 마케팅 에이전트 동작 |
|--------|-----------|---------------------|
| 전시 이미지 업데이트 | `cross_exhibition_image_updated` | 해당 전시 SNS 포스트 재생성 |
| 공간 이미지 업데이트 | `cross_space_image_updated` | Space Highlight 포스트 소재 갱신 |
| 새 공지 게시 | `cross_news_published` | SNS 공유 포스트 생성 |
| 새 전시 등록 | `cross_exhibition_created` | 전시 홍보 포스트 시리즈 생성 |
| 전시 상태 변경 | `cross_exhibition_status_changed` | "Now Open" 포스트 생성 |

### 마케팅 → 어드민 트리거

| 이벤트 | task_type | 어드민 에이전트 동작 |
|--------|-----------|---------------------|
| SNS 콘텐츠 승인됨 | `cross_sns_content_approved` | 홈페이지 News에 동일 내용 게시 고려 |
| 이미지 필요 | `cross_image_needed` | 사용자에게 이미지 요청, 업로드 후 URL 공유 |

## 참조 파일
- `scripts/sac_website_api.py` — API 클라이언트 (이미지/뉴스/전시 관리 메서드 포함)
- `scripts/sns_marketing.py` — SNS 콘텐츠 큐 (연동 시 참조)
- `scripts/agent_state.py` — 에이전트 간 상태 공유
- `.claude/skills/sns-marketing/SKILL.md` — 마케팅 에이전트 스킬 (연동 참조)
