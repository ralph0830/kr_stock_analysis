"""
리소스 모니터링 테스트

TDD 방식으로 작성되었습니다.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch
from datetime import datetime, timezone

from src.monitoring.resource_monitor import (
    ResourceMonitor,
    ResourceUsage,
    MemoryStats,
    get_resource_monitor,
)


# =============================================================================
# Test Fixtures
# =============================================================================

@pytest.fixture
def resource_monitor():
    """테스트용 ResourceMonitor fixture"""
    return ResourceMonitor(
        check_interval_seconds=1,
        cpu_threshold_percent=80.0,
        memory_threshold_percent=80.0,
    )


# =============================================================================
# Test 1: 리소스 사용량 조회
# =============================================================================

class TestResourceUsage:
    """리소스 사용량 조회 검증"""

    @patch('src.monitoring.resource_monitor.psutil.cpu_percent', return_value=45.5)
    @patch('src.monitoring.resource_monitor.psutil.virtual_memory')
    def test_get_current_usage(self, mock_memory, mock_cpu, resource_monitor):
        """
        GIVEN: ResourceMonitor 인스턴스
        WHEN: get_current_usage()를 호출하면
        THEN: 현재 CPU 및 메모리 사용량을 반환해야 함
        """
        # Arrange: psutil mock 설정
        mock_mem = Mock()
        mock_mem.total = 8_000_000_000  # 8GB
        mock_mem.available = 4_000_000_000  # 4GB
        mock_mem.used = 4_000_000_000
        mock_mem.percent = 50.0
        mock_memory.return_value = mock_mem

        # Act
        usage = resource_monitor.get_current_usage()

        # Assert
        assert usage.cpu_percent == 45.5
        assert usage.memory.total == 8_000_000_000
        assert usage.memory.percent == 50.0
        assert isinstance(usage.timestamp, datetime)

    @patch('src.monitoring.resource_monitor.psutil.cpu_percent', return_value=95.0)
    @patch('src.monitoring.resource_monitor.psutil.virtual_memory')
    def test_to_dict_conversion(self, mock_memory, mock_cpu, resource_monitor):
        """
        GIVEN: ResourceUsage 객체
        WHEN: to_dict()를 호출하면
        THEN: 딕셔너리로 변환되어야 함
        """
        # Arrange
        mock_mem = Mock()
        mock_mem.total = 8_000_000_000
        mock_mem.available = 1_000_000_000
        mock_mem.used = 7_000_000_000
        mock_mem.percent = 87.5
        mock_memory.return_value = mock_mem

        # Act
        usage = resource_monitor.get_current_usage()
        usage_dict = usage.to_dict()

        # Assert
        assert usage_dict["cpu_percent"] == 95.0
        assert usage_dict["memory_percent"] == 87.5
        assert "timestamp" in usage_dict


# =============================================================================
# Test 2: 알림 기능
# =============================================================================

class TestAlerts:
    """알림 기능 검증"""

    @patch('src.monitoring.resource_monitor.psutil.cpu_percent', return_value=85.0)
    @patch('src.monitoring.resource_monitor.psutil.virtual_memory')
    def test_cpu_alert_triggered(self, mock_memory, mock_cpu, resource_monitor):
        """
        GIVEN: CPU 사용량이 85%인 상황 (임계값 80%)
        WHEN: 알림 콜백을 등록하고 _check_alerts()를 호출하면
        THEN: 알림 콜백이 호출되어야 함
        """
        # Arrange
        mock_mem = Mock()
        mock_mem.total = 8_000_000_000
        mock_mem.available = 4_000_000_000
        mock_mem.used = 4_000_000_000
        mock_mem.percent = 50.0
        mock_memory.return_value = mock_mem

        alert_received = [False]

        def alert_callback(usage):
            alert_received[0] = True

        resource_monitor.on_alert(alert_callback)

        # Act
        usage = resource_monitor.get_current_usage()
        resource_monitor._check_alerts(usage)

        # Assert
        assert alert_received[0], "CPU 임계값 초과 시 알림 콜백이 호출되어야 함"

    @patch('src.monitoring.resource_monitor.psutil.cpu_percent', return_value=50.0)
    @patch('src.monitoring.resource_monitor.psutil.virtual_memory')
    def test_memory_alert_triggered(self, mock_memory, mock_cpu, resource_monitor):
        """
        GIVEN: 메모리 사용량이 85%인 상황 (임계값 80%)
        WHEN: 알림 콜백을 등록하고 _check_alerts()를 호출하면
        THEN: 알림 콜백이 호출되어야 함
        """
        # Arrange
        mock_mem = Mock()
        mock_mem.total = 8_000_000_000
        mock_mem.available = 1_200_000_000
        mock_mem.used = 6_800_000_000
        mock_mem.percent = 85.0
        mock_memory.return_value = mock_mem

        alert_received = [False]

        def alert_callback(usage):
            alert_received[0] = True

        resource_monitor.on_alert(alert_callback)

        # Act
        usage = resource_monitor.get_current_usage()
        resource_monitor._check_alerts(usage)

        # Assert
        assert alert_received[0], "메모리 임계값 초과 시 알림 콜백이 호출되어야 함"

    @patch('src.monitoring.resource_monitor.psutil.cpu_percent', return_value=70.0)
    @patch('src.monitoring.resource_monitor.psutil.virtual_memory')
    def test_no_alert_below_threshold(self, mock_memory, mock_cpu, resource_monitor):
        """
        GIVEN: CPU/메모리 사용량이 임계값 미만인 상황
        WHEN: _check_alerts()를 호출하면
        THEN: 알림 콜백이 호출되지 않아야 함
        """
        # Arrange
        mock_mem = Mock()
        mock_mem.total = 8_000_000_000
        mock_mem.available = 4_000_000_000
        mock_mem.used = 4_000_000_000
        mock_mem.percent = 50.0
        mock_memory.return_value = mock_mem

        call_count = [0]

        def alert_callback(usage):
            call_count[0] += 1

        resource_monitor.on_alert(alert_callback)

        # Act
        usage = resource_monitor.get_current_usage()
        resource_monitor._check_alerts(usage)

        # Assert
        assert call_count[0] == 0, "임계값 미만에서는 알림이 발생하지 않아야 함"


# =============================================================================
# Test 3: 모니터링 루프
# =============================================================================

class TestMonitorLoop:
    """모니터링 루프 검증"""

    @pytest.mark.asyncio
    async def test_start_stop_monitor(self, resource_monitor):
        """
        GIVEN: ResourceMonitor 인스턴스
        WHEN: start()와 stop()를 호출하면
        THEN: 모니터링이 시작되고 중지되어야 함
        """
        # Act: 시작
        await resource_monitor.start()

        # Assert: 실행 중
        assert resource_monitor.is_running() is True

        # Act: 중지
        await resource_monitor.stop()

        # Assert: 중지됨
        assert resource_monitor.is_running() is False

    @pytest.mark.asyncio
    async def test_monitor_periodic_checks(self, resource_monitor):
        """
        GIVEN: 1초 간격으로 설정된 모니터
        WHEN: 2.5초 동안 실행하면
        THEN: 최소 2회의 체크가 수행되어야 함
        """
        # Arrange
        check_count = [0]

        original_get_usage = resource_monitor.get_current_usage

        def mock_get_usage():
            check_count[0] += 1
            return original_get_usage()

        resource_monitor.get_current_usage = mock_get_usage

        # Act: 2.5초 동안 실행
        await resource_monitor.start()
        await asyncio.sleep(2.5)
        await resource_monitor.stop()

        # Assert: 최소 2회 체크 (start 시 1회 + 1초 후 1회 + 2초 후 1회)
        assert check_count[0] >= 2, f"최소 2회 체크되어야 함, 실제: {check_count[0]}"

    @pytest.mark.asyncio
    async def test_stats_tracking(self, resource_monitor):
        """
        GIVEN: 모니터링이 실행 중인 상황
        WHEN: 통계를 조회하면
        THEN: 올바른 통계 정보가 반환되어야 함
        """
        # Act: 모니터링 시작 후 중지
        await resource_monitor.start()
        await asyncio.sleep(0.1)
        await resource_monitor.stop()

        stats = resource_monitor.get_stats()

        # Assert
        assert stats["is_running"] is False
        assert stats["total_checks"] >= 1
        assert stats["cpu_threshold_percent"] == 80.0
        assert stats["memory_threshold_percent"] == 80.0


# =============================================================================
# Test 4: 싱글톤 패턴
# =============================================================================

class TestSingleton:
    """싱글톤 패턴 검증"""

    def test_get_resource_monitor_returns_same_instance(self):
        """
        GIVEN: get_resource_monitor() 함수
        WHEN: 여러 번 호출하면
        THEN: 동일한 인스턴스를 반환해야 함
        """
        # Act
        monitor1 = get_resource_monitor()
        monitor2 = get_resource_monitor()

        # Assert
        assert monitor1 is monitor2, "동일한 인스턴스를 반환해야 함"


# =============================================================================
# Test 5: 커스텀 임계값
# =============================================================================

class TestCustomThresholds:
    """커스텀 임계값 검증"""

    @patch('src.monitoring.resource_monitor.psutil.cpu_percent', return_value=75.0)
    @patch('src.monitoring.resource_monitor.psutil.virtual_memory')
    def test_custom_cpu_threshold(self, mock_memory, mock_cpu):
        """
        GIVEN: CPU 임계값이 70%로 설정된 모니터
        WHEN: CPU 사용량이 75%이면
        THEN: 알림이 발생해야 함
        """
        # Arrange: 커스텀 임계값
        monitor = ResourceMonitor(
            check_interval_seconds=1,
            cpu_threshold_percent=70.0,  # 낮은 임계값
        )

        mock_mem = Mock()
        mock_mem.total = 8_000_000_000
        mock_mem.available = 4_000_000_000
        mock_mem.used = 4_000_000_000
        mock_mem.percent = 50.0
        mock_memory.return_value = mock_mem

        alert_received = [False]

        def alert_callback(usage):
            alert_received[0] = True

        monitor.on_alert(alert_callback)

        # Act
        usage = monitor.get_current_usage()
        monitor._check_alerts(usage)

        # Assert
        assert alert_received[0], "커스텀 임계값 초과 시 알림 발생"
