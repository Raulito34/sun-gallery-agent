# Sun Art Center — Claude Code 네이티브 실행 가이드

Claude Max 플랜에서 Claude Code를 직접 사용하여 에이전틱 AI 시스템을 운영하는 방법입니다.
GitHub Actions 대신 Claude Code의 Channels, Scheduled Tasks, Agent Teams 기능을 활용합니다.

## 왜 Claude Code 네이티브?

| | GitHub Actions 봇 | Claude Code 네이티브 |
|---|---|---|
| AI 지능 | Claude API 1회 호출 | 멀티턴 대화, 도구 사용, 코드 실행 |
| 코드 접근 | 불가 | 파일 읽기/수정/git 가능 |
| 외부 연동 | 직접 코딩 필요 | MCP/Channels/Plugins |
| 에이전트 협업 | 불가 | Agent Teams (실험적) |
| 비용 | 무료 (Public repo) | Max 플랜 포함 |

---

## Step 1: 환경변수 설정

터미널에서 `.env` 파일 생성:

```bash
cd sun-gallery-agent
cat > .env << 'EOF'
# 필수
ANTHROPIC_API_KEY=your-api-key

# SAC 웹사이트 API
SAC_API_URL=https://your-app.railway.app
SAC_ADMIN_CODE=your-admin-code

# Telegram (Channel 플러그인이 대체하지만, 기존 봇 호환용)
TELEGRAM_BOT_TOKEN=your-bot-token
TELEGRAM_CHAT_ID=your-chat-id

# 네이버 웍스 (선택)
NAVER_WORKS_EMAIL=
NAVER_WORKS_PASSWORD=

# SNS (계정 생성 후)
INSTAGRAM_ACCESS_TOKEN=
INSTAGRAM_USER_ID=
X_API_KEY=
X_API_SECRET=
X_ACCESS_TOKEN=
X_ACCESS_SECRET=
EOF
```

환경변수 로드:
```bash
source .env
# 또는 direnv를 사용하면 자동 로드
```

---

## Step 2: Telegram Channel 설정 (기존 봇 대체)

Claude Code가 Telegram 메시지를 직접 받고 처리합니다.
자체 봇 코드(`telegram_bot.py`) 없이도 동작합니다.

### 2-1. Bun 설치 (채널 플러그인 필요)
```bash
curl -fsSL https://bun.sh/install | bash
```

### 2-2. Telegram 플러그인 설치
Claude Code에서:
```
/plugin marketplace add anthropics/claude-plugins-official
/plugin install telegram@claude-plugins-official
/reload-plugins
```

### 2-3. 봇 토큰 연결
```
/telegram:configure YOUR_BOT_TOKEN
```

### 2-4. 채널 활성화 상태로 Claude Code 시작
```bash
claude --channels plugin:telegram@claude-plugins-official
```

### 2-5. Telegram에서 봇에게 메시지 → 페어링
봇에게 아무 메시지 → 페어링 코드 수신 → Claude Code에서:
```
/telegram:access pair CODE_HERE
/telegram:access policy allowlist
```

**이제 Telegram 메시지가 Claude Code 세션에 직접 도착합니다.**

---

## Step 3: Scheduled Tasks 설정 (능동 스캔)

Claude Code 세션에서:

```
/loop 30m 아래 작업을 수행해줘:
1. SAC API에서 새 대관 신청 확인 (pending 상태)
2. collectors.json에서 7일 이상 미연락 고객 확인
3. fair_schedule.json에서 D-14/D-7/D-3/D-1 페어 확인
4. 월/수/금이면 SNS 콘텐츠 생성
발견된 항목은 Telegram으로 알려줘.
```

또는 Desktop/Web에서 persistent scheduled task:
```
/schedule
```
→ "30분마다 SAC 대관 + 마케팅 스캔" 설정

---

## Step 4: 사용 방법

### Telegram에서 지시하기

Claude Code Channel이 활성화되면, Telegram에서 자연어로 지시:

```
"SAC에 새로운 대관 신청 있어? 확인해줘"
→ Claude가 SAC API 호출 → 결과 보고

"전시 #3 이미지를 이 URL로 교체해줘: https://..."
→ Claude가 API 호출 → 교체 완료 → SNS 콘텐츠 업데이트 제안

"이번 주 인스타 포스트 만들어줘"
→ Claude가 SAC API에서 전시 조회 → 포스트 생성 → 승인 요청

"대관 #5 승인하고 승인 이메일 보내줘"
→ Claude가 API 상태 업데이트 + 이메일 드래프트 생성
```

### Claude Code에서 직접 사용하기

```bash
claude --channels plugin:telegram@claude-plugins-official
```

세션에서:
```
SAC 사이트의 placeholder 이미지를 확인하고 교체가 필요한 것들을 알려줘

이번 주 전시 캘린더 SNS 포스트를 만들어서 큐에 추가해줘

전시 #2의 공지문을 작성해서 홈페이지에 게시해줘
```

---

## Step 5: Agent Teams (고급 — 실험적)

여러 에이전트가 동시에 작업:

```
에이전트 팀을 만들어줘:
1. 어드민 에이전트: SAC 사이트의 placeholder 이미지 감지 + 공지 작성
2. 마케팅 에이전트: 이번 주 SNS 콘텐츠 3개 시리즈 생성
3. 대관 에이전트: 미처리 대관 신청 검토 + 추천

각자 작업하고 결과를 공유해줘.
```

---

## 기존 코드와의 관계

| 파일 | Claude Code 네이티브에서 | 역할 |
|------|------------------------|------|
| `scripts/sac_website_api.py` | **직접 import하여 사용** | SAC API 호출 |
| `scripts/sns_marketing.py` | **직접 import하여 사용** | 콘텐츠 큐 관리 |
| `scripts/agent_state.py` | **직접 import하여 사용** | 상태 추적 |
| `scripts/telegram_bot.py` | Channel이 대체 (백업용 유지) | — |
| `.claude/skills/*` | **자동 로드** | 지식 + 가이드 |
| `backend/data/*.json` | **직접 읽기/쓰기** | 데이터 |
| `.github/workflows/*` | 사용하지 않음 (백업용 유지) | — |

**핵심**: Claude Code 네이티브에서는 `telegram_bot.py`의 봇 로직이 필요 없습니다.
Claude Code 자체가 Telegram Channel을 통해 메시지를 받고, Skills를 참고하여 판단하고, Python 모듈을 직접 실행합니다.

---

## 비용 참고

- Claude Max: $100/월 (또는 $200/월 5x 사용량)
- SAC API 호출: 무료 (자체 서버)
- Telegram: 무료
- SNS API: 무료 (Free tier)

Max 플랜의 Claude Code 사용량 내에서 모든 에이전트 기능이 동작합니다.
