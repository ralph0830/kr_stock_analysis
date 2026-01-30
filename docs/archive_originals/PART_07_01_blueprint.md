# PART 07-1: Blueprint Overview

> **파일**: `blueprint/BLUEPRINT_01_OVERVIEW.md`
> **용도**: KR Market AI Stock Analysis System 시스템 개요
> **버전**: 1.0 | **업데이트**: 2026-01-03

---

## 1. Project Overview

### 1.1 What This System Does

한국 주식 시장 분석 시스템입니다:

1. **VCP Screening** - Mark Minervini의 변동성 수축 패턴 감지
2. **Institutional Flow Analysis** - 외국인/기관 수급 추적
3. **Dual-AI Analysis** - GPT-5.2 + Gemini 3.0 교차 검증
4. **Real-time News Grounding** - Gemini Google Search 최신 뉴스
5. **Automated Price Updates** - 백그라운드 스케줄러 실시간 가격

---

## 2. System Architecture

### 2.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         USER INTERFACE                              │
│                    (Web Browser - dashboard.html)                   │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         FLASK SERVER                                │
│                        (flask_app.py)                               │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                 │
│  │ KR Market   │  │ US Market   │  │ Dividend    │                 │
│  │ APIs        │  │ APIs        │  │ APIs        │                 │
│  └─────────────┘  └─────────────┘  └─────────────┘                 │
└─────────────────────────────────────────────────────────────────────┘
                                    │
              ┌─────────────────────┼─────────────────────┐
              ▼                     ▼                     ▼
┌─────────────────────┐ ┌─────────────────────┐ ┌─────────────────────┐
│   AI ANALYSIS       │ │   DATA SOURCES      │ │   BACKGROUND JOBS   │
│   (kr_ai_analyzer)  │ │   (pykrx, yfinance) │ │   (scheduler)       │
│                     │ │                     │ │                     │
│  - Gemini 3.0       │ │  - KRX (Korea)      │ │  - Price Updates    │
│  - GPT-5.2          │ │  - Yahoo Finance    │ │  - Signal Tracking  │
│  - News Grounding   │ │  - News APIs        │ │  - Daily Scans      │
└─────────────────────┘ ┌─────────────────────┘ ┌─────────────────────┘
```

### 2.2 Data Flow

```
1. User requests AI Analysis
           │
           ▼
2. Flask loads signals from signals_log.csv
           │
           ▼
3. For each signal (Top 10):
   ├── Fetch fundamentals (pykrx)
   ├── Fetch current price (pykrx)
   ├── Call Gemini (with Google Search grounding)
   │   └── Returns: recommendation + news summaries
   ├── Call GPT (with Gemini's news)
   │   └── Returns: recommendation
   └── Combine results
           │
           ▼
4. Save to kr_ai_analysis.json
           │
           ▼
5. Return JSON to frontend
```

---

## 3. File Structure

```
국내주식/
├── flask_app.py                 # Main Flask server (3,522 lines)
├── requirements.txt             # Python dependencies
├── .env                         # Environment variables (API keys)
│
├── templates/
│   ├── dashboard.html           # Main dashboard (5,923 lines)
│   └── index.html               # Landing page (723 lines)
│
├── kr_market/                   # Korean market module
│   ├── __init__.py              # Package init
│   ├── config.py                # Configuration classes (183 lines)
│   ├── kr_ai_analyzer.py        # AI analysis logic (397 lines)
│   ├── signal_tracker.py        # VCP signal tracking (358 lines)
│   ├── screener.py              # Stock screener (563 lines)
│   ├── scheduler.py             # Background jobs (384 lines)
│   ├── market_gate.py           # Market condition checker (300 lines)
│   ├── models.py                # Data models (286 lines)
│   │
│   ├── data/
│   │   ├── kr_ai_analysis.json  # AI analysis results (cached)
│   │   └── history/             # Historical analysis files
│   │
│   ├── scripts/
│   │   └── create_complete_daily_prices.py  # Daily price data generator
│   │
│   ├── daily_prices.csv                     # 📌 2년치 일봉 데이터 (120MB+)
│   ├── all_institutional_trend_data.csv     # 📌 수급 데이터
│   ├── signals_log.csv                      # Active VCP signals
│   ├── korean_stocks_list.csv               # Korean stock ticker DB
│   └── backtest_results.csv                 # Backtest output
│
└── us_market/                   # US market module (separate)
    └── ...
```

---

## 4. Dependencies

### 4.1 requirements.txt

```txt
# Web Framework
flask
gunicorn

# Data & Finance
yfinance
pandas
numpy
pykrx

# AI/LLM
google-generativeai
openai

# Utilities
requests
tqdm
python-dotenv
beautifulsoup4
lxml_html_clean

# Visualization
plotly
```

### 4.2 System Requirements

| 항목 | 요구사항 |
|-----|---------|
| **Python** | 3.11+ |
| **OS** | macOS / Linux / Windows |
| **RAM** | 4GB+ 권장 |
| **Storage** | 1GB for data files |

---

## 5. Environment Variables

### 5.1 .env File Template

```bash
# === AI API Keys ===
GOOGLE_API_KEY=your_gemini_api_key_here
OPENAI_API_KEY=your_openai_api_key_here

# === Optional: News APIs ===
# NAVER_CLIENT_ID=your_naver_client_id       # Deprecated
# NAVER_CLIENT_SECRET=your_naver_secret      # Deprecated

# === Server Config ===
FLASK_DEBUG=true
FLASK_PORT=5001
```

### 5.2 Getting API Keys

| Service | URL | Purpose |
|:---|:---|:---|
| **Google AI Studio** | https://aistudio.google.com/apikey | Gemini 3.0 API |
| **OpenAI** | https://platform.openai.com/api-keys | GPT-5.2 API |

---

## 6. Data Schemas

### 6.1 signals_log.csv (VCP Signals)

```csv
ticker,name,signal_date,entry_price,status,score,contraction_ratio,foreign_5d,inst_5d
005930,삼성전자,2025-12-29,72000,OPEN,82.5,0.45,1500000,800000
000270,기아,2025-12-29,119800,OPEN,75.0,0.52,420000,350000
```

| Column | Type | Description |
|:---|:---|:---|
| `ticker` | string | 6-digit stock code (zero-padded) |
| `name` | string | Company name |
| `signal_date` | date | VCP signal detection date |
| `entry_price` | float | Recommended entry price |
| `status` | enum | OPEN / CLOSED |
| `score` | float | VCP score (0-100) |
| `contraction_ratio` | float | Volatility contraction (0-1) |
| `foreign_5d` | int | Foreign net buy (5-day cumulative) |
| `inst_5d` | int | Institutional net buy (5-day cumulative) |

### 6.2 kr_ai_analysis.json (AI Results)

```json
{
  "market_indices": {
    "kospi": { "value": 4281.47, "change_pct": 1.6 },
    "kosdaq": { "value": 940.43, "change_pct": 1.62 }
  },
  "signals": [
    {
      "ticker": "123410",
      "name": "코리아에프티",
      "score": 82.5,
      "contraction_ratio": 0.41,
      "foreign_5d": 1036584,
      "inst_5d": 223456,
      "entry_price": 8240,
      "current_price": 8180,
      "return_pct": -0.73,
      "fundamentals": {
        "per": "6.49",
        "pbr": "1.05",
        "roe": "16.18%",
        "eps": "1,269원",
        "bps": "7,705원",
        "div_yield": "1.85%",
        "marcap": "2,255억원"
      },
      "news": [
        {
          "title": "코리아에프티, HEV 열풍 타고 '1조 클럽' 진입 초읽기",
          "summary": "하이브리드용 캐니스터 ASP가 내연기관 대비 2배 이상...",
          "url": "https://example.com/news/1"
        }
      ],
      "gpt_recommendation": {
        "action": "BUY",
        "confidence": 84,
        "reason": "VCP 점수와 외국인 순매수세, 실적 호조..."
      },
      "gemini_recommendation": {
        "action": "BUY",
        "confidence": 92,
        "reason": "HEV 시장 성장 수혜 및 저평가..."
      }
    }
  ],
  "generated_at": "2026-01-02T13:52:31.311951",
  "signal_date": "2025-12-29"
}
```

---

## 7. API Endpoints Overview

### 7.1 KR Market APIs

| Method | Endpoint | Description |
|:---|:---|:---|
| GET | `/api/kr/signals` | Get active VCP signals |
| GET | `/api/kr/ai-analysis` | Get AI recommendations (cached) |
| GET | `/api/kr/ai-analysis?refresh=true` | Force new AI analysis |
| GET | `/api/kr/vcp-scan` | Run VCP scanner |
| GET | `/api/kr/backtest` | Get backtest results |

### 7.2 Response Format

모든 API는 일관된 JSON 구조를 반환:

```json
{
  "status": "success",
  "data": { ... },
  "generated_at": "2026-01-03T10:00:00"
}
```

---

## 8. Configuration Reference

### 8.1 VCP Scoring Weights

```python
# From config.py
weight_foreign: float = 0.40    # Foreign flow (40%)
weight_inst: float = 0.30       # Institutional flow (30%)
weight_technical: float = 0.20  # Technical analysis (20%)
weight_fundamental: float = 0.10 # Fundamentals (10%)
```

### 8.2 Backtest Parameters

```python
@dataclass
class BacktestConfig:
    stop_loss_pct: float = 5.0       # Stop loss at -5%
    take_profit_pct: float = 15.0    # Take profit at +15%
    trailing_stop_pct: float = 5.0   # Trailing stop
    max_hold_days: int = 15          # Maximum holding period
    position_size_pct: float = 10.0  # 10% of capital per position
    max_positions: int = 10          # Maximum 10 concurrent positions
```

### 8.3 Signal Thresholds

```python
# Strong buy signals
foreign_strong_buy: int = 5_000_000  # 5M shares foreign net buy
inst_strong_buy: int = 3_000_000     # 3M shares institutional net buy

# VCP pattern requirements
min_score: int = 60                  # Minimum VCP score
max_contraction_ratio: float = 0.8   # Maximum volatility contraction
```

---

## 9. Quick Start Guide

### 9.1 Installation

```bash
# 1. Clone or create project directory
mkdir 국내주식
cd 국내주식

# 2. Create virtual environment
python3.11 -m venv .venv
source .venv/bin/activate  # macOS/Linux
# .venv\Scripts\activate   # Windows

# 3. Install dependencies
pip install flask gunicorn yfinance pandas numpy pykrx
pip install google-generativeai openai
pip install requests tqdm python-dotenv beautifulsoup4 plotly

# 4. Create .env file
cat > .env << 'EOF'
GOOGLE_API_KEY=your_gemini_key
OPENAI_API_KEY=your_openai_key
FLASK_DEBUG=true
FLASK_PORT=5001
EOF

# 5. Create directory structure
mkdir -p kr_market/data templates
```

### 9.2 Running the Server

```bash
# Development mode
python flask_app.py

# Production mode (with gunicorn)
gunicorn -w 4 -b 0.0.0.0:5001 flask_app:app
```

### 9.3 Accessing the Dashboard

Open browser: `http://localhost:5001/app`

---

## 10. Troubleshooting

### 10.1 Common Issues

| Issue | Cause | Solution |
|:---|:---|:---|
| `ModuleNotFoundError: pykrx` | Missing dependency | `pip install pykrx` |
| API returns empty data | No signals in CSV | Run VCP scanner first |
| Gemini timeout | Rate limiting | Wait 1 minute, retry |
| Port 5001 in use | Another process | Kill process or change port |
| `❌ 가격 데이터 파일이 없습니다` | daily_prices.csv 누락 | `python scripts/create_complete_daily_prices.py` 실행 |
| `❌ 수급 데이터 파일이 없습니다` | institutional data 누락 | `python all_institutional_trend_data.py` 실행 |
| `signal_tracker` 데이터 못 찾음 | 🔧 경로 버그 (2026-01-03 수정됨) | `os.path.dirname()` 제거 - data_dir 직접 사용 |

### 10.2 데이터 파일 생성 순서 (중요!)

```bash
cd kr_market

# 1. 주식 목록 생성 (pykrx 사용)
python scripts/create_kr_stock_list.py

# 2. 일별 가격 데이터 생성 (약 5분 소요)
python scripts/create_complete_daily_prices.py

# 3. 수급 데이터 수집 (약 5분 소요)
python all_institutional_trend_data.py

# 4. VCP 시그널 스캔
python signal_tracker.py

# 5. AI 분석 (Flask 서버에서 /api/kr/ai-analysis?refresh=true)
```

---

## 다음 문서

계속해서 **[BLUEPRINT_02_BACKEND_FLASK_CORE.md](./BLUEPRINT_02_BACKEND_FLASK_CORE.md)**를 참조하여 Flask 서버 구현 세부사항을 확인하세요.
