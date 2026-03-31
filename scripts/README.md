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

### AI 콘텐츠 생성

| 명령어 | 설명 | 예시 |
|--------|------|------|
| `/email <내용>` | 이메일 드래프트 생성 | `/email Ahmed에게 Art Central HK 초대` |
| `/whatsapp <내용>` | WhatsApp 답장 | `/whatsapp Jason에게 이정지 작품 가격 안내` |
| `/marketing <내용>` | 마케팅 콘텐츠 | `/marketing Art Basel HK 인스타 포스트` |
| `/document <내용>` | 문서 생성 | `/document 이영지 Tree and Bird Sale Offer` |
| `/translate <내용>` | 미술 번역 | `/translate 이정지 작가 소개문을 아랍어로` |
| `/fair <내용>` | 페어 준비 | `/fair Art Central HK 사전 체크리스트` |

### 실제 이메일 연동 (네이버 웍스)

| 명령어 | 설명 | 예시 |
|--------|------|------|
| `/inbox` | 안 읽은 메일 확인 | |
| `/reply <번호>` | 수신 메일에 AI 답장 생성 | `/reply 1` |
| `/sendmail <to> <제목> \| <본문>` | 메일 직접 발송 | `/sendmail a@b.com Hello \| Dear...` |

### WhatsApp 연동

| 명령어 | 설명 | 예시 |
|--------|------|------|
| `/wa <번호> <메시지>` | WhatsApp 메시지 발송 | `/wa +971501234567 Hello` |

### 조회

| 명령어 | 설명 |
|--------|------|
| `/collectors` | 팔로업 필요 고객 목록 |
| `/fairs` | 다가오는 페어 일정 |
| `/scan` | 데일리 스캔 즉시 실행 |
| (일반 텍스트) | 자유 질문 |

## 네이버 웍스 메일 설정

### 사전 조건
- 네이버 웍스 **Standard** 또는 **Standard Plus** 요금제
- 관리자가 IMAP/SMTP 사용을 허용해야 함

### 설정 절차
1. **관리자 설정**: 관리자 > 보안 > 서비스 권한 > 메일 > IMAP/SMTP 사용 허용
2. **외부 앱 비밀번호 생성**: 설정 > 보안 > 외부 앱 비밀번호 > 비밀번호 생성
3. **환경변수 설정**:
   ```bash
   export NAVER_WORKS_EMAIL=joonwha@sungallery.com
   export NAVER_WORKS_PASSWORD=생성된-외부-앱-비밀번호
   ```

### 서버 정보
| 프로토콜 | 서버 | 포트 | 보안 |
|---------|------|------|------|
| IMAP | `imap.worksmobile.com` | 993 | SSL |
| SMTP | `smtp.worksmobile.com` | 587 | TLS |

## WhatsApp Business API 설정

### 설정 절차
1. [Meta for Developers](https://developers.facebook.com) → 앱 만들기 → WhatsApp 추가
2. WhatsApp > API 설정 > **임시 액세스 토큰** 복사 (테스트용, 24시간 유효)
3. 같은 페이지에서 **전화번호 ID** 복사
4. **환경변수 설정**:
   ```bash
   export WHATSAPP_TOKEN=임시-또는-영구-액세스-토큰
   export WHATSAPP_PHONE_ID=전화번호-ID
   ```

### 영구 토큰 (운영용)
- 비즈니스 설정 > 시스템 사용자 > 토큰 생성
- `whatsapp_business_messaging` 권한 필요

### Webhook (수신 메시지)
WhatsApp 메시지를 수신하려면 FastAPI 서버에 webhook을 등록해야 합니다:
1. FastAPI 서버를 공개 URL로 배포 (ngrok 등)
2. Meta 앱 > WhatsApp > Configuration > Callback URL: `https://your-domain/api/whatsapp-webhook`
3. Verify Token: `WHATSAPP_VERIFY_TOKEN` 환경변수 값과 동일하게 설정

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
