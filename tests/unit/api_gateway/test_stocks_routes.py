"""
Stocks Routes Unit Tests
TDD GREEN Phase - Tests should pass with implementation
"""

import pytest
from unittest.mock import Mock, patch
from datetime import date, datetime
from fastapi import HTTPException

from src.database.models import Stock, DailyPrice, Signal, InstitutionalFlow
from services.api_gateway.schemas import (
    StockDetailResponse,
)


@pytest.fixture
def mock_stock():
    """Mock Stock 데이터"""
    stock = Stock(
        id=1,
        ticker="005930",
        name="삼성전자",
        market="KOSPI",
        sector="반도체",
        market_cap=500000000000000,
        is_etf=False,
        is_admin=False,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    return stock


@pytest.fixture
def mock_daily_prices():
    """Mock DailyPrice 데이터"""
    return [
        DailyPrice(
            ticker="005930",
            date=date(2024, 1, 10),
            open_price=80000,
            high_price=81000,
            low_price=79500,
            close_price=80500,
            volume=1000000,
            foreign_net_buy=500000,
            inst_net_buy=-300000,
            retail_net_buy=-200000,
        ),
        DailyPrice(
            ticker="005930",
            date=date(2024, 1, 11),
            open_price=80500,
            high_price=81500,
            low_price=80000,
            close_price=81200,
            volume=1200000,
            foreign_net_buy=600000,
            inst_net_buy=-200000,
            retail_net_buy=-400000,
        ),
    ]


@pytest.fixture
def mock_signals():
    """Mock Signal 데이터"""
    return [
        Signal(
            id=1,
            ticker="005930",
            signal_type="VCP",
            status="OPEN",
            score=85.5,
            grade="A",
            contraction_ratio=0.3,
            entry_price=80000,
            stop_price=78000,
            target_price=88000,
            signal_date=date(2024, 1, 10),
            created_at=datetime.now(),
        ),
        Signal(
            id=2,
            ticker="005930",
            signal_type="JONGGA_V2",
            status="CLOSED",
            score=92.0,
            grade="S",
            total_score=12,
            entry_price=75000,
            signal_date=date(2024, 1, 5),
            entry_time=datetime(2024, 1, 5, 9, 0),
            exit_time=datetime(2024, 1, 15, 15, 30),
            exit_reason="Target Reached",
            created_at=datetime.now(),
        ),
    ]


@pytest.fixture
def mock_institutional_flows():
    """Mock InstitutionalFlow 데이터"""
    return [
        InstitutionalFlow(
            ticker="005930",
            date=date(2024, 1, 10),
            foreign_net_buy=500000,
            foreign_consecutive_days=5,
            foreign_trend="buying",
            inst_net_buy=-300000,
            inst_consecutive_days=-2,
            inst_trend="selling",
            foreign_net_5d=2000000,
            foreign_net_20d=5000000,
            inst_net_5d=-1000000,
            inst_net_20d=-3000000,
            supply_demand_score=65.0,
            is_double_buy=False,
        ),
        InstitutionalFlow(
            ticker="005930",
            date=date(2024, 1, 11),
            foreign_net_buy=600000,
            foreign_consecutive_days=6,
            foreign_trend="buying",
            inst_net_buy=-200000,
            inst_consecutive_days=-1,
            inst_trend="selling",
            foreign_net_5d=2500000,
            foreign_net_20d=5500000,
            inst_net_5d=-800000,
            inst_net_20d=-2800000,
            supply_demand_score=68.0,
            is_double_buy=False,
        ),
    ]


class TestStocksRoutesUnit:
    """Stocks Routes 단위 테스트"""

    def test_get_stock_detail_found(self, mock_stock, mock_daily_prices):
        """종목 상세 조회 - 종목 존재"""
        from services.api_gateway.routes.stocks import get_stock_detail

        # Mock session 설정
        mock_session = Mock()

        # StockRepository mock
        mock_stock_repo = Mock()
        mock_stock_repo.get_by_ticker.return_value = mock_stock

        # DailyPriceRepository mock
        mock_price_repo = Mock()
        mock_price_repo.get_latest_by_ticker.return_value = mock_daily_prices[:1]
        # 이전 날짜 가격도 mock
        mock_price_repo.get_latest_by_ticker.return_value = mock_daily_prices

        with patch(
            "services.api_gateway.routes.stocks.StockRepository",
            return_value=mock_stock_repo,
        ):
            with patch(
                "services.api_gateway.routes.stocks.DailyPriceRepository",
                return_value=mock_price_repo,
            ):
                result = get_stock_detail("005930", mock_session)
                assert result.ticker == "005930"
                assert result.name == "삼성전자"

    def test_get_stock_detail_not_found(self):
        """종목 상세 조회 - 종목 없음 404"""
        from services.api_gateway.routes.stocks import get_stock_detail

        mock_session = Mock()
        mock_repo = Mock()
        mock_repo.get_by_ticker.return_value = None

        with patch(
            "services.api_gateway.routes.stocks.StockRepository",
            return_value=mock_repo,
        ):
            with pytest.raises(HTTPException) as exc_info:
                get_stock_detail("999999", mock_session)
            assert exc_info.value.status_code == 404

    def test_get_stock_chart_success(self, mock_daily_prices):
        """차트 데이터 조회 - 성공"""
        from services.api_gateway.routes.stocks import get_stock_chart

        mock_session = Mock()
        mock_repo = Mock()
        mock_repo.get_by_ticker_and_date_range.return_value = mock_daily_prices

        with patch(
            "services.api_gateway.routes.stocks.DailyPriceRepository",
            return_value=mock_repo,
        ):
            result = get_stock_chart("005930", 30, mock_session)
            assert result.ticker == "005930"
            assert len(result.data) == 2
            assert result.data[0].close == 80500

    def test_get_stock_chart_empty(self):
        """차트 데이터 조회 - 데이터 없음"""
        from services.api_gateway.routes.stocks import get_stock_chart

        mock_session = Mock()
        mock_repo = Mock()
        mock_repo.get_by_ticker_and_date_range.return_value = []

        with patch(
            "services.api_gateway.routes.stocks.DailyPriceRepository",
            return_value=mock_repo,
        ):
            result = get_stock_chart("005930", 30, mock_session)
            assert result.ticker == "005930"
            assert len(result.data) == 0

    def test_get_stock_flow_success(self, mock_institutional_flows):
        """수급 데이터 조회 - 성공"""
        from services.api_gateway.routes.stocks import get_stock_flow

        mock_session = Mock()
        mock_repo = Mock()
        mock_repo.get_institutional_flow.return_value = mock_institutional_flows

        with patch(
            "services.api_gateway.routes.stocks.StockRepository",
            return_value=mock_repo,
        ):
            result = get_stock_flow("005930", 20, mock_session)
            assert result.ticker == "005930"
            assert len(result.data) == 2
            assert 0 <= result.smartmoney_score <= 100

    def test_get_stock_signals_success(self, mock_signals):
        """시그널 히스토리 조회 - 성공"""
        from services.api_gateway.routes.stocks import get_stock_signals

        mock_session = Mock()
        mock_repo = Mock()
        mock_repo.get_by_ticker.return_value = mock_signals

        with patch(
            "services.api_gateway.routes.stocks.SignalRepository",
            return_value=mock_repo,
        ):
            result = get_stock_signals("005930", mock_session)
            assert result.ticker == "005930"
            assert result.total_signals == 2
            assert result.open_signals == 1
            assert result.closed_signals == 1

    def test_stock_detail_response_model(self, mock_stock):
        """StockDetailResponse 모델 검증"""
        response = StockDetailResponse(
            ticker=mock_stock.ticker,
            name=mock_stock.name,
            market=mock_stock.market,
            sector=mock_stock.sector,
            current_price=80500,
            price_change=500,
            price_change_pct=0.62,
            volume=1000000,
            updated_at=datetime.now(),
        )
        assert response.ticker == "005930"
        assert response.name == "삼성전자"

    def test_stock_chart_response_model(self, mock_daily_prices):
        """StockChartResponse 모델 검증"""
        from services.api_gateway.schemas import ChartPoint, StockChartResponse

        chart_points = [
            ChartPoint(
                date=dp.date,
                open=dp.open_price,
                high=dp.high_price,
                low=dp.low_price,
                close=dp.close_price,
                volume=dp.volume,
            )
            for dp in mock_daily_prices
        ]

        response = StockChartResponse(
            ticker="005930", period="1mo", data=chart_points, total_points=2
        )
        assert response.ticker == "005930"
        assert response.total_points == 2

    def test_stock_flow_response_model(self, mock_institutional_flows):
        """StockFlowResponse 모델 검증"""
        from services.api_gateway.schemas import FlowDataPoint, StockFlowResponse

        flow_points = [
            FlowDataPoint(
                date=flow.date,
                foreign_net=flow.foreign_net_buy,
                inst_net=flow.inst_net_buy,
                foreign_net_amount=flow.foreign_net_buy * 10000,  # 금액 계산
                inst_net_amount=flow.inst_net_buy * 10000,
                supply_demand_score=flow.supply_demand_score,
            )
            for flow in mock_institutional_flows
        ]

        response = StockFlowResponse(
            ticker="005930",
            period_days=20,
            data=flow_points,
            smartmoney_score=66.5,
            total_points=2,
        )
        assert response.ticker == "005930"
        assert response.smartmoney_score == 66.5

    def test_signal_history_response_model(self, mock_signals):
        """SignalHistoryResponse 모델 검증"""
        from services.api_gateway.schemas import (
            SignalHistoryItem,
            SignalHistoryResponse,
        )

        signal_items = [
            SignalHistoryItem(
                id=sig.id,
                ticker=sig.ticker,
                signal_type=sig.signal_type,
                signal_date=sig.signal_date,
                status=sig.status,
                score=sig.score,
                grade=sig.grade,
                entry_price=sig.entry_price,
                exit_price=None,  # Signal 모델에 exit_price 필드 없음
                entry_time=sig.entry_time,
                exit_time=sig.exit_time,
                return_pct=None,  # exit_price가 없으므로 None
                exit_reason=sig.exit_reason,
            )
            for sig in mock_signals
        ]

        response = SignalHistoryResponse(
            ticker="005930",
            total_signals=2,
            open_signals=1,
            closed_signals=1,
            avg_return_pct=None,  # 계산 불가
            win_rate=None,
            signals=signal_items,
        )
        assert response.ticker == "005930"
        assert response.total_signals == 2

    def test_get_stock_chart_with_period_parameter(self, mock_daily_prices):
        """차트 데이터 조회 - period 파라미터 처리"""
        from services.api_gateway.routes.stocks import get_stock_chart

        mock_session = Mock()
        mock_repo = Mock()
        mock_repo.get_by_ticker_and_date_range.return_value = mock_daily_prices

        with patch(
            "services.api_gateway.routes.stocks.DailyPriceRepository",
            return_value=mock_repo,
        ):
            # 다양한 days 값 테스트
            for days in [7, 30, 90]:
                result = get_stock_chart("005930", days, mock_session)
                assert result.ticker == "005930"

    def test_get_stock_signals_empty_history(self):
        """시그널 히스토리 조회 - 빈 히스토리"""
        from services.api_gateway.routes.stocks import get_stock_signals

        mock_session = Mock()
        mock_repo = Mock()
        mock_repo.get_by_ticker.return_value = []

        with patch(
            "services.api_gateway.routes.stocks.SignalRepository",
            return_value=mock_repo,
        ):
            result = get_stock_signals("005930", mock_session)
            assert result.ticker == "005930"
            assert result.total_signals == 0
            assert result.open_signals == 0
            assert result.closed_signals == 0


class TestCalculateSmartMoneyScore:
    """SmartMoney 점수 계산 단위 테스트"""

    def test_calculate_smartmoney_score_empty(self):
        """빈 데이터면 기본값 50 반환"""
        from services.api_gateway.routes.stocks import calculate_smartmoney_score

        result = calculate_smartmoney_score([])
        assert result == 50.0

    def test_calculate_smartmoney_score_foreign_only_buying(self):
        """외국인만 순매수 시 점수 상승"""
        from services.api_gateway.routes.stocks import calculate_smartmoney_score
        from src.database.models import InstitutionalFlow
        from datetime import date

        flows = [
            InstitutionalFlow(
                ticker="005930",
                date=date(2024, 1, 10),
                foreign_net_5d=5000000,  # +500만주
                inst_net_5d=0,
                foreign_consecutive_days=5,
                is_double_buy=False,
            )
        ]

        result = calculate_smartmoney_score(flows)
        # 외국인 점수 = min(100, 50 + 5000000/100000) = 100
        # 기관 점수 = 50
        # 연속일수 점수 = min(100, 5*10) = 50
        # 이중 매수 = 0
        # 전체 = 100*0.4 + 50*0.3 + 50*0.15 = 40 + 15 + 7.5 = 62.5
        assert result > 60

    def test_calculate_smartmoney_score_inst_only_buying(self):
        """기관만 순매수 시 점수 상승"""
        from services.api_gateway.routes.stocks import calculate_smartmoney_score
        from src.database.models import InstitutionalFlow
        from datetime import date

        flows = [
            InstitutionalFlow(
                ticker="005930",
                date=date(2024, 1, 10),
                foreign_net_5d=0,
                inst_net_5d=3000000,  # +300만주
                foreign_consecutive_days=0,
                is_double_buy=False,
            )
        ]

        result = calculate_smartmoney_score(flows)
        # 외국인 점수 = 50
        # 기관 점수 = min(100, 50 + 3000000/100000) = 80
        # 연속일수 = 0
        # 전체 = 50*0.4 + 80*0.3 = 20 + 24 = 44
        assert result > 40

    def test_calculate_smartmoney_score_double_buying(self):
        """이중 매수(외국인+기관 동시 순매수) 시 최고 점수"""
        from services.api_gateway.routes.stocks import calculate_smartmoney_score
        from src.database.models import InstitutionalFlow
        from datetime import date

        flows = [
            InstitutionalFlow(
                ticker="005930",
                date=date(2024, 1, 10),
                foreign_net_5d=2000000,
                inst_net_5d=1500000,
                foreign_consecutive_days=3,
                is_double_buy=True,  # 이중 매수
            )
        ]

        result = calculate_smartmoney_score(flows)
        # 외국인 점수 = 50 + 20 = 70
        # 기관 점수 = 50 + 15 = 65
        # 연속일수 점수 = 30
        # 이중 매수 점수 = 20
        # 전체 = 70*0.4 + 65*0.3 + 30*0.15 + 20*0.15 = 28 + 19.5 + 4.5 + 3 = 55
        assert result >= 55

    def test_calculate_smartmoney_score_both_selling(self):
        """외국인/기관 모두 순매도 시 점수 하락"""
        from services.api_gateway.routes.stocks import calculate_smartmoney_score
        from src.database.models import InstitutionalFlow
        from datetime import date

        flows = [
            InstitutionalFlow(
                ticker="005930",
                date=date(2024, 1, 10),
                foreign_net_5d=-2000000,  # -200만주
                inst_net_5d=-1500000,  # -150만주
                foreign_consecutive_days=0,
                is_double_buy=False,
            )
        ]

        result = calculate_smartmoney_score(flows)
        # 외국인 점수 = max(0, 50 - 20) = 30
        # 기관 점수 = max(0, 50 - 15) = 35
        # 연속일수 = 0
        # 이중 매수 = 0
        # 전체 = 30*0.4 + 35*0.3 = 12 + 10.5 = 22.5
        assert result < 50

    def test_calculate_smartmoney_score_consecutive_days(self):
        """외국인 연속 순매수 일수 반영"""
        from services.api_gateway.routes.stocks import calculate_smartmoney_score
        from src.database.models import InstitutionalFlow
        from datetime import date

        # 10일 연속 순매수
        flows_long = [
            InstitutionalFlow(
                ticker="005930",
                date=date(2024, 1, 10),
                foreign_net_5d=1000000,
                inst_net_5d=0,
                foreign_consecutive_days=10,
                is_double_buy=False,
            )
        ]

        result = calculate_smartmoney_score(flows_long)
        # 외국인 점수 = 60
        # 연속일수 점수 = min(100, 10*10) = 100
        # 전체 = 60*0.4 + 50*0.3 + 100*0.15 = 24 + 15 + 15 = 54
        assert result >= 54

    def test_calculate_smartmoney_score_range(self):
        """점수 범위 검증: 0~100 사이"""
        from services.api_gateway.routes.stocks import calculate_smartmoney_score
        from src.database.models import InstitutionalFlow
        from datetime import date

        # 다양한 시나리오 테스트
        test_cases = [
            # (foreign_5d, inst_5d, consecutive, is_double, expected_min, expected_max)
            (0, 0, 0, False, 30, 40),  # 중립: 35.0 (50*0.4 + 50*0.3 + 0*0.15 + 0*0.15)
            (10000000, 0, 0, False, 50, 60),  # 외국인 대량 순매수: 55 (100*0.4 + 50*0.3)
            (0, 10000000, 0, False, 45, 55),  # 기관 대량 순매수: 50 (50*0.4 + 100*0.3)
            (-10000000, 0, 0, False, 10, 20),  # 외국인 대량 순매도: 15 (0*0.4 + 50*0.3)
            (5000000, 5000000, 5, True, 75, 90),  # 이중 매수: 80.5
        ]

        for foreign_5d, inst_5d, consecutive, is_double, exp_min, exp_max in test_cases:
            flows = [
                InstitutionalFlow(
                    ticker="005930",
                    date=date(2024, 1, 10),
                    foreign_net_5d=foreign_5d,
                    inst_net_5d=inst_5d,
                    foreign_consecutive_days=consecutive,
                    is_double_buy=is_double,
                )
            ]
            result = calculate_smartmoney_score(flows)
            assert exp_min <= result <= exp_max, f"Score {result} not in range [{exp_min}, {exp_max}] for inputs ({foreign_5d}, {inst_5d}, {consecutive}, {is_double})"

    def test_calculate_smartmoney_score_multiple_days_average(self):
        """여러 날의 평균 계산"""
        from services.api_gateway.routes.stocks import calculate_smartmoney_score
        from src.database.models import InstitutionalFlow
        from datetime import date

        flows = [
            InstitutionalFlow(
                ticker="005930",
                date=date(2024, 1, 10),
                foreign_net_5d=2000000,
                inst_net_5d=1000000,
                foreign_consecutive_days=3,
                is_double_buy=False,
            ),
            InstitutionalFlow(
                ticker="005930",
                date=date(2024, 1, 11),
                foreign_net_5d=3000000,
                inst_net_5d=1500000,
                foreign_consecutive_days=4,
                is_double_buy=False,
            ),
        ]

        result = calculate_smartmoney_score(flows)
        # 평균: foreign_5d = 2500000, inst_5d = 1250000
        # foreign_score = 50 + 25 = 75
        # inst_score = 50 + 12.5 = 62.5
        # 연속일수 = 4 (max)
        # 이중 매수 = 0
        # 전체 = 75*0.4 + 62.5*0.3 + 40*0.15 = 30 + 18.75 + 6 = 54.75
        assert 0 <= result <= 100
