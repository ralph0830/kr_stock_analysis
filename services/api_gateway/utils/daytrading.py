"""
Daytrading API 유틸리티 함수

candidates 형식을 signals 형식으로 변환하는 유틸리티 함수.
"""

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
    # 이미 올바른 형식인지 확인 (checks 필드가 있고 리스트인 경우)
    if "checks" in candidate and isinstance(candidate.get("checks"), list):
        # 이미 signals 형식이면 그대로 반환
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
            signal_type = "WATCH"

    # market 결정 (ticker 기반 추론)
    market = candidate.get("market")
    if not market:
        ticker = candidate.get("ticker", "")
        # 한국 주식 코드 규칙 (단순화):
        # KOSPI 대형주 예외 처리: 005930(삼성전자), 005380(현대차) 등
        # KOSDAQ: 0으로 시작 (대부분)
        # 정확한 구분을 위해서는 DB 조회가 필요하지만,
        # 간단히 005xxx, 05xxx, 06xxx는 KOSPI, 그 외 0으로 시작하면 KOSDAQ로 처리
        if ticker and len(ticker) == 6:
            if ticker.startswith(("005", "05", "06")):
                market = "KOSPI"
            elif ticker.startswith("0"):
                market = "KOSDAQ"
            else:
                market = "KOSPI"  # 기본값
        else:
            market = "KOSPI"  # 기본값

    # price → current_price 변환
    current_price = candidate.get("current_price") or candidate.get("price")

    # entry_price, target_price, stop_loss 계산 (없는 경우)
    entry_price = candidate.get("entry_price") or current_price
    target_price = candidate.get("target_price")
    stop_loss = candidate.get("stop_loss")

    # target_price, stop_loss가 없으면 계산
    if current_price:
        if not target_price:
            target_price = int(current_price * 1.05)  # +5%
        if not stop_loss:
            stop_loss = int(current_price * 0.97)  # -3%

    return {
        "ticker": candidate.get("ticker"),
        "name": candidate.get("name"),
        "market": market,
        "total_score": score,
        "grade": candidate.get("grade", "C"),
        "checks": candidate.get("checks", []),
        "signal_type": signal_type,
        "current_price": current_price,
        "entry_price": entry_price,
        "target_price": target_price,
        "stop_loss": stop_loss,
        "detected_at": candidate.get("detected_at") or candidate.get("scan_time") or datetime.now().isoformat(),
    }


def normalize_scan_response(response: Dict[str, Any]) -> Dict[str, Any]:
    """
    Daytrading Scanner 스캔 응답을 프론트엔드 기대 형식으로 변환

    Args:
        response: Daytrading Scanner 원본 응답

    Returns:
        정규화된 응답 (candidates → signals)
    """
    candidates = response.get("data", {}).get("candidates", [])

    # candidates를 signals 형식으로 변환
    normalized_signals = [normalize_candidate_to_signal(c) for c in candidates]

    return {
        "success": True,
        "data": {
            "signals": normalized_signals,
            "count": len(normalized_signals),
            "generated_at": response.get("data", {}).get("scan_time") or datetime.now().isoformat()
        }
    }
