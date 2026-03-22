# Sun Gallery AI Assistant (선화랑 에이전틱 AI)

Sun Gallery의 이메일, WhatsApp, 마케팅, 문서, 번역, 아트페어 업무를 AI로 자동화하는 웹 기반 어시스턴트입니다.

FastAPI 백엔드 + React 프론트엔드 + Claude API 연동 + Claude Code Skills로 구성되어 있습니다.

## 설치

### Backend
```bash
cd backend
pip install -r requirements.txt
```

### Frontend
```bash
cd frontend
npm install
```

### 환경변수
```bash
cp .env.example .env
# .env 파일에 ANTHROPIC_API_KEY를 설정하세요
```

## 실행

### Backend 서버
```bash
cd backend
uvicorn main:app --reload
```
서버가 http://localhost:8000 에서 실행됩니다.

### Frontend 개발 서버
```bash
cd frontend
npm run dev
```
http://localhost:5173 에서 프론트엔드가 실행됩니다.

## API 엔드포인트

| 엔드포인트 | 메서드 | 설명 |
|-----------|--------|------|
| `/api/email-draft` | POST | 이메일 드래프트 생성 |
| `/api/whatsapp-reply` | POST | WhatsApp 답장 생성 |
| `/api/marketing-content` | POST | 마케팅 콘텐츠 생성 |
| `/api/gallery-document` | POST | 갤러리 문서 생성 |
| `/api/translate` | POST | 미술 전문 번역 |
| `/api/fair-prep` | POST | 아트페어 준비 |
| `/api/data/collectors` | GET | 컬렉터 목록 |
| `/api/data/fairs` | GET | 페어 일정 |
| `/api/data/artists` | GET | 작가 목록 |
| `/api/data/inventory` | GET | 작품 인벤토리 |
| `/api/health` | GET | 헬스체크 |

### 요청 형식 (POST)
```json
{
  "mode": "email",
  "message": "Write a follow-up email to Ahmed about Youngji Lee paintings",
  "recipient": "Ahmed",
  "sender": "Joonwha Lee",
  "language": "en"
}
```

## Claude Code Skills

| 스킬 | 설명 |
|------|------|
| `/email-draft` | 이메일 드래프트 생성 (수신자 유형별 톤 자동 조절) |
| `/whatsapp-reply` | WhatsApp 답장 (3-5문장 이내) |
| `/marketing-content` | SNS 포스트, 뉴스레터, 작가 소개문 |
| `/gallery-document` | 인보이스, Condition Report, CoA, Sale Offer |
| `/translate-art` | 미술 전문 번역 (KR↔EN↔AR) |
| `/fair-prep` | 아트페어 준비 (before/after/checklist) |

## 환경변수

| 변수 | 설명 |
|------|------|
| `ANTHROPIC_API_KEY` | Claude API 키 (필수) |

## 기술 스택

- **Backend**: Python 3.11+ / FastAPI / uvicorn / anthropic SDK
- **Frontend**: React 18 / Vite / Tailwind CSS
- **AI Model**: claude-sonnet-4-6
- **Data**: JSON 파일 기반
- **Testing**: pytest
