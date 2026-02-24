# 시장 스캔 API 응답 구조 정규화 요구사항

**작성일:** 2026-02-06
**목적:** 시장 스캔 API 응답 구조 불일치 문제 해결을 위한 백엔드 구현 가이드

---

## 1. 문제 개요

### 1.1 발생한 오류
```
TypeError: Cannot read properties of undefined (reading 'map')
```

### 1.2 원인
- 백엔드 Daytrading Scanner `/scan` 엔드포인트가 `candidates` 필드로 반환
- 프론트엔드는 `signals` 필드를 기대
- API Gateway에서 응답 구조 변환을 수행하지 않음

### 1.3 프론트엔드 조치 완료
- `daytradingStore.ts`에 응답 구조 호환성 처리 추가 (`candidates` → `signals` 변환)
- 하지만 백엔드에서 근본적으로 해결하는 것이 바람직함

---

## 2. 현재 응답 구조

### 2.1 Daytrading Scanner `/scan` 응답 (현재)
```json
{
  "success": true,
  "data": {
    "candidates": [
      {
        "ticker": "005930",
        "name": "삼성전자",
        "price": 75000,
        "change_rate": 2.5,
        "volume": 20000000,
        "avg_volume": 10000000,
        "volume_ratio": 2.0,
        "total_score": 90,
        "grade": "S"
      }
    ],
    "scan_time": "2026-02-06T04:55:37.985679",
    "count": 2
  }
}
```

### 2.2 `/signals` 응답 (정상)
```json
{
  "success": true,
  "data": {
    "signals": [
      {
        "ticker": "005930",
        "name": "삼성전자",
        "market": "KOSPI",
        "total_score": 90,
        "grade": "S",
        "checks": [...],
        "signal_type": "STRONG_BUY",
        "current_price": 75500,
        "entry_price": 75000,
        "target_price": 80000,
        "stop_loss": 73000,
        "detected_at": "2026-02-06T04:00:00Z"
      }
    ],
    "count": 3
  }
}
```

---

## 3. 백엔드 구현 방안

### 3.1 API Gateway 수정 (권장)

**파일:** `services/api_gateway/routes/daytrading.py`

**수정 전:**
```python
@router.post("/scan")
async def scan_daytrading_market(request: dict):
    # ... 기존 코드 ...
    result = response.json()
    await _invalidate_daytrading_cache()
    return result
```

**수정 후:**
```python
@router.post("/scan")
async def scan_daytrading_market(request: dict):
    # ... 기존 코드 ...

    result = response.json()

    # 응답 구조 정규화 (candidates → signals)
    candidates = result.get("data", {}).get("candidates", [])

    # candidates를 IDaytradingSignal 형식으로 변환
    normalized_signals = []
    for candidate in candidates:
        # checks 필드가 있는 경우 이미 올바른 형식
        if "checks" in candidate and isinstance(candidate.get("checks"), list):
            normalized_signals.append(candidate)
        else:
            # candidates 형식을 signals 형식으로 변환
            normalized_signals.append({
                "ticker": candidate.get("ticker"),
                "name": candidate.get("name"),
                "market": candidate.get("market", "KOSPI"),
                "total_score": candidate.get("total_score", candidate.get("score", 0)),
                "grade": candidate.get("grade", "C"),
                "checks": candidate.get("checks", []),
                "signal_type": candidate.get("signal_type") or (
                    "STRONG_BUY" if candidate.get("total_score", candidate.get("score", 0)) >= 80
                    else "BUY" if candidate.get("total_score", candidate.get("score", 0)) >= 60
                    else "MODERATE_BUY"
                ),
                "current_price": candidate.get("price", candidate.get("current_price")),
                "entry_price": candidate.get("entry_price"),
                "target_price": candidate.get("target_price"),
                "stop_loss": candidate.get("stop_loss"),
                "detected_at": candidate.get("detected_at", candidate.get("scan_time", datetime.now().isoformat())),
            })

    # 프론트엔드 기대 구조로 변환
    normalized_response = {
        "success": True,
        "data": {
            "signals": normalized_signals,
            "count": len(normalized_signals),
            "generated_at": result.get("data", {}).get("scan_time", datetime.now().isoformat())
        }
    }

    await _invalidate_daytrading_cache()
    return normalized_response
```

### 3.2 공통 유틸리티 함수 추출 (권장)

**파일:** `services/api_gateway/utils/daytrading.py`

```python
from datetime import datetime
from typing import Any, Dict, List

def normalize_candidate_to_signal(candidate: Dict[str, Any]) -> Dict[str, Any]:
    """
    Daytrading Scanner의 candidates 형식을 IDaytradingSignal 형식으로 변환

    Args:
        candidate: candidates 배열의 항목

    Returns:
        IDaytradingSignal 형식으로 변환된 딕셔너리
    """
    # 이미 올바른 형식인지 확인
    if "checks" in candidate and isinstance(candidate.get("checks"), list):
        return candidate

    # 점수 계산 (total_score 또는 score 필드 사용)
    score = candidate.get("total_score", candidate.get("score", 0))

    # signal_type 결정
    signal_type = candidate.get("signal_type")
    if not signal_type:
        if score >= 80:
            signal_type = "STRONG_BUY"
        elif score >= 60:
            signal_type = "BUY"
        else:
            signal_type = "MODERATE_BUY"

    # market 결정 (ticker 기반 추론)
    market = candidate.get("market")
    if not market:
        ticker = candidate.get("ticker", "")
        # KOSDAQ: 0으로 시작, KOSPI: 그 외
        market = "KOSDAQ" if ticker.startswith("0") else "KOSPI"

    return {
        "ticker": candidate.get("ticker"),
        "name": candidate.get("name"),
        "market": market,
        "total_score": score,
        "grade": candidate.get("grade", "C"),
        "checks": candidate.get("checks", []),
        "signal_type": signal_type,
        "current_price": candidate.get("price", candidate.get("current_price")),
        "entry_price": candidate.get("entry_price"),
        "target_price": candidate.get("target_price"),
        "stop_loss": candidate.get("stop_loss"),
        "detected_at": candidate.get("detected_at", candidate.get("scan_time", datetime.now().isoformat())),
    }

def normalize_scan_response(response: Dict[str, Any]) -> Dict[str, Any]:
    """
    Daytrading Scanner 스캔 응답을 프론트엔드 기대 형식으로 변환

    Args:
        response: Daytrading Scanner 원본 응답

    Returns:
        정규화된 응답
    """
    candidates = response.get("data", {}).get("candidates", [])
    normalized_signals = [normalize_candidate_to_signal(c) for c in candidates]

    return {
        "success": True,
        "data": {
            "signals": normalized_signals,
            "count": len(normalized_signals),
            "generated_at": response.get("data", {}).get("scan_time", datetime.now().isoformat())
        }
    }
```

---

## 4. 관련 엔드포인트

| 엔드포인트 | 응답 구조 변환 | 상태 |
|-----------|---------------|------|
| `GET /api/daytrading/signals` | O (format 파라미터 지원) | 정상 |
| `POST /api/daytrading/scan` | X (추가 필요) | **구현 필요** |
| `POST /api/daytrading/analyze` | X (확인 필요) | 확인 필요 |

---

## 5. 우선순위

1. **P1 - 권장:** API Gateway에서 응답 구조 정규화
2. **P2 - 개선:** 공통 유틸리티 함수 추출

---

## 6. 프론트엔드 대응 완료 사항

| 파일 | 수정 내용 |
|------|----------|
| `frontend/store/daytradingStore.ts` | `scanDaytradingMarket`, `analyzeStocks`에서 `candidates` → `signals` 변환 로직 추가 |

---

## 7. 테스트 시나리오

1. "시장 스캔" 버튼 클릭 → API 응답 수신 → 오류 없이 렌더링 ✅
2. 빈 응답 수신 시 → 빈 목록으로 정상 표시
3. `candidates` 형식 응답 → 자동 변환되어 정상 표시 ✅

---

*마지막 수정: 2026-02-06*
