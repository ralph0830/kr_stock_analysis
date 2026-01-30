# PART 07-1: Blueprint Overview

> **용도**: KR Market AI Stock Analysis System 시스템 개요
> **전체 문서**: `docs/archive_originals/PART_07_01_blueprint.md` (417줄)

---

## 시스템 개요

한국 주식 시장 분석 시스템:
1. **VCP Screening** - Mark Minervini 변동성 수축 패턴 감지
2. **Institutional Flow Analysis** - 외국인/기관 수급 추적
3. **Dual-AI Analysis** - GPT-5.2 + Gemini 3.0 교차 검증
4. **Real-time News Grounding** - Gemini Google Search 최신 뉴스
5. **Automated Price Updates** - 백그라운드 스케줄러 실시간 가격

---

## 아키텍처

```
┌─────────────────────────────────────────┐
│            USER INTERFACE               │
│         (Web Browser)                   │
└─────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────┐
│            FLASK SERVER                 │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐   │
│  │ KR API  │ │ US API  │ │Div API  │   │
│  └─────────┘ └─────────┘ └─────────┘   │
└─────────────────────────────────────────┘
         │              │              │
    ┌────┴────┐    ┌───┴────┐   ┌────┴────┐
    │  AI     │    │  DATA  │   │  JOB    │
    │ Gemini  │    │ pykrx  │   │Scheduler│
    │ GPT     │    │ yahoo  │   │         │
    └─────────┘    └────────┘   └─────────┘
```

---

## 핵심 파일

| 파일 | 라인 수 | 설명 |
|------|---------|------|
| `flask_app.py` | 3,522 | 메인 Flask 서버 |
| `dashboard.html` | 5,923 | 메인 대시보드 |
| `kr_ai_analyzer.py` | 397 | AI 분석 로직 |
| `signal_tracker.py` | 358 | VCP 시그널 추적 |
| `screener.py` | 563 | 종목 스크리너 |
