"""
Trigger Routes Unit Tests
TDD GREEN Phase - Tests should pass with implementation
"""



class TestTriggerRoutesUnit:
    """Trigger Routes 단위 테스트"""

    def test_trigger_vcp_scan(self):
        """VCP 스캔 트리거"""
        from services.api_gateway.routes.triggers import VCPScanResponse
        from services.api_gateway.schemas import VCPScanResponse

        # Test response model validation
        response = VCPScanResponse(
            status="completed",
            scanned_count=100,
            found_signals=5,
            started_at="2024-01-27T10:00:00",
            completed_at="2024-01-27T10:05:00",
        )
        assert response.status == "completed"
        assert response.scanned_count == 100

    def test_trigger_signal_generation(self):
        """시그널 생성 트리거"""
        from services.api_gateway.routes.triggers import SignalGenerationResponse
        from services.api_gateway.schemas import SignalGenerationResponse

        # Test response model validation
        response = SignalGenerationResponse(
            status="completed",
            generated_count=10,
            started_at="2024-01-27T10:00:00",
            completed_at="2024-01-27T10:02:00",
        )
        assert response.status == "completed"
        assert response.generated_count == 10

    def test_get_scan_status(self):
        """스캔 상태 조회"""
        from services.api_gateway.routes.triggers import get_scan_status
        from services.api_gateway.schemas import ScanStatusResponse

        result = get_scan_status()
        assert isinstance(result, ScanStatusResponse)
        assert "vcp_scan_status" in result.dict()
        assert "signal_generation_status" in result.dict()

    def test_vcp_scan_response_model(self):
        """VCPScanResponse 모델"""
        from services.api_gateway.schemas import VCPScanResponse

        response = VCPScanResponse(
            status="completed",
            scanned_count=100,
            found_signals=5,
            started_at="2024-01-27T10:00:00",
            completed_at="2024-01-27T10:05:00",
        )
        assert response.status == "completed"
        assert response.scanned_count == 100

    def test_signal_generation_response_model(self):
        """SignalGenerationResponse 모델"""
        from services.api_gateway.schemas import SignalGenerationResponse

        response = SignalGenerationResponse(
            status="completed",
            generated_count=10,
            started_at="2024-01-27T10:00:00",
            completed_at="2024-01-27T10:02:00",
        )
        assert response.status == "completed"
        assert response.generated_count == 10

    def test_scan_status_response_model(self):
        """ScanStatusResponse 모델"""
        from services.api_gateway.schemas import ScanStatusResponse

        response = ScanStatusResponse(
            vcp_scan_status="idle",
            signal_generation_status="idle",
            last_vcp_scan="2024-01-27T10:00:00",
            last_signal_generation="2024-01-27T10:00:00",
        )
        assert response.vcp_scan_status == "idle"
        assert response.signal_generation_status == "idle"

    def test_vcp_signal_item(self):
        """VCPSignalItem 모델"""
        from services.api_gateway.schemas import VCPSignalItem
        from datetime import datetime, timezone

        item = VCPSignalItem(
            ticker="005930",
            name="삼성전자",
            market="KOSPI",
            signal_type="VCP",
            score=85.5,
            grade="A",
            signal_date="2024-01-27",
            entry_price=80000,
            target_price=88000,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        assert item.ticker == "005930"
        assert item.grade == "A"

    def test_get_scan_state(self):
        """스캔 상태 조회"""
        from services.api_gateway.routes.triggers import get_scan_state

        state = get_scan_state()
        assert isinstance(state, dict)
        assert "vcp_scan_status" in state

    def test_update_scan_state(self):
        """스캔 상태 업데이트"""
        from services.api_gateway.routes.triggers import update_scan_state, get_scan_state

        update_scan_state(vcp_scan_status="running")
        state = get_scan_state()
        assert state["vcp_scan_status"] == "running"

        # Reset
        update_scan_state(vcp_scan_status="idle")
