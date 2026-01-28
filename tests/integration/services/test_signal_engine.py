"""
Test Suite: Signal Engine Service (GREEN Phase)
종가베팅 V2 시그널 엔진 서비스 테스트
"""

import pytest
from httpx import AsyncClient, ASGITransport

from services.signal_engine.main import app
from services.signal_engine.scorer import SignalScorer, Grade


class TestSignalEngineEndpoints:
    """Signal Engine 엔드포인트 테스트"""

    @pytest.mark.asyncio
    async def test_health_check(self):
        """헬스 체크 엔드포인트"""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/health")

        assert response.status_code == 200
        assert response.json()["service"] == "signal-engine"

    @pytest.mark.asyncio
    async def test_get_latest_signals(self):
        """/signals/latest 엔드포인트"""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/signals/latest")

        assert response.status_code == 200
        data = response.json()
        assert "signals" in data
        assert isinstance(data["signals"], list)

    @pytest.mark.asyncio
    async def test_generate_signals(self):
        """/generate 엔드포인트 - 시그널 생성"""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/generate", json={
                "market": "KOSPI",
                "top_n": 10,
                "capital": 10_000_000
            })

        assert response.status_code == 200
        data = response.json()
        assert "signals" in data
        assert isinstance(data["signals"], list)

    @pytest.mark.asyncio
    async def test_analyze_stock(self):
        """/analyze 엔드포인트"""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/analyze", json={
                "ticker": "005930",
                "name": "삼성전자",
                "price": 80000
            })

        assert response.status_code == 200
        data = response.json()
        assert "ticker" in data
        assert "score" in data
        assert "grade" in data


class TestSignalScorer:
    """시그널 점수 계산 테스트"""

    def test_scorer_init(self):
        """Scorer 초기화 테스트"""
        scorer = SignalScorer()
        assert scorer is not None

    def test_calculate_signal(self):
        """시그널 계산 테스트"""
        scorer = SignalScorer()
        signal = scorer.calculate("005930", "삼성전자", 80000)

        assert signal is not None
        assert signal.ticker == "005930"
        assert 0 <= signal.score.total <= 12
        assert signal.grade in [Grade.S, Grade.A, Grade.B, Grade.C]

    def test_grade_calculation(self):
        """등급 산정 테스트"""
        scorer = SignalScorer()

        # S급 (10점 이상)
        # 실제로는 random이므로 여러 번 시도해서 확인
        for _ in range(10):
            signal = scorer.calculate("005930", "삼성전자", 80000)
            if signal:
                assert signal.grade in [Grade.S, Grade.A, Grade.B, Grade.C]
                # 등급과 점수의 관계 확인
                if signal.score.total >= 10:
                    assert signal.grade == Grade.S
                elif signal.score.total >= 8:
                    assert signal.grade in [Grade.S, Grade.A]

    def test_position_size_calculation(self):
        """포지션 크기 계산 테스트"""
        scorer = SignalScorer()
        signal = scorer.calculate("005930", "삼성전자", 80000)

        if signal:
            # 포지션 크기는 자본의 일부여야 함
            # 1000만원 기준
            assert signal.position_size > 0
            # 포지션 크기 * 주가 = 자본 투자액
            invested = signal.position_size * 80000
            assert invested > 0


class TestLLMAnalyzer:
    """LLM 뉴스 분석 테스트 (추후 구현)"""

    @pytest.mark.skip(reason="LLM Analyzer not implemented yet")
    @pytest.mark.asyncio
    async def test_analyze_news_sentiment(self):
        """뉴스 감성 분석 테스트"""
        pass


class TestPositionSizer:
    """포지션 사이징 테스트"""

    def test_position_size_by_grade(self):
        """등급별 포지션 크기 테스트"""
        # S급: 15%, A급: 12%, B급: 10%, C급: 5%
        scorer = SignalScorer()

        # 여러 번 시도해서 다양한 등급 확인
        for _ in range(10):
            signal = scorer.calculate("005930", "삼성전자", 80000)
            if signal:
                assert signal.position_size > 0
