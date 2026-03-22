---
description: "인보이스, Condition Report, CoA, Sale Offer 생성"
---

# Gallery Document Skill

Sun Gallery 공식 문서를 생성합니다.

## 사용법
인보이스, Condition Report, Certificate of Authenticity, Sale Offer 등 요청 시 활성화됩니다.

## 문서 유형

### Invoice (인보이스)
- 작품명, 작가명, 매체, 크기, 제작연도
- 가격 (USD 기준)
- 결제 조건

### Condition Report (상태 보고서)
- 작품의 물리적 상태 기술
- 갤러리 대표가 배송 전 최종 검수

### Certificate of Authenticity (진위 확인서)
- 작가명, 작품명, 매체, 크기, 제작연도
- 갤러리 인증 문구

### Sale Offer (판매 제안서)
- 작품 정보 + 거래 조건

## 기본 거래 조건
- **수령**: Buyer가 직접 갤러리 스토리지에서 수거 (buyer-arranged collection)
- **결제**: 결제 완료 후 수령 원칙
- **환불**: 수령 후 반품 불가
- **손상 클레임**: 수령 후 48시간 이내
- **UAE 거래**: 관세 5% + VAT 5% = 10.25% (CIF 기준)

## 수수료 구조
- 국내 (한국/대만/홍콩/일본): 50:50
- 해외 (위 제외): 60:40

### 참조
- `context/sun_gallery_agent_context_v3.md` 파일을 참조합니다
