# KR Stock API Gateway 가이드

한국 주식 분석 시스템 API Gateway의 공식 API 가이드 문서입니다.

> **전체 문서**: `docs/archive_originals/API_GUIDE.md` (1076줄)

## 시작하기

### Base URL
```
http://localhost:5111
```

### 포트 구성
| 서비스 | 포트 | 설명 |
|--------|------|------|
| Frontend (Next.js) | 5110 | React 기반 웹 UI |
| API Gateway | 5111 | 메인 API 엔드포인트 |
| VCP Scanner | 5112 | VCP 패턴 스캔 서비스 |
| Signal Engine | 5113 | 종가베팅 V2 시그널 생성 |
| Chatbot Service | 5114 | AI 챗봇 서비스 |

### Interactive Docs
- **Swagger UI**: `http://localhost:5111/docs`
- **ReDoc**: `http://localhost:5111/redoc`

---

## API 엔드포인트

### 1. 헬스 체크
| 엔드포인트 | 메서드 | 설명 |
|-----------|--------|------|
| `/health` | GET | 서비스 상태 확인 |
| `/` | GET | 기본 정보 |

### 2. 시스템 상태
| 엔드포인트 | 메서드 | 설명 |
|-----------|--------|------|
| `/api/system/health` | GET | 전체 시스템 건강 상태 |
| `/api/system/data-status` | GET | 데이터 상태 조회 |
| `/api/system/update-data-stream` | POST | 가격 데이터 업데이트 |

### 3. 시그널 조회
| 엔드포인트 | 메서드 | 설명 |
|-----------|--------|------|
| `/api/kr/signals` | GET | 활성 VCP 시그널 목록 |
| `/api/kr/signals/{ticker}` | GET | 특정 종목 시그널 |

### 4. Market Gate
| 엔드포인트 | 메서드 | 설명 |
|-----------|--------|------|
| `/api/kr/market-gate` | GET | 시장 상태 점수 |
| `/api/kr/market-gate/sectors` | GET | 섹터별 상태 |

### 5. 종목/차트
| 엔드포인트 | 메서드 | 설명 |
|-----------|--------|------|
| `/api/kr/stocks/{ticker}` | GET | 종목 상세 |
| `/api/kr/stocks/{ticker}/chart` | GET | 종목 차트 데이터 |
| `/api/kr/stocks/{ticker}/flow` | GET | 수급 데이터 |

### 6. 실시간 가격
| 엔드포인트 | 메서드 | 설명 |
|-----------|--------|------|
| `/api/kr/prices` | POST | 실시간 가격 조회 |
| `/ws` | WS | WebSocket 연결 |

### 7. AI 분석
| 엔드포인트 | 메서드 | 설명 |
|-----------|--------|------|
| `/api/kr/ai-analysis` | GET | AI 분석 목록 |
| `/api/kr/ai-summary/{ticker}` | GET | 종목 AI 요약 |
| `/api/kr/ai-analyze/{ticker}` | POST | AI 분석 트리거 |

### 8. 백테스트
| 엔드포인트 | 메서드 | 설명 |
|-----------|--------|------|
| `/api/kr/backtest` | GET | 백테스트 결과 |
| `/api/kr/backtest-summary` | GET | 백테스트 요약 |

### 9. 스캔 트리거
| 엔드포인트 | 메서드 | 설명 |
|-----------|--------|------|
| `/api/kr/scan/vcp` | POST | VCP 스캔 트리거 |
| `/api/kr/scan/signals` | POST | 시그널 생성 트리거 |
| `/api/kr/scan/status` | GET | 스캔 상태 |

### 10. 챗봇
| 엔드포인트 | 메서드 | 설명 |
|-----------|--------|------|
| `/api/kr/chatbot/chat` | POST | 챗봇 질의응답 |
| `/api/kr/chatbot/context` | POST | 질문 기반 컨텍스트 검색 |
| `/api/kr/chatbot/context` | GET | 세션 기반 대화 기록 조회 |
| `/api/kr/chatbot/recommendations` | GET | 종목 추천 조회 |
| `/api/kr/chatbot/session/{id}` | GET | 세션 정보 조회 |
| `/api/kr/chatbot/session/{id}` | DELETE | 세션 삭제 |
| `/api/kr/chatbot/health` | GET | 챗봇 서비스 헬스 체크 |

#### 요청 예시

**채팅 요청:**
```json
POST /api/kr/chatbot/chat
{
  "message": "삼성전자 현재가 알려줘",
  "session_id": "user-session-123"  // 선택사항
}
```

**응답:**
```json
{
  "reply": "삼성전자(005930)의 현재가는 82,400원입니다.",
  "suggestions": [
    "삼성전자 목표가",
    "삼성전자 최신 뉴스",
    "삼성전자 VCP 시그널"
  ],
  "session_id": "user-session-123",
  "timestamp": "2026-01-30T10:00:00"
}
```

**종목 추천:**
```json
GET /api/kr/chatbot/recommendations?strategy=both&limit=5
```

**응답:**
```json
[
  {
    "ticker": "005930",
    "name": "삼성전자",
    "signal_type": "vcp",
    "grade": "A",
    "score": 85,
    "position_size": 12.0
  }
]
```

---

## 상태 코드
| 코드 | 설명 |
|------|------|
| 200 | 성공 |
| 400 | 잘못된 요청 |
| 404 | 리소스 없음 |
| 429 | Rate Limit 초과 |
| 500 | 서버 에러 |

---

## 주요 응답 모델

### SignalResponse
```json
{
  "ticker": "005930",
  "name": "삼성전자",
  "grade": "A",
  "entry_price": 75000,
  "target_price": 85000,
  "stop_price": 72000
}
```

### MarketGateResponse
```json
{
  "score": 65,
  "label": "YELLOW",
  "status": "caution"
}
```
