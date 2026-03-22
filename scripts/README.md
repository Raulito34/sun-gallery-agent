# Proactive Daily Scan — 선제적 알림 시스템

매일 아침 자동으로 고객 팔로업 상태와 페어 일정을 스캔하여 Telegram으로 알림을 보냅니다.

## 동작 방식

1. `backend/data/collectors.json` 스캔 → `last_contact`가 7일 이상 지난 `interested` / `pending_followup` / `vip` 상태 고객 추출
2. `backend/data/fair_schedule.json` 스캔 → 14일 이내 시작하는 페어 추출
3. Claude API로 액션 요약 생성 (한국어+영어 혼용 갤러리 실무 스타일)
4. Telegram Bot API로 알림 전송

## 설정 가이드

### 1. Telegram 봇 만들기

1. Telegram에서 [@BotFather](https://t.me/BotFather)를 검색하여 대화 시작
2. `/newbot` 명령어 입력
3. 봇 이름과 username 설정 (예: `SunGalleryBot`, `sun_gallery_alert_bot`)
4. 발급된 **Bot Token**을 저장 (예: `123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11`)

### 2. Chat ID 확인하기

1. 생성한 봇에게 아무 메시지 전송
2. 브라우저에서 아래 URL 접속 (TOKEN을 실제 토큰으로 교체):
   ```
   https://api.telegram.org/bot<TOKEN>/getUpdates
   ```
3. 응답 JSON에서 `"chat":{"id": 123456789}` 부분의 숫자가 Chat ID

### 3. GitHub Secrets 설정

Repository → Settings → Secrets and variables → Actions → New repository secret

| Secret 이름 | 값 |
|-------------|-----|
| `ANTHROPIC_API_KEY` | Claude API 키 |
| `TELEGRAM_BOT_TOKEN` | Telegram Bot Token |
| `TELEGRAM_CHAT_ID` | Telegram Chat ID |

### 4. 수동 테스트

1. GitHub → Actions 탭 → "Daily Scan — Sun Gallery Proactive Alerts"
2. "Run workflow" 버튼 클릭
3. 로그와 Telegram 메시지 확인

## 예상 비용

| 항목 | 비용 |
|------|------|
| Claude API | ~$0.03/일 (sonnet, ~2K tokens) |
| GitHub Actions | 무료 (public repo) / 2,000분 무료 (private repo) |
| Telegram Bot API | 무료 |

## 로컬 테스트

```bash
export ANTHROPIC_API_KEY=your-key
export TELEGRAM_BOT_TOKEN=your-token
export TELEGRAM_CHAT_ID=your-chat-id
python scripts/daily_scan.py
```

ANTHROPIC_API_KEY가 없으면 fallback으로 기본 텍스트 요약이 생성됩니다.
TELEGRAM_BOT_TOKEN이 없으면 메시지가 stdout에 출력됩니다.
