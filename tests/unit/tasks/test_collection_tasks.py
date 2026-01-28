"""
Collection Tasks Unit Tests
데이터 수집 Celery Tasks 테스트
"""

import pytest
from unittest.mock import Mock, patch, MagicMock


# ============================================================================
# Test Data
# ============================================================================

MOCK_STOCK_LIST = [
    {"ticker": "005930", "name": "삼성전자", "market": "KOSPI", "sector": "반도체"},
    {"ticker": "000660", "name": "SK하이닉스", "market": "KOSPI", "sector": "반도체"},
]

MOCK_DAILY_PRICES = [
    {"date": "2024-01-15", "open": 75000, "high": 76000, "low": 74500, "close": 75500, "volume": 1000000},
    {"date": "2024-01-16", "open": 75500, "high": 77000, "low": 75000, "close": 76500, "volume": 1200000},
]

MOCK_SUPPLY_DEMAND = {
    "005930": {
        "foreign_net_buy": 150000,
        "inst_net_buy": 80000,
    }
}


# ============================================================================
# Collection Tasks Tests
# ============================================================================

class TestCollectionTasks:
    """Collection Tasks 테스트"""

    def test_import_tasks(self):
        """Collection Tasks import 테스트"""
        from src.tasks.collection_tasks import (
            collect_stock_list,
            collect_daily_prices,
            collect_supply_demand,
            sync_all_data,
        )
        assert collect_stock_list is not None
        assert collect_daily_prices is not None
        assert collect_supply_demand is not None
        assert sync_all_data is not None

    @patch('src.tasks.collection_tasks.KRXCollector')
    @patch('src.tasks.collection_tasks.StockRepository')
    @patch('src.tasks.collection_tasks.SessionLocal')
    def test_collect_stock_list_success(self, mock_session_local, mock_repo_class, mock_krx_class):
        """종목 리스트 수집 성공 테스트"""
        from src.tasks.collection_tasks import collect_stock_list

        # Mock KRXCollector
        mock_collector = Mock()
        mock_krx_class.return_value = mock_collector
        mock_collector.fetch_stock_list.return_value = MOCK_STOCK_LIST

        # Mock session and repository
        mock_session = MagicMock()
        mock_session_local.return_value.__enter__.return_value = mock_session

        mock_repo = Mock()
        mock_repo_class.return_value = mock_repo

        # Execute
        result = collect_stock_list("KOSPI")

        # Verify
        assert result == 2  # 2 stocks in MOCK_STOCK_LIST
        mock_collector.fetch_stock_list.assert_called_once_with(market="KOSPI")

    @patch('src.tasks.collection_tasks.KRXCollector')
    @patch('src.tasks.collection_tasks.SessionLocal')
    def test_collect_stock_list_with_error(self, mock_session_local, mock_krx_class):
        """종목 리스트 수집 에러 발생 시 로깅 테스트"""
        from src.tasks.collection_tasks import collect_stock_list

        mock_collector = Mock()
        mock_krx_class.return_value = mock_collector
        mock_collector.fetch_stock_list.side_effect = Exception("KRX API error")

        mock_session = MagicMock()
        mock_session_local.return_value.__enter__.return_value = mock_session

        # Should raise exception (not caught in task)
        with pytest.raises(Exception, match="KRX API error"):
            collect_stock_list("KOSPI")

    @patch('src.tasks.collection_tasks.KRXCollector')
    @patch('src.tasks.collection_tasks.SessionLocal')
    def test_collect_daily_prices_success(self, mock_session_local, mock_krx_class):
        """일봉 데이터 수집 성공 테스트"""
        from src.tasks.collection_tasks import collect_daily_prices
        import pandas as pd

        mock_collector = Mock()
        mock_krx_class.return_value = mock_collector

        # Create mock DataFrame
        mock_df = pd.DataFrame([
            {"ticker": "005930", "date": "2024-01-15", "open": 75000, "high": 76000,
             "low": 74500, "close": 75500, "volume": 1000000}
        ])
        mock_collector.fetch_daily_prices.return_value = mock_df

        mock_session = MagicMock()
        mock_session_local.return_value.__enter__.return_value = mock_session

        # Collect prices
        result = collect_daily_prices("005930")

        # Verify
        assert result > 0  # Should return count of collected prices
        mock_collector.fetch_daily_prices.assert_called_once()

    @patch('src.tasks.collection_tasks.KRXCollector')
    @patch('src.tasks.collection_tasks.SessionLocal')
    def test_collect_daily_prices_empty_result(self, mock_session_local, mock_krx_class):
        """일봉 데이터 수집 빈 결과 테스트"""
        from src.tasks.collection_tasks import collect_daily_prices
        import pandas as pd

        mock_collector = Mock()
        mock_krx_class.return_value = mock_collector

        # Empty DataFrame
        mock_df = pd.DataFrame()
        mock_collector.fetch_daily_prices.return_value = mock_df

        # Collect prices with empty result
        result = collect_daily_prices("005930")

        # Verify
        assert result == 0

    @patch('src.tasks.collection_tasks.KRXCollector')
    @patch('src.tasks.collection_tasks.SessionLocal')
    def test_collect_supply_demand_success(self, mock_session_local, mock_krx_class):
        """수급 데이터 수집 성공 테스트"""
        from src.tasks.collection_tasks import collect_supply_demand
        import pandas as pd

        mock_collector = Mock()
        mock_krx_class.return_value = mock_collector

        # Create mock DataFrame
        mock_df = pd.DataFrame([
            {"ticker": "005930", "date": "2024-01-15", "foreign_net_buy": 150000,
             "inst_net_buy": 80000}
        ])
        mock_collector.fetch_supply_demand.return_value = mock_df

        mock_session = MagicMock()
        mock_session_local.return_value.__enter__.return_value = mock_session

        # Collect supply/demand
        result = collect_supply_demand("005930")

        # Verify
        assert result > 0
        mock_collector.fetch_supply_demand.assert_called_once()

    @patch('src.tasks.collection_tasks.collect_stock_list')
    @patch('src.tasks.collection_tasks.collect_daily_prices')
    @patch('src.tasks.collection_tasks.collect_supply_demand')
    @patch('src.tasks.collection_tasks.SessionLocal')
    def test_sync_all_data(self, mock_session_local, mock_supply, mock_prices, mock_list):
        """전체 데이터 동기화 테스트"""
        from src.tasks.collection_tasks import sync_all_data

        mock_list.return_value = 2  # 2 stocks collected
        mock_prices.return_value = 10  # 10 price records
        mock_supply.return_value = 5  # 5 supply/demand records

        # Mock database query for tickers
        mock_session = MagicMock()
        mock_session_local.return_value.__enter__.return_value = mock_session
        mock_session.execute.return_value.fetchall.return_value = [("005930",), ("000660",)]

        # Sync all data
        result = sync_all_data()

        # Verify all tasks were called
        assert mock_list.call_count == 2  # KOSPI + KOSDAQ
        assert "stocks" in result
        assert "daily_prices" in result
        assert "supply_demand" in result

    def test_celery_task_decorators(self):
        """Celery 태스크 데코레이터 확인 테스트"""
        from src.tasks.collection_tasks import (
            collect_stock_list,
            collect_daily_prices,
            collect_supply_demand,
            sync_all_data,
        )

        # Verify tasks have celery attributes
        assert hasattr(collect_stock_list, 'name')
        assert hasattr(collect_daily_prices, 'name')
        assert hasattr(collect_supply_demand, 'name')
        assert hasattr(sync_all_data, 'name')


# ============================================================================
# Integration Test Mocks
# ============================================================================

class TestCollectionTasksIntegrationMocks:
    """Collection Tasks 통합 테스트 (Mock 사용)"""

    @patch('src.tasks.collection_tasks.SessionLocal')
    def test_full_collection_workflow(self, mock_session_local):
        """전체 수집 워크플로우 테스트"""
        from src.tasks.collection_tasks import (
            collect_stock_list,
            collect_daily_prices,
            collect_supply_demand,
        )

        mock_session = MagicMock()
        mock_session_local.return_value.__enter__.return_value = mock_session

        # Note: These are basic import/structure tests
        # Full integration tests would require actual database
        assert collect_stock_list is not None
        assert collect_daily_prices is not None
        assert collect_supply_demand is not None
