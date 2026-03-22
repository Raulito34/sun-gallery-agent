# Sun Gallery Agent — 선화랑 AI 어시스턴트

## 프로젝트 목적
선화랑(Sun Gallery)의 이메일/WhatsApp/마케팅/문서 업무를 AI로 자동화하는 웹 기반 에이전틱 시스템.
FastAPI 백엔드 + React 프론트엔드 + Claude API 연동 + Claude Code Skills.

## 프로젝트 구조
```
sun-gallery-agent/
├── CLAUDE.md
├── context/
│   └── sun_gallery_agent_context_v3.md   ← 갤러리 컨텍스트 (절대 수정 금지)
├── backend/
│   ├── main.py                           ← FastAPI 서버, CORS
│   ├── agent.py                          ← Claude API 호출 + 컨텍스트 주입
│   ├── models.py                         ← Pydantic 모델 (요청/응답)
│   ├── routers/
│   │   ├── email.py                      ← POST /api/email-draft
│   │   ├── whatsapp.py                   ← POST /api/whatsapp-reply
│   │   ├── marketing.py                  ← POST /api/marketing-content
│   │   ├── document.py                   ← POST /api/gallery-document
│   │   ├── translate.py                  ← POST /api/translate
│   │   └── fair.py                       ← POST /api/fair-prep
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
│   ├── vite.config.js
│   ├── index.html
│   ├── tailwind.config.js
│   └── src/
│       ├── App.jsx
│       ├── main.jsx
│       ├── index.css
│       └── components/
│           ├── Dashboard.jsx             ← 메인 레이아웃
│           ├── ModeSelector.jsx          ← 6개 모드 선택
│           ├── InputPanel.jsx            ← 요청 입력 (수신자, 내용, 옵션)
│           ├── OutputPanel.jsx           ← AI 응답 + 복사/발송 버튼
│           ├── CollectorList.jsx         ← 고객 리스트 (CRM)
│           ├── FairSchedule.jsx          ← 페어 일정 타임라인
│           └── SettingsPage.jsx          ← 갤러리 컨텍스트 편집
├── .claude/
│   └── skills/
│       ├── email-draft/SKILL.md
│       ├── whatsapp-reply/SKILL.md
│       ├── marketing-content/SKILL.md
│       ├── gallery-document/SKILL.md
│       ├── translate-art/SKILL.md
│       ├── fair-prep/SKILL.md
│       └── gallery-context/SKILL.md
└── README.md
```

## 핵심 원칙
1. **갤러리 컨텍스트 필수 참조**: 모든 API 호출 시 context/sun_gallery_agent_context_v3.md를 system prompt로 주입
2. **내부 전략 비공개**: 컨텍스트 섹션 13의 내용은 대외 출력에 절대 포함 금지. agent.py에서 섹션 13을 system prompt에서 제외하는 필터링 로직 구현
3. **Human-in-the-loop**: AI가 직접 발송하지 않음. 드래프트만 생성하고 사람이 확인 후 전송
4. **간결함 우선**: 이메일은 핵심만, WhatsApp은 3-5문장 이내

## 기술 스택
- Backend: Python 3.11+ / FastAPI / uvicorn / anthropic SDK
- Frontend: React 18 / Vite / Tailwind CSS
- AI Model: claude-sonnet-4-6 (Claude API)
- Data: JSON 파일 기반
- Testing: pytest (backend)

## agent.py 핵심 로직
```python
# 갤러리 컨텍스트 로드 시:
# 1. context/sun_gallery_agent_context_v3.md 전체를 읽음
# 2. "## 13. 내부 전략" 부터 다음 "---" 까지를 제거 (대외 출력 방지)
# 3. 모드별 추가 프롬프트를 append
# 4. Claude API messages.create()에 system= 파라미터로 주입
```

## 모드별 API 엔드포인트
| 모드 | 엔드포인트 | 설명 |
|------|-----------|------|
| 이메일 드래프트 | POST /api/email-draft | 수신자 유형별 톤 자동 조절, Subject line 포함 |
| WhatsApp 답장 | POST /api/whatsapp-reply | 3-5문장 강제, 간결 |
| 마케팅 콘텐츠 | POST /api/marketing-content | SNS 포스트, 뉴스레터, 작가 소개 |
| 갤러리 문서 | POST /api/gallery-document | 인보이스, Condition Report, CoA |
| 번역 | POST /api/translate | 미술 전문 용어 KR↔EN↔AR |
| 페어 준비 | POST /api/fair-prep | before/after/checklist 모드 |

## 데이터 파일 초기화
- artists.json: context 파일의 섹션 2(소속 작가) 전체 로스터 추출
- collectors.json: Ahmed(UAE, 이영지 관심), Jason(UK, 이정지 관심, 런던 거주) 등 실제 데이터
- inventory.json: 주요 작가별 샘플 작품 3-5점
- fair_schedule.json: 2026 페어 일정 (Art Basel HK 3/25-29 부스 3D28, Art Central HK 3/24-29 부스 B2, Galleries Art Fair 4/8-12, Expo Chicago 4/9-12)

## 프론트엔드 디자인
- 컬러 스킴: 골드(#C5A572) + 차콜(#2C2C2A) + 화이트(#FFFFFF) + 라이트그레이(#F5F5F0)
- 폰트: 제목 Playfair Display, 본문 Inter
- 레이아웃: 왼쪽 사이드바(모드 선택 + 네비게이션) + 오른쪽 메인 영역(입출력)
- 반응형: 데스크탑 + 태블릿

## 기본 발신자 정보
- 이름: Joonwha Lee (이준화)
- 직책: Manager
- 갤러리: Sun Gallery | Seoul, Korea
- 이메일: sungallery1977@gmail.com
- 전화: +82 2-734-0458

## 작가명 표기 주의
- 이정지 = Lee Chungji (NOT 이충지)
- 수수료: 국내 50:50 / 해외(한/대만/홍콩/일본 제외) 60:40

## 검증 명령어
- Backend: cd backend && pip install -r requirements.txt && pytest
- Frontend: cd frontend && npm install && npm run build
