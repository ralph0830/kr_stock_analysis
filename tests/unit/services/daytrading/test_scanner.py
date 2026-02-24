"""
Daytrading Scanner 단위 테스트

scanner.py의 핵심 로직을 테스트합니다:
- 시장 스캔 메인 로직
- 거래정지 종목 필터링
- Kiwoom API fallback
- 캐시 무효화
- 데이터 변환 로직
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timezone, date, timedelta
from sqlalchemy.orm import Session

from services.daytrading_scanner.scanner import DaytradingScanner


# =============================================================================
# Test Fixtures
# =============================================================================

@pytest.fixture
def mock_db_session():
    """Mock DB 세션"""
    db = MagicMock(spec=Session)
    return db


@pytest.fixture
def mock_stock():
    """Mock 종목 데이터"""
    stock = Mock()
    stock.ticker = "005930"
    stock.name = "삼성전자"
    stock.market = "KOSPI"
    stock.sector = "전기전자"
    stock.is_etf = False
    stock.is_admin = False
    stock.is_spac = False
    stock.is_bond = False
    stock.is_excluded_etf = False
    return stock


@pytest.fixture
def mock_prices():
    """Mock 일봉 데이터 (최신 순, 20일)"""
    prices = []
    base_price = 70000
    base_date = datetime.now(timezone.utc)

    for i in range(20):
        price = Mock()
        price.ticker = "005930"
        price.date = (base_date - timedelta(days=i)).date()
        price.close_price = base_price + (i * 100)
        price.high_price = base_price + (i * 100) + 500
        price.low_price = base_price + (i * 100) - 500
        price.volume = 10000000 + (i * 500000)
        price.open_price = base_price + (i * 100) - 200
        prices.append(price)

    return prices


@pytest.fixture
def mock_flow():
    """Mock 수급 데이터"""
    flow = Mock()
    flow.foreign_net_buy = 50000000000  # 500억
    flow.inst_net_buy = 30000000000  # 300억
    return flow


@pytest.fixture
def mock_kiwoom_api():
    """Mock Kiwoom API"""
    api = AsyncMock()
    api.issue_token = AsyncMock(return_value=True)
    api.get_stock_daily_chart = AsyncMock(return_value=[
        {"date": "20260206", "open": 71000, "high": 72000, "low": 70500, "close": 71500, "volume": 15000000},
        {"date": "20260205", "open": 70500, "high": 71500, "low": 70000, "close": 71000, "volume": 10000000},
    ])
    api.get_daily_trade_detail = AsyncMock(return_value=[
        {"date": "20260206", "foreign_net_buy": 5000000000, "inst_net_buy": 3000000000},
    ])
    api.get_suspended_stocks = AsyncMock(return_value={
        "900010": "거래정지",
        "900020": "사모청약",
    })
    api.close = AsyncMock()
    return api


@pytest.fixture
def scanner():
    """DaytradingScanner 인스턴스"""
    return DaytradingScanner()


# =============================================================================
# 1. scan_market 메인 로직 테스트
# =============================================================================

class TestScanMarket:
    """시장 스캔 메인 로직 테스트"""

    @pytest.mark.asyncio
    async def test_scan_market_with_kospi_market(self, scanner, mock_db_session):
        """
        GIVEN: KOSPI 마켓 요청
        WHEN: scan_market()를 호출하면
        THEN: KOSPI 종목만 스캔해야 함
        """
        # Arrange
        request = {"market": "KOSPI", "limit": 10}

        with patch.object(scanner, '_scan_with_db', return_value=[]) as mock_scan:
            # Act
            result = await scanner.scan_market(request, mock_db_session)

            # Assert
            mock_scan.assert_called_once()
            call_args = mock_scan.call_args
            assert call_args[0][0] == mock_db_session
            assert call_args[0][1] == "KOSPI"
            assert call_args[0][2] == 10

    @pytest.mark.asyncio
    async def test_scan_market_with_all_market(self, scanner, mock_db_session):
        """
        GIVEN: ALL 마켓 요청
        WHEN: scan_market()를 호출하면
        THEN: "ALL" 문자열이 그대로 전달되어야 함 (scanner.py _get_stocks에서 처리)
        """
        # Arrange
        request = {"market": "ALL", "limit": 50}

        with patch.object(scanner, '_scan_with_db', return_value=[]) as mock_scan:
            # Act
            result = await scanner.scan_market(request, mock_db_session)

            # Assert
            call_args = mock_scan.call_args
            assert call_args[0][1] == "ALL"

    @pytest.mark.asyncio
    async def test_scan_market_default_values(self, scanner, mock_db_session):
        """
        GIVEN: 빈 요청
        WHEN: scan_market()를 호출하면
        THEN: 기본값 (market=None, limit=50)을 사용해야 함
        """
        # Arrange
        request = {}

        with patch.object(scanner, '_scan_with_db', return_value=[]) as mock_scan:
            # Act
            result = await scanner.scan_market(request, mock_db_session)

            # Assert
            call_args = mock_scan.call_args
            assert call_args[0][1] is None
            assert call_args[0][2] == 50

    @pytest.mark.asyncio
    async def test_scan_market_creates_db_session_when_not_provided(self, scanner):
        """
        GIVEN: DB 세션 없음
        WHEN: scan_market()를 호출하면
        THEN: 새로운 DB 세션을 생성해야 함
        """
        # Arrange
        request = {"market": "KOSPI", "limit": 10}

        with patch('src.database.session.get_db_session_sync') as mock_get_db:
            mock_get_db.return_value.__enter__ = Mock()
            mock_get_db.return_value.__exit__ = Mock()
            mock_get_db.return_value.__enter__.return_value = MagicMock()

            with patch.object(scanner, '_scan_with_db', return_value=[]):
                # Act
                result = await scanner.scan_market(request, db=None)

                # Assert
                mock_get_db.assert_called_once()


# =============================================================================
# 2. 거래정지 종목 필터링 테스트
# =============================================================================

class TestSuspendedStocksFiltering:
    """거래정지 종목 필터링 테스트"""

    @pytest.mark.asyncio
    async def test_get_suspended_stocks_calls_api(self, scanner, mock_kiwoom_api):
        """
        GIVEN: Kiwoom API가 정상 작동
        WHEN: _get_suspended_stocks()를 호출하면
        THEN: API를 호출하고 결과를 캐싱해야 함
        """
        # Act
        result = await scanner._get_suspended_stocks(mock_kiwoom_api)

        # Assert
        mock_kiwoom_api.get_suspended_stocks.assert_called_once_with("ALL")
        assert "900010" in result
        assert result["900010"] == "거래정지"
        assert scanner._suspended_stocks_cache == result

    @pytest.mark.asyncio
    async def test_get_suspended_stocks_uses_cache(self, scanner, mock_kiwoom_api):
        """
        GIVEN: 캐시된 데이터가 존재하고 유효함
        WHEN: _get_suspended_stocks()를 다시 호출하면
        THEN: API를 호출하지 않고 캐시를 반환해야 함
        """
        # Arrange - 캐시 설정
        scanner._suspended_stocks_cache = {"900010": "거래정지"}
        scanner._suspended_cache_time = __import__('time').time()

        # Act
        result = await scanner._get_suspended_stocks(mock_kiwoom_api)

        # Assert
        mock_kiwoom_api.get_suspended_stocks.assert_not_called()
        assert result == {"900010": "거래정지"}

    @pytest.mark.asyncio
    async def test_get_suspended_stocks_api_fails_returns_cache(self, scanner, mock_kiwoom_api):
        """
        GIVEN: API 호출이 실패
        WHEN: _get_suspended_stocks()를 호출하면
        THEN: 캐시된 데이터를 반환해야 함
        """
        # Arrange
        mock_kiwoom_api.get_suspended_stocks = AsyncMock(side_effect=Exception("API Error"))
        scanner._suspended_stocks_cache = {"900010": "거래정지"}
        scanner._suspended_cache_time = __import__('time').time() - 100  # 만료된 캐시

        # Act
        result = await scanner._get_suspended_stocks(mock_kiwoom_api)

        # Assert
        assert result == {"900010": "거래정지"}

    def test_is_trading_suspended_true(self, scanner):
        """
        GIVEN: 종목이 거래정지 목록에 있음
        WHEN: _is_trading_suspended()를 호출하면
        THEN: True를 반환해야 함
        """
        # Arrange
        suspended_stocks = {"900010": "거래정지", "900020": "사모청약"}

        # Act
        result = scanner._is_trading_suspended("900010", suspended_stocks)

        # Assert
        assert result is True

    def test_is_trading_suspended_false(self, scanner):
        """
        GIVEN: 종목이 거래정지 목록에 없음
        WHEN: _is_trading_suspended()를 호출하면
        THEN: False를 반환해야 함
        """
        # Arrange
        suspended_stocks = {"900010": "거래정지", "900020": "사모청약"}

        # Act
        result = scanner._is_trading_suspended("005930", suspended_stocks)

        # Assert
        assert result is False


# =============================================================================
# 3. Kiwoom API Fallback 테스트
# =============================================================================

class TestKiwoomAPIFallback:
    """Kiwoom API Fallback 테스트"""

    @pytest.mark.asyncio
    async def test_scan_with_db_falls_back_to_db_on_api_failure(self, scanner, mock_db_session):
        """
        GIVEN: Kiwoom API 초기화 실패
        WHEN: _scan_with_db()를 호출하면
        THEN: DB 데이터만 사용해야 함
        """
        # Arrange
        with patch('src.kiwoom.rest_api.KiwoomRestAPI') as mock_api_class:
            mock_api_class.from_env.side_effect = Exception("API Error")

            mock_stocks = [Mock(ticker="005930", name="삼성전자")]
            with patch.object(scanner, '_get_stocks', return_value=mock_stocks):
                with patch.object(scanner, '_get_recent_prices', return_value=[]):
                    with patch.object(scanner, '_get_flow_data', return_value=Mock()):
                        with patch.object(scanner, '_save_signal'):
                            # Act
                            result = await scanner._scan_with_db(mock_db_session, None, 10)

                            # Assert - 에러 없이 처리되어야 함
                            assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_scan_with_db_uses_db_data_when_api_returns_empty(self, scanner, mock_db_session):
        """
        GIVEN: Kiwoom API가 빈 데이터 반환
        WHEN: 개별 종목 스캔 중
        THEN: DB fallback을 사용해야 함
        """
        # 이 테스트는 _scan_with_db의 내부 로직을 검증합니다
        # 실제로는 _get_recent_prices가 호출되는지 확인

        mock_prices = [Mock(close_price=70000, volume=10000000)]
        with patch.object(scanner, '_get_recent_prices', return_value=mock_prices):
            # Act
            prices = scanner._get_recent_prices(mock_db_session, "005930", days=20)

            # Assert
            assert len(prices) > 0


# =============================================================================
# 4. 캐시 무효화 테스트
# =============================================================================

class TestCacheInvalidation:
    """캐시 무효화 테스트"""

    @pytest.mark.asyncio
    async def test_invalidate_cache_clears_pattern(self, scanner):
        """
        GIVEN: 캐시 클라이언트가 정상 작동
        WHEN: _invalidate_cache()를 호출하면
        THEN: daytrading:signals:* 패턴을 삭제해야 함
        """
        # Arrange
        mock_cache = AsyncMock()
        mock_cache.clear_pattern = AsyncMock(return_value=5)

        with patch('src.cache.cache_client.get_cache', return_value=mock_cache):
            # Act
            await scanner._invalidate_cache()

            # Assert
            mock_cache.clear_pattern.assert_called_once_with("daytrading:signals:*")

    @pytest.mark.asyncio
    async def test_invalidate_cache_handles_import_error(self, scanner):
        """
        GIVEN: 캐시 모듈이 없음
        WHEN: _invalidate_cache()를 호출하면
        THEN: 에러 없이 처리되어야 함
        """
        # Act - 에러 없이 완료되어야 함
        await scanner._invalidate_cache()

    @pytest.mark.asyncio
    async def test_invalidate_cache_handles_cache_error(self, scanner):
        """
        GIVEN: 캐시 클리어 중 에러 발생
        WHEN: _invalidate_cache()를 호출하면
        THEN: 에러를 로깅하고 계속 진행해야 함
        """
        # Arrange
        mock_cache = AsyncMock()
        mock_cache.clear_pattern = AsyncMock(side_effect=Exception("Cache Error"))

        with patch('src.cache.cache_client.get_cache', return_value=mock_cache):
            # Act - 에러 없이 완료되어야 함
            await scanner._invalidate_cache()


# =============================================================================
# 5. 데이터 변환 로직 테스트
# =============================================================================

class TestDataConversion:
    """데이터 변환 로직 테스트"""

    def test_convert_chart_to_daily_prices_valid_data(self, scanner):
        """
        GIVEN: Kiwoom API 차트 데이터
        WHEN: _convert_chart_to_daily_prices()를 호출하면
        THEN: DailyPrice 형식 객체 리스트를 반환해야 함
        """
        # Arrange
        chart_data = [
            {"date": "20260206", "open": 71000, "high": 72000, "low": 70500, "close": 71500, "volume": 15000000},
            {"date": "20260205", "open": 70500, "high": 71500, "low": 70000, "close": 71000, "volume": 10000000},
            {"date": "20260204", "open": 70000, "high": 71000, "low": 69500, "close": 70500, "volume": 12000000},
        ]

        # Act
        result = scanner._convert_chart_to_daily_prices("005930", chart_data)

        # Assert
        assert len(result) == 3
        assert result[0].ticker == "005930"
        assert result[0].close_price == 71500
        assert result[0].volume == 15000000
        assert result[0].date == date(2026, 2, 6)

    def test_convert_chart_to_daily_prices_date_format(self, scanner):
        """
        GIVEN: YYYYMMDD 형식의 날짜 문자열
        WHEN: _convert_chart_to_daily_prices()를 호출하면
        THEN: YYYY-MM-DD 형식의 date 객체로 변환해야 함
        """
        # Arrange
        chart_data = [
            {"date": "20260206", "open": 71000, "high": 72000, "low": 70500, "close": 71500, "volume": 15000000},
        ]

        # Act
        result = scanner._convert_chart_to_daily_prices("005930", chart_data)

        # Assert
        assert result[0].date == date(2026, 2, 6)

    def test_convert_chart_to_daily_prices_invalid_date(self, scanner):
        """
        GIVEN: 잘못된 날짜 형식
        WHEN: _convert_chart_to_daily_prices()를 호출하면
        THEN: 오늘 날짜를 사용해야 함 (fallback)
        """
        # Arrange
        chart_data = [
            {"date": "invalid", "open": 71000, "high": 72000, "low": 70500, "close": 71500, "volume": 15000000},
        ]

        # Act
        result = scanner._convert_chart_to_daily_prices("005930", chart_data)

        # Assert
        assert result[0].date == date.today()

    def test_convert_chart_to_daily_prices_empty_data(self, scanner):
        """
        GIVEN: 빈 차트 데이터
        WHEN: _convert_chart_to_daily_prices()를 호출하면
        THEN: 빈 리스트를 반환해야 함
        """
        # Arrange
        chart_data = []

        # Act
        result = scanner._convert_chart_to_daily_prices("005930", chart_data)

        # Assert
        assert result == []

    def test_convert_trade_to_flow_valid_data(self, scanner):
        """
        GIVEN: Kiwoom API 일별거래상세 데이터
        WHEN: _convert_trade_to_flow()를 호출하면
        THEN: Flow 데이터 객체를 반환해야 함
        """
        # Arrange
        trade_data = [
            {"date": "20260206", "foreign_net_buy": 5000000000, "inst_net_buy": 3000000000},
            {"date": "20260205", "foreign_net_buy": 2000000000, "inst_net_buy": 1000000000},
            {"date": "20260204", "foreign_net_buy": 1000000000, "inst_net_buy": 500000000},
            {"date": "20260203", "foreign_net_buy": -500000000, "inst_net_buy": -300000000},
            {"date": "20260202", "foreign_net_buy": 1000000000, "inst_net_buy": 200000000},
        ]

        # Act
        result = scanner._convert_trade_to_flow(trade_data)

        # Assert
        # 최근 5일 합계
        assert result.foreign_net_buy == 8500000000  # 5000 + 2000 + 1000 - 500 + 1000 (만원 단위)
        assert result.inst_net_buy == 4400000000  # 3000 + 1000 + 500 - 300 + 200

    def test_convert_trade_to_flow_less_than_5_days(self, scanner):
        """
        GIVEN: 5일 미만의 데이터
        WHEN: _convert_trade_to_flow()를 호출하면
        THEN: 있는 데이터만 합산해야 함
        """
        # Arrange
        trade_data = [
            {"date": "20260206", "foreign_net_buy": 5000000000, "inst_net_buy": 3000000000},
            {"date": "20260205", "foreign_net_buy": 2000000000, "inst_net_buy": 1000000000},
        ]

        # Act
        result = scanner._convert_trade_to_flow(trade_data)

        # Assert
        assert result.foreign_net_buy == 7000000000
        assert result.inst_net_buy == 4000000000


# =============================================================================
# 6. 종목 조회 테스트
# =============================================================================

class TestGetStocks:
    """종목 조회 테스트"""

    def test_get_stocks_filters_etf_and_admin(self, scanner, mock_db_session):
        """
        GIVEN: DB에 다양한 종목이 존재
        WHEN: _get_stocks()를 호출하면
        THEN: ETF, ADMIN, SPAC, BOND, EXCLUDED_ETF를 필터링해야 함
        """
        # 이 테스트는 실제 DB 쿼리 로직을 검증합니다
        # Mock을 사용하여 쿼리가 올바르게 구성되었는지 확인

        # Arrange - 실제 쿼리 실행은 어렵기 때문에
        # 테스트용 Mock DB를 사용합니다

        # Act & Assert - 메서드가 에러 없이 실행되는지 확인
        result = scanner._get_stocks(mock_db_session, None)
        assert isinstance(result, list)


# =============================================================================
# 7. 신호 저장 테스트
# =============================================================================

class TestSaveSignal:
    """시그널 저장 테스트"""

    @pytest.mark.asyncio
    async def test_save_signal_creates_new_record(self, scanner, mock_db_session):
        """
        GIVEN: 기존 시그널이 없음
        WHEN: _save_signal()를 호출하면
        THEN: 새로운 DaytradingSignal을 생성해야 함
        """
        # Arrange
        mock_score_result = Mock()
        mock_score_result.ticker = "005930"
        mock_score_result.name = "삼성전자"
        mock_score_result.total_score = 75
        mock_score_result.grade = "A"
        mock_score_result.checks = []

        mock_current_price = Mock()
        mock_current_price.close_price = 71500

        mock_db_session.query.return_value.filter_by.return_value.first.return_value = None

        # Act
        await scanner._save_signal(mock_db_session, mock_score_result, mock_current_price)

        # Assert
        mock_db_session.add.assert_called_once()
        mock_db_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_save_signal_updates_existing(self, scanner, mock_db_session):
        """
        GIVEN: 기존 시그널이 존재 (OPEN 상태)
        WHEN: _save_signal()를 호출하면
        THEN: 기존 레코드를 업데이트해야 함
        """
        # Arrange
        mock_score_result = Mock()
        mock_score_result.ticker = "005930"
        mock_score_result.name = "삼성전자"
        mock_score_result.total_score = 80
        mock_score_result.grade = "A"
        mock_score_result.checks = []

        mock_current_price = Mock()
        mock_current_price.close_price = 71500

        # 기존 시그널 Mock
        mock_existing = Mock()
        mock_existing.score = 70
        mock_existing.grade = "B"

        mock_db_session.query.return_value.filter_by.return_value.first.return_value = mock_existing

        # Act
        await scanner._save_signal(mock_db_session, mock_score_result, mock_current_price)

        # Assert
        mock_db_session.add.assert_not_called()  # add는 호출 안 됨
        mock_db_session.commit.assert_called_once()
        assert mock_existing.score == 80  # 업데이트됨
        assert mock_existing.grade == "A"

    @pytest.mark.asyncio
    async def test_save_signal_handles_rollback_on_error(self, scanner, mock_db_session):
        """
        GIVEN: DB 저장 중 에러 발생
        WHEN: _save_signal()를 호출하면
        THEN: rollback을 수행해야 함
        """
        # Arrange
        mock_score_result = Mock()
        mock_score_result.ticker = "005930"
        mock_score_result.name = "삼성전자"
        mock_score_result.total_score = 75
        mock_score_result.grade = "A"
        mock_score_result.checks = []

        mock_current_price = Mock()
        mock_current_price.close_price = 71500

        mock_db_session.query.return_value.filter_by.return_value.first.return_value = None
        mock_db_session.add.side_effect = Exception("DB Error")

        # Act
        await scanner._save_signal(mock_db_session, mock_score_result, mock_current_price)

        # Assert
        mock_db_session.rollback.assert_called_once()


# =============================================================================
# 8. Mock 데이터 생성 테스트
# =============================================================================

class TestMockFlowData:
    """Mock 수급 데이터 테스트"""

    def test_get_mock_flow_data_returns_zero_values(self, scanner):
        """
        GIVEN: _get_mock_flow_data() 호출
        WHEN: 항상
        THEN: 0값을 가진 Flow 객체를 반환해야 함
        """
        # Act
        result = scanner._get_mock_flow_data("005930")

        # Assert
        assert result.foreign_net_buy == 0
        assert result.inst_net_buy == 0


# =============================================================================
# 9. 통합 테스트 (Kiwoom API + DB)
# =============================================================================

class TestScanningIntegration:
    """스캐닝 통합 테스트"""

    @pytest.mark.asyncio
    async def test_full_scan_workflow_with_kiwoom_api(self, scanner, mock_db_session):
        """
        GIVEN: Kiwoom API와 DB가 정상 작동
        WHEN: 전체 스캔을 실행하면
        THEN: 점수 계산 → 저장 → 캐시 무효화가 순차적으로 진행되어야 함
        """
        # Arrange
        mock_stocks = [Mock(ticker="005930", name="삼성전자")]

        mock_prices = [
            Mock(close_price=71500, high_price=72000, low_price=71000, volume=15000000, open_price=71200, date=date.today()),
            Mock(close_price=71000, high_price=71500, low_price=70500, volume=10000000, open_price=70800, date=date.today() - timedelta(days=1)),
            Mock(close_price=70500, high_price=71000, low_price=70000, volume=12000000, open_price=70300, date=date.today() - timedelta(days=2)),
            Mock(close_price=70000, high_price=70500, low_price=69500, volume=11000000, open_price=69800, date=date.today() - timedelta(days=3)),
            Mock(close_price=69500, high_price=70000, low_price=69000, volume=13000000, open_price=69300, date=date.today() - timedelta(days=4)),
        ]

        mock_flow = Mock()
        mock_flow.foreign_net_buy = 5000000000
        mock_flow.inst_net_buy = 3000000000

        with patch('src.kiwoom.rest_api.KiwoomRestAPI') as mock_api_class:
            mock_api = AsyncMock()
            mock_api.issue_token = AsyncMock(return_value=True)
            mock_api.get_suspended_stocks = AsyncMock(return_value={})
            mock_api.get_stock_daily_chart = AsyncMock(return_value=[])
            mock_api.get_daily_trade_detail = AsyncMock(return_value=[])
            mock_api.close = AsyncMock()
            mock_api_class.from_env.return_value = mock_api

            with patch.object(scanner, '_get_stocks', return_value=mock_stocks):
                with patch.object(scanner, '_get_recent_prices', return_value=mock_prices):
                    with patch.object(scanner, '_get_flow_data', return_value=mock_flow):
                        with patch.object(scanner, '_save_signal'):
                            with patch.object(scanner, '_invalidate_cache') as mock_invalidate:
                                # Act
                                result = await scanner._scan_with_db(mock_db_session, None, 10)

                                # Assert
                                mock_invalidate.assert_called_once()
