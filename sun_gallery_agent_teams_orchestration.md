# 선화랑 에이전틱 AI — Agent Teams 엔드투엔드 개발 가이드

## 사전 준비

```bash
# 1. 프로젝트 폴더 생성
mkdir sun-gallery-agent && cd sun-gallery-agent
git init

# 2. 갤러리 컨텍스트 파일 배치
mkdir -p context
# sun_gallery_agent_context_v3.md → context/ 폴더에 복사

# 3. settings.json 생성
mkdir -p .claude
```

## .claude/settings.json

```json
{
  "env": {
    "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1"
  },
  "permissions": {
    "allow": [
      "Bash(npm install*)",
      "Bash(pip install*)",
      "Bash(python*)",
      "Bash(node*)",
      "Bash(bun*)",
      "Bash(npx*)",
      "Bash(mkdir*)",
      "Bash(cp*)",
      "Bash(cat*)",
      "Bash(ls*)",
      "Bash(cd*)",
      "Bash(pytest*)"
    ]
  }
}
```

## CLAUDE.md

```markdown
# Sun Gallery Agent — 선화랑 AI 어시스턴트

## 프로젝트 목적
선화랑(Sun Gallery)의 이메일/WhatsApp/마케팅/문서 업무를 AI로 자동화하는 에이전틱 시스템.
FastAPI 백엔드 + React 프론트엔드 + Claude API 연동 + Claude Code Skills/Channels/Scheduled Tasks.

## 프로젝트 구조
sun-gallery-agent/
├── CLAUDE.md
├── context/
│   └── sun_gallery_agent_context_v3.md   ← 갤러리 컨텍스트 (절대 수정 금지)
├── backend/
│   ├── main.py                           ← FastAPI 서버
│   ├── agent.py                          ← Claude API 호출 + 컨텍스트 주입
│   ├── models.py                         ← Pydantic 모델
│   ├── routers/
│   │   ├── email.py                      ← /api/email-draft
│   │   ├── whatsapp.py                   ← /api/whatsapp-reply  
│   │   ├── marketing.py                  ← /api/marketing-content
│   │   ├── document.py                   ← /api/gallery-document
│   │   ├── translate.py                  ← /api/translate
│   │   └── fair.py                       ← /api/fair-prep
│   ├── data/
│   │   ├── artists.json
│   │   ├── collectors.json
│   │   ├── inventory.json
│   │   └── fair_schedule.json
│   ├── tests/
│   │   ├── test_agent.py
│   │   ├── test_email.py
│   │   └── test_whatsapp.py
│   └── requirements.txt
├── frontend/
│   ├── package.json
│   ├── src/
│   │   ├── App.jsx
│   │   ├── components/
│   │   │   ├── Dashboard.jsx             ← 메인 대시보드
│   │   │   ├── ModeSelector.jsx          ← 모드 선택 (이메일/WhatsApp/마케팅...)
│   │   │   ├── InputPanel.jsx            ← 요청 입력
│   │   │   ├── OutputPanel.jsx           ← AI 응답 표시 + 복사/발송 버튼
│   │   │   ├── CollectorList.jsx         ← 고객 관리 (CRM)
│   │   │   ├── FairSchedule.jsx          ← 페어 일정
│   │   │   └── SettingsPage.jsx          ← 갤러리 컨텍스트 편집
│   │   └── styles/
│   └── vite.config.js
├── .claude/
│   ├── skills/
│   │   ├── email-draft/SKILL.md
│   │   ├── whatsapp-reply/SKILL.md
│   │   ├── marketing-content/SKILL.md
│   │   ├── gallery-document/SKILL.md
│   │   ├── translate-art/SKILL.md
│   │   ├── fair-prep/SKILL.md
│   │   └── gallery-context/SKILL.md
│   └── settings.json
└── README.md

## 핵심 원칙
1. 갤러리 컨텍스트 (context/sun_gallery_agent_context_v3.md)를 모든 API 호출 시 system prompt로 주입
2. 내부 전략(섹션 13)은 대외 출력에 절대 포함 금지
3. Human-in-the-loop: AI가 직접 발송하지 않음, 항상 사람이 확인 후 전송
4. 간결함 우선: 이메일은 핵심만, WhatsApp은 3-5문장
5. 기본 발신자: 이준화 (Joonwha Lee)

## 기술 스택
- Backend: Python 3.11+ / FastAPI / uvicorn
- Frontend: React 18+ / Vite / Tailwind CSS
- AI: Claude API (anthropic SDK) / claude-sonnet-4-6
- Data: JSON 파일 기반 (추후 DB 마이그레이션 가능)
- Testing: pytest (backend) / vitest (frontend)

## 작가명 표기 주의
- 이정지 = Lee Chungji (NOT 이충지)
- 수수료: 국내 50:50 / 해외(한/대만/홍콩/일본 제외) 60:40 / 어드바이저 경유 45:55 (case by case)

## 검증 명령어
- Backend: cd backend && pytest
- Frontend: cd frontend && npm test
- Lint: cd backend && ruff check .
- Full: cd backend && pytest && cd ../frontend && npm test
```

---

## Agent Teams 오케스트레이션 프롬프트

Claude Code를 실행한 후, 아래 프롬프트를 입력합니다:

```
이 프로젝트는 선화랑(Sun Gallery)의 에이전틱 AI 어시스턴트입니다.
context/sun_gallery_agent_context_v3.md 파일을 먼저 읽어서 갤러리의 
전체 맥락을 이해하세요.

Agent Team을 만들어서 엔드투엔드로 개발을 완료해주세요.
4명의 팀원을 스폰합니다:

1. **Backend Engineer** — FastAPI 백엔드 전체 구현
   - backend/main.py: FastAPI 앱, CORS 설정
   - backend/agent.py: Claude API 호출 로직
     * context/sun_gallery_agent_context_v3.md를 읽어서 system prompt로 주입
     * 모드별(email, whatsapp, marketing, document, translate, fair-prep) 프롬프트 템플릿 관리
     * 섹션 13(내부 전략)을 대외 출력에서 필터링하는 로직 포함
   - backend/models.py: Pydantic 모델 (요청/응답 스키마)
   - backend/routers/: 모드별 API 엔드포인트 6개
   - backend/data/: 
     * artists.json — context 파일에서 작가 로스터 추출하여 초기 데이터 생성
     * collectors.json — Ahmed, Jason 등 실제 고객 데이터 포함
     * inventory.json — 샘플 작품 데이터
     * fair_schedule.json — 2026 페어 일정 (Art Basel HK, Art Central HK 등)
   - backend/requirements.txt: fastapi, uvicorn, anthropic, pydantic, pytest, ruff
   - backend/tests/: 각 라우터 + agent.py 테스트
   - 파일 경계: backend/ 폴더만 수정

2. **Frontend Engineer** — React 대시보드 UI 전체 구현
   - Vite + React 18 + Tailwind CSS
   - 컴포넌트: Dashboard, ModeSelector, InputPanel, OutputPanel, CollectorList, FairSchedule, SettingsPage
   - Dashboard: 왼쪽에 모드 선택, 오른쪽에 입출력 패널
   - ModeSelector: 6개 모드 (이메일 드래프트, WhatsApp 답장, 마케팅 콘텐츠, 갤러리 문서, 번역, 페어 준비)
   - OutputPanel: AI 응답 표시 + "복사" 버튼 + "이메일로 보내기" 버튼
   - CollectorList: data/collectors.json 조회/편집 UI
   - FairSchedule: data/fair_schedule.json 기반 달력/타임라인 뷰
   - SettingsPage: 갤러리 컨텍스트 파일 내용 표시 + 편집 가능한 textarea
   - 갤러리 브랜딩: 골드(#C5A572) + 차콜(#2C2C2A) + 화이트 컬러 스킴
   - 반응형: 데스크탑 + 태블릿
   - 파일 경계: frontend/ 폴더만 수정

3. **Skills Engineer** — Claude Code 스킬 6종 + 데이터 파일
   - .claude/skills/ 폴더에 7개 스킬 생성:
     * email-draft/SKILL.md — 수신자 유형별 톤 자동 조절, 템플릿 참조
     * whatsapp-reply/SKILL.md — 3-5문장 강제, 간결함 규칙
     * marketing-content/SKILL.md — SNS 포스트, 뉴스레터, 작가 소개
     * gallery-document/SKILL.md — 인보이스, Condition Report, CoA, Sale Offer
     * translate-art/SKILL.md — 미술 전문 용어 KR↔EN↔AR
     * fair-prep/SKILL.md — before/after/checklist 3가지 모드
     * gallery-context/SKILL.md — user-invocable: false, 배경지식 자동 로드
   - 각 스킬의 description은 자연어 트리거에 최적화
   - context 파일의 섹션 7(커뮤니케이션 가이드)을 스킬에 녹여넣기
   - 파일 경계: .claude/skills/ 폴더만 수정

4. **QA & Integration** — 테스트 + 통합 검증 + README
   - Backend 테스트 실행 및 검증 (pytest)
   - Frontend 빌드 검증 (npm run build)
   - Backend↔Frontend API 연동 테스트
   - 각 모드별 실제 시나리오 테스트:
     * "Ahmed에게 이영지 작품 팔로업 이메일" → 갤러리 톤 확인
     * "Art Basel HK 부스 방문 WhatsApp 초대" → 3-5문장 확인
     * "이정지 작가 Condition Report 생성" → 문서 형식 확인
   - 섹션 13 내부 전략이 출력에 노출되지 않는지 검증
   - README.md 작성 (설치 방법, 실행 방법, 스킬 사용법)
   - 파일 경계: tests/, README.md, 통합 검증만

팀 리드인 나는 delegate mode로 코디네이션만 합니다.
각 팀원은 독립적으로 작업하되, Backend/Frontend 간 API 스키마는 
Backend Engineer가 먼저 models.py를 완성한 후 Frontend Engineer에게 공유하세요.
QA는 다른 3명의 작업이 완료된 후 통합 검증을 시작하세요.

작업 완료 후 각 팀원은 자신의 테스트를 먼저 돌리고, 
모두 통과하면 QA에게 알려주세요.
```

---

## 작업 흐름 (예상 타임라인)

```
Phase 1: 병렬 개발 (Backend + Frontend + Skills 동시)
┌─────────────────────────────────────────────────────────────┐
│ Lead (You)                                                  │
│  - delegate mode ON                                        │
│  - 진행 상황 모니터링                                         │
├──────────┬──────────┬──────────┬────────────────────────────┤
│ Backend  │ Frontend │ Skills   │ QA (대기)                   │
│          │          │          │                            │
│ main.py  │ Vite     │ email-   │ ⏳ Waiting for             │
│ agent.py │ setup    │  draft   │    Phase 1 completion      │
│ models.py│ App.jsx  │ whatsapp │                            │
│ routers/ │ Dash-    │ market-  │                            │
│ data/    │  board   │  ing     │                            │
│ tests/   │ Panels   │ document │                            │
│          │ CRM UI   │ translate│                            │
│          │ Fair UI  │ fair-prep│                            │
│          │          │ context  │                            │
├──────────┴──────────┴──────────┤                            │
│ ✅ models.py 공유 → Frontend   │                            │
└────────────────────────────────┴────────────────────────────┘

Phase 2: 통합 검증 (QA 활성화)
┌─────────────────────────────────────────────────────────────┐
│ QA & Integration                                           │
│  - pytest 실행                                              │
│  - npm run build 확인                                       │
│  - API 연동 테스트                                           │
│  - 시나리오 테스트 (이메일, WhatsApp, 문서)                     │
│  - 내부 전략 노출 여부 검증                                    │
│  - README.md 작성                                           │
│                                                             │
│  버그 발견 시 → 해당 팀원에게 메시지로 수정 요청                  │
└─────────────────────────────────────────────────────────────┘

Phase 3: 완료
┌─────────────────────────────────────────────────────────────┐
│ Lead                                                        │
│  - 최종 확인                                                 │
│  - git commit -m "feat: Sun Gallery Agent v1.0"             │
└─────────────────────────────────────────────────────────────┘
```

---

## 실행 방법

```bash
# 1. 프로젝트 폴더에서 tmux 세션 시작 (스플릿 팬 사용 권장)
tmux new-session -s sun-gallery

# 2. Claude Code 실행
claude

# 3. 위의 Agent Teams 오케스트레이션 프롬프트 입력
# → Claude가 4명의 팀원을 스폰하고 작업 시작

# 4. 팀원 간 전환: Shift+Down/Up (in-process) 또는 tmux pane 클릭 (split)

# 5. 작업 완료 후 테스트
cd backend && pytest
cd ../frontend && npm run build

# 6. 로컬 실행
# 터미널 1:
cd backend && uvicorn main:app --reload --port 8000
# 터미널 2:
cd frontend && npm run dev
# → http://localhost:5173 에서 대시보드 확인
```

---

## 개발 완료 후 추가 설정

### Telegram Channel 연동
```bash
/plugin install telegram@claude-plugins-official
/telegram:configure
# → 봇 토큰 입력
claude --channels plugin:telegram@claude-plugins-official
```

### Scheduled Tasks (Desktop)
```
"매일 오전 9시에 data/fair_schedule.json을 확인해서
2주 이내 페어가 있으면 준비 상태 알려줘.
data/collectors.json에서 7일 이상 팔로업 안 한 고객도 알려줘."
```

### 스킬 테스트
```bash
/email-draft Ahmed에게 이영지 작품 팔로업
/whatsapp-reply Andrew에게 Art Basel HK 부스 방문 초대
/fair-prep before "Art Basel Hong Kong 2026"
/gallery-document Condition Report for 김정수 Azalea-Blessing
/translate-art "이정지는 한국 유일의 여성 단색화 작가입니다" to English
/marketing-content Prospective 2026 전시 인스타그램 포스트
```
