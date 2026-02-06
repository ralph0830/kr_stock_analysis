"""
Daytrading API 응답 구조 정규화 테스트

candidates → signals 변환 로직을 검증합니다.
"""

import pytest
from services.api_gateway.utils.daytrading import (
    normalize_candidate_to_signal,
    normalize_scan_response,
)


# =============================================================================
# normalize_candidate_to_signal 테스트
# =============================================================================

class TestNormalizeCandidateToSignal:
    """candidate → signal 변환 테스트"""

    def test_converts_candidate_with_all_fields(self):
        """모든 필드가 있는 candidate 변환"""
        candidate = {
            "ticker": "005930",
            "name": "삼성전자",
            "market": "KOSPI",
            "total_score": 90,
            "grade": "S",
            "price": 75000,
            "change_rate": 2.5,
            "volume": 20000000,
            "volume_ratio": 2.0,
        }

        result = normalize_candidate_to_signal(candidate)

        assert result["ticker"] == "005930"
        assert result["name"] == "삼성전자"
        assert result["market"] == "KOSPI"
        assert result["total_score"] == 90
        assert result["grade"] == "S"
        assert result["signal_type"] == "STRONG_BUY"  # 90점 >= 80
        assert result["current_price"] == 75000

    def test_converts_candidate_with_score_field(self):
        """score 필드를 사용하는 candidate 변환"""
        candidate = {
            "ticker": "000270",
            "name": "기아",
            "score": 75,  # score 필드
            "grade": "A",
        }

        result = normalize_candidate_to_signal(candidate)

        assert result["total_score"] == 75
        assert result["signal_type"] == "BUY"  # 75점 >= 60

    def test_infers_market_from_ticker_kospi(self):
        """ticker로 KOSPI market 추론"""
        candidate = {
            "ticker": "005930",  # 00으로 시작하지 않음
            "name": "삼성전자",
            "total_score": 80,
        }

        result = normalize_candidate_to_signal(candidate)

        assert result["market"] == "KOSPI"

    def test_infers_market_from_ticker_kosdaq(self):
        """ticker로 KOSDAQ market 추론"""
        candidate = {
            "ticker": "035420",  # 0으로 시작
            "name": "NAVER",
            "total_score": 70,
        }

        result = normalize_candidate_to_signal(candidate)

        assert result["market"] == "KOSDAQ"

    def test_calculates_signal_type_from_score(self):
        """점수 기반 signal_type 계산"""
        # STRONG_BUY (>= 80)
        candidate_s = {"ticker": "005930", "total_score": 90}
        assert normalize_candidate_to_signal(candidate_s)["signal_type"] == "STRONG_BUY"

        # BUY (>= 60)
        candidate_a = {"ticker": "005930", "total_score": 75}
        assert normalize_candidate_to_signal(candidate_a)["signal_type"] == "BUY"

        # WATCH (< 60)
        candidate_b = {"ticker": "005930", "total_score": 50}
        assert normalize_candidate_to_signal(candidate_b)["signal_type"] == "WATCH"

    def test_calculates_target_price_and_stop_loss(self):
        """target_price와 stop_loss 자동 계산"""
        candidate = {
            "ticker": "005930",
            "name": "삼성전자",
            "price": 75000,  # current_price로 사용
            "total_score": 80,
        }

        result = normalize_candidate_to_signal(candidate)

        assert result["current_price"] == 75000
        assert result["entry_price"] == 75000
        assert result["target_price"] == 78750  # 75000 * 1.05
        assert result["stop_loss"] == 72750  # 75000 * 0.97

    def test_preserves_existing_target_and_stop_loss(self):
        """기존 target_price와 stop_loss 유지"""
        candidate = {
            "ticker": "005930",
            "price": 75000,
            "target_price": 80000,  # 기존 값
            "stop_loss": 73000,  # 기존 값
            "total_score": 80,
        }

        result = normalize_candidate_to_signal(candidate)

        assert result["target_price"] == 80000
        assert result["stop_loss"] == 73000

    def test_returns_signal_format_if_already_has_checks(self):
        """이미 signals 형식이면 그대로 반환"""
        candidate = {
            "ticker": "005930",
            "name": "삼성전자",
            "market": "KOSPI",
            "total_score": 90,
            "grade": "S",
            "checks": [{"name": "거래량 폭증", "status": "passed", "points": 15}],
            "signal_type": "STRONG_BUY",
            "current_price": 75000,
        }

        result = normalize_candidate_to_signal(candidate)

        # 그대로 반환됨
        assert result is candidate
        assert result["checks"] == candidate["checks"]


# =============================================================================
# normalize_scan_response 테스트
# =============================================================================

class TestNormalizeScanResponse:
    """scan 응답 정규화 테스트"""

    def test_converts_candidates_to_signals(self):
        """candidates → signals 변환"""
        response = {
            "success": True,
            "data": {
                "candidates": [
                    {"ticker": "005930", "name": "삼성전자", "total_score": 90},
                    {"ticker": "000270", "name": "기아", "total_score": 75},
                ],
                "scan_time": "2026-02-06T10:00:00",
                "count": 2
            }
        }

        result = normalize_scan_response(response)

        assert "signals" in result["data"]
        assert "candidates" not in result["data"]
        assert len(result["data"]["signals"]) == 2
        assert result["data"]["count"] == 2

    def test_sets_generated_at_from_scan_time(self):
        """generated_at 필드 설정"""
        response = {
            "success": True,
            "data": {
                "candidates": [{"ticker": "005930", "total_score": 80}],
                "scan_time": "2026-02-06T10:00:00"
            }
        }

        result = normalize_scan_response(response)

        assert result["data"]["generated_at"] == "2026-02-06T10:00:00"

    def test_handles_empty_candidates(self):
        """빈 candidates 처리"""
        response = {
            "success": True,
            "data": {
                "candidates": [],
                "scan_time": "2026-02-06T10:00:00"
            }
        }

        result = normalize_scan_response(response)

        assert result["data"]["signals"] == []
        assert result["data"]["count"] == 0

    def test_handles_missing_data_key(self):
        """data 키가 없는 경우 처리"""
        response = {"success": True}

        result = normalize_scan_response(response)

        assert result["data"]["signals"] == []
        assert result["data"]["count"] == 0
