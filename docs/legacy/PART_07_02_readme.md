# PART 07-2: README (기술 문서)

> **파일**: `README.md`
> **용도**: KR Market Package 기술 문서
> **프레임워크**: Next.js + Flask

---

## 시스템 아키텍처

```
┌─────────────────────────────────────────────────────────────────┐
│                        Next.js Frontend                         │
│                     (http://localhost:3000)                      │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────────┐   │
│  │ VCP 시그널 │ │ 종가베팅  │ │ Market   │ │   Data Status    │   │
│  │  /vcp    │ │/closing  │ │  Gate    │ │   /data-status   │   │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────────┬─────────┘   │
└───────┼────────────┼────────────┼────────────────┼─────────────┘
        │            │            │                │
        ▼            ▼            ▼                ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Flask API Backend                            │
│                    (http://localhost:5001)                       │
│                                                                  │
│  /api/kr/signals     /api/kr/jongga-v2    /api/kr/market-gate   │
│  /api/kr/ai-analysis /api/kr/backtest     /api/system/data-status│
└───────┬─────────────────────────┬────────────────────────────────┘
        │                         │
        ▼                         ▼
┌──────────────────┐    ┌──────────────────────────────────────────┐
│   Data Sources   │    │              AI Analysis                  │
│                  │    │                                          │
│  1. pykrx (KRX)  │    │  ┌─────────────┐ ┌─────────────────────┐ │
│  2. FinanceData  │    │  │   Gemini    │ │      OpenAI GPT     │ │
│     Reader       │    │  │   (필수)    │ │     (선택사항)      │ │
│  3. yfinance     │    │  └─────────────┘ └─────────────────────┘ │
│  4. 네이버 금융  │    └──────────────────────────────────────────┘
└──────────────────┘
```

---

## 분석 엔진 상세

### 1. VCP (Volatility Contraction Pattern) 분석

**파일**: `screener.py` → `SmartMoneyScreener.detect_vcp_pattern()`

```
VCP 감지 로직:
├── ATR(변동성) 점진적 감소 확인
├── 고가-저가 범위 축소 비율 계산
├── 현재가가 최근 고점 근처인지 확인
└── contraction_threshold: 0.7 (70% 이하 축소 시 VCP 인정)
```

**VCP 점수 (0-20점)**:
- 수축 비율 깊을수록 높은 점수
- 시간 조정 기간 적절할수록 가산점

---

### 2. SmartMoney 수급 분석

**파일**: `screener.py` → `SmartMoneyScreener.analyze_supply_demand()`

```
수급 점수 산정:
├── 외국인 5일 순매수 (40% 가중치)
├── 기관 5일 순매수 (30% 가중치)
├── 연기금 5일 순매수 (15% 가중치)
└── 외국인 지분율 (15% 가중치)
```

**쌍끌이 (Double Buy) 조건**:
- 외국인 5일 순매수 > 0 AND 기관 5일 순매수 > 0

---

### 3. 종가베팅 V2 (12점 만점 시스템)

**파일**: `engine/generator.py`

```
점수 구성:
├── 뉴스 점수 (0-3점): LLM 감성 분석
├── 거래대금 점수 (0-3점): 거래대금 기준
├── 차트 점수 (0-2점): VCP, 52주 고가 근접
├── 캔들 점수 (0-1점): 양봉 패턴
├── 기간조정 점수 (0-1점): 조정 기간
└── 수급 점수 (0-2점): 외국인/기관 순매수
```

**등급 산정**:
- S급 (10점+): 자본의 15%
- A급 (8점+): 자본의 12%
- B급 (6점+): 자본의 10%
- C급 (6점 미만): 추천 안함

---

## API 엔드포인트

### KR Market APIs

| 엔드포인트 | 메서드 | 설명 |
|-----------|--------|------|
| `/api/kr/signals` | GET | 활성 VCP 시그널 목록 |
| `/api/kr/market-gate` | GET | Market Gate 상태 |
| `/api/kr/jongga-v2/latest` | GET | 최신 종가베팅 시그널 |
| `/api/kr/jongga-v2/dates` | GET | 가능한 날짜 목록 |
| `/api/kr/jongga-v2/history/{date}` | GET | 특정 날짜 시그널 |
| `/api/kr/ai-analysis` | GET | AI 분석 결과 |
| `/api/kr/ai-analysis?refresh=true` | GET | 새 AI 분석 강제 실행 |
| `/api/kr/backtest` | GET | 백테스트 결과 |

### System APIs

| 엔드포인트 | 메서드 | 설명 |
|-----------|--------|------|
| `/api/system/health` | GET | 시스템 헬스 체크 |
| `/api/system/data-status` | GET | 데이터 파일 상태 |

---

## 데이터 파일

### 필수 데이터 파일

```
kr_market/data/
├── daily_prices.csv                     # 2년치 일봉 데이터 (120MB+)
├── all_institutional_trend_data.csv     # 수급 데이터
├── signals_log.csv                      # 활성 VCP 시그널
├── korean_stocks_list.csv               # 종목 티커 DB
└── backtest_results.csv                 # 백테스트 결과
```

### 생성 순서

```bash
# 1. 종목 목록
python scripts/create_kr_stock_list.py

# 2. 일별 가격 (약 5분)
python scripts/create_complete_daily_prices.py

# 3. 수급 데이터 (약 5분)
python all_institutional_trend_data.py

# 4. VCP 스캔
python signal_tracker.py
```

---

## 환경 설정

### .env 파일

```bash
# === AI API Keys ===
GOOGLE_API_KEY=your_gemini_api_key_here
OPENAI_API_KEY=your_openai_api_key_here

# === Server Config ===
FLASK_DEBUG=true
FLASK_PORT=5001

# === Database (optional) ===
DATABASE_URL=postgresql://user:pass@localhost:5432/kr_stock
```

---

## 실행 방법

### Backend (Flask)

```bash
# 개발 모드
python flask_app.py

# 또는
flask run --host=0.0.0.0 --port=5001

# 프로덕션 모드
gunicorn -w 4 -b 0.0.0.0:5001 flask_app:app
```

### Frontend (Next.js)

```bash
cd frontend
npm install
npm run dev    # http://localhost:3000
npm run build  # 프로덕션 빌드
npm start      # 프로덕션 실행
```

---

## 의존성 설치

### Python

```bash
pip install flask gunicorn
pip install yfinance pandas numpy pykrx
pip install google-generativeai openai
pip install requests tqdm python-dotenv beautifulsoup4 plotly
pip install psycopg2-binary  # PostgreSQL (선택사항)
```

### Node.js

```bash
cd frontend
npm install
```

---

## 트러블슈팅

### 데이터 파일 누락

| 에러 메시지 | 해결 방법 |
|-------------|-----------|
| `❌ 가격 데이터 파일이 없습니다` | `python scripts/create_complete_daily_prices.py` |
| `❌ 수급 데이터 파일이 없습니다` | `python all_institutional_trend_data.py` |
| API가 빈 데이터 반환 | VCP 스캔 실행 (`python signal_tracker.py`) |

### API 키

| 서비스 | URL |
|-------|-----|
| Gemini | https://aistudio.google.com/apikey |
| OpenAI | https://platform.openai.com/api-keys |

---

## 라이선스

MIT License
