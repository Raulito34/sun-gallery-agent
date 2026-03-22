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

## 로컬 테스트 (Daily Scan)

```bash
export ANTHROPIC_API_KEY=your-key
export TELEGRAM_BOT_TOKEN=your-token
export TELEGRAM_CHAT_ID=your-chat-id
python scripts/daily_scan.py
```

ANTHROPIC_API_KEY가 없으면 fallback으로 기본 텍스트 요약이 생성됩니다.
TELEGRAM_BOT_TOKEN이 없으면 메시지가 stdout에 출력됩니다.

---

# Interactive Telegram Bot — 양방향 대화형 봇

Telegram 채팅으로 갤러리 업무 지시를 보내면 Claude API가 처리하여 결과를 반환합니다.

## 실행

```bash
export ANTHROPIC_API_KEY=your-key
export TELEGRAM_BOT_TOKEN=your-token
python scripts/telegram_bot.py
```

봇이 시작되면 Telegram에서 메시지를 보내 업무를 지시할 수 있습니다.

## 명령어

| 명령어 | 설명 | 예시 |
|--------|------|------|
| `/start` | 봇 소개 + 명령어 목록 | |
| `/email <내용>` | 이메일 드래프트 생성 | `/email Ahmed에게 Art Central HK 초대` |
| `/whatsapp <내용>` | WhatsApp 답장 | `/whatsapp Jason에게 이정지 작품 가격 안내` |
| `/marketing <내용>` | 마케팅 콘텐츠 | `/marketing Art Basel HK 인스타 포스트` |
| `/document <내용>` | 문서 생성 | `/document 이영지 Tree and Bird Sale Offer` |
| `/translate <내용>` | 미술 번역 | `/translate 이정지 작가 소개문을 아랍어로` |
| `/fair <내용>` | 페어 준비 | `/fair Art Central HK 사전 체크리스트` |
| `/collectors` | 팔로업 필요 고객 목록 | |
| `/fairs` | 다가오는 페어 일정 | |
| `/scan` | 데일리 스캔 즉시 실행 | |
| (일반 텍스트) | 자유 질문 | `이영지 작가 최근 페어 실적 알려줘` |

## 상시 실행 방법

봇은 long polling 방식이라 프로세스가 계속 실행되어야 합니다.

### 방법 1: 로컬 PC (간단 테스트)
```bash
python scripts/telegram_bot.py
```

### 방법 2: 백그라운드 실행 (서버)
```bash
nohup python scripts/telegram_bot.py > bot.log 2>&1 &
```

### 방법 3: systemd 서비스 (리눅스 서버 권장)
```ini
# /etc/systemd/system/sun-gallery-bot.service
[Unit]
Description=Sun Gallery Telegram Bot

[Service]
ExecStart=/usr/bin/python3 /path/to/scripts/telegram_bot.py
Environment=ANTHROPIC_API_KEY=your-key
Environment=TELEGRAM_BOT_TOKEN=your-token
Restart=always

[Install]
WantedBy=multi-user.target
```
```bash
sudo systemctl enable --now sun-gallery-bot
```

### 방법 4: Railway / Render (무료 클라우드)
- [Railway](https://railway.app) 또는 [Render](https://render.com)에서 Python 앱으로 배포
- 환경변수에 `ANTHROPIC_API_KEY`, `TELEGRAM_BOT_TOKEN` 설정
- Start command: `python scripts/telegram_bot.py`
