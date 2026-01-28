# Frontend Development Guide

## 개발 서버 시작

```bash
cd frontend
npm run dev
```

서버는 **http://localhost:5110**에서 실행됩니다.

## 주요 페이지

### 메인 페이지
- URL: http://localhost:5110
- 기능: 전체 종목 목록, 시그널 현황

### 종목 상세 페이지
- URL: http://localhost:5110/stock/[ticker]
- 예: http://localhost:5110/stock/005930 (삼성전자)
- 기능:
  - 기본 차트 (일봉, 거래량)
  - 수급 차트 (외국인/기관 순매수)
  - 시그널 히스토리 (VCP, 종가베팅 V2)
  - 수익률 분석 (승률, MDD, 누적 수익률)
  - 기술적 지표 (RSI, MACD, 볼린저 밴드, 52주 신고가/신저가)
  - 관련 뉴스 (감성 분석, 키워드)

## API 백엔드 연결

프론트엔드는 다음 API 엔드포인트에 연결됩니다:

- **API Gateway**: http://localhost:5111
- **VCP Scanner**: http://localhost:5112
- **Signal Engine**: http://localhost:5113

환경 변수: `NEXT_PUBLIC_API_URL=http://localhost:5111`

## 포트 변경 내역

포트 충돌을 방지하기 위해 다음과 같이 변경되었습니다:

| 서비스 | 기존 포트 | 새 포트 |
|--------|-----------|---------|
| API Gateway | 8000 | 5111 |
| VCP Scanner | 8001 | 5112 |
| Signal Engine | 8003 | 5113 |
| Frontend | - | 5110 |

## 테스트

```bash
# 단위 테스트
npm test

# E2E 테스트
npm run test:e2e

# 커버리지
npm run test:coverage
```
