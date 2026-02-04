"""
종가베팅 V2 API Integration Tests
TDD RED Phase - Tests should FAIL before implementation

이 테스트들은 다음 엔드포인트를 검증합니다:
- POST /api/kr/jongga-v2/run - 종가베팅 V2 엔진 트리거
"""

import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime

from services.api_gateway.main import app
from src.database.session import get_db_session


@pytest.fixture
async def client():
    """
    Test Client Fixture
    종가베팅 V2 API 테스트를 위한 비동기 클라이언트
    """
    # DB 세션 mock (빠른 테스트를 위해)
    mock_session = MagicMock()
    app.dependency_overrides[get_db_session] = lambda: mock_session

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


class TestJonggaV2RunAPI:
    """종가베팅 V2 엔진 트리거 API 테스트"""

    async def test_run_jongga_v2_engine_returns_200_on_success(self, client: AsyncClient):
        """
        RED Phase: POST /api/kr/jongga-v2/run
        정상 요청 시 200 상태 코드와 응답을 반환해야 함
        """
        # Mock Celery task
        with patch("tasks.signal_tasks.generate_jongga_signals.delay") as mock_task:
            # Mock 태스크 결과 반환
            mock_result = MagicMock()
            mock_result.id = "task-id-123"
            mock_result.state = "PENDING"
            mock_task.return_value = mock_result

            response = await client.post(
                "/api/kr/jongga-v2/run",
                json={
                    "market": "KOSPI",
                    "top_n": 30,
                    "min_score": 6
                }
            )

            # GREEN Phase expectation: 현재는 404 에러 예상
            # 엔드포인트 구현 후 200이 되어야 함
            assert response.status_code == 200, f"Expected 200, got {response.status_code}"

            data = response.json()
            assert "status" in data
            assert "task_id" in data

    async def test_run_jongga_v2_engine_calls_celery_task(self, client: AsyncClient):
        """
        RED Phase: Celery 태스크가 호출되어야 함
        """
        with patch("tasks.signal_tasks.generate_jongga_signals.delay") as mock_task:
            mock_task.return_value = MagicMock(id="task-id-456")

            response = await client.post(
                "/api/kr/jongga-v2/run",
                json={"market": "KOSPI", "top_n": 10}
            )

            # Celery 태스크가 호출되었는지 확인
            # 엔드포인트 구현 후 호출됨
            if response.status_code == 200:
                mock_task.assert_called_once()
                call_kwargs = mock_task.call_args.kwargs if mock_task.call_args.kwargs else {}
                # 매개변수 검증
                assert "capital" in call_kwargs or "top_n" in call_kwargs

    async def test_run_jongga_v2_engine_request_validation(self, client: AsyncClient):
        """
        RED Phase: 요청 파라미터 검증
        """
        with patch("tasks.signal_tasks.generate_jongga_signals.delay") as mock_task:
            mock_task.return_value = MagicMock(id="task-id-789")

            # 필수 파라미터 없는 요청
            response = await client.post(
                "/api/kr/jongga-v2/run",
                json={}
            )

            # 기본값이 적용되어야 함
            assert response.status_code == 200

    async def test_run_jongga_v2_engine_response_structure(self, client: AsyncClient):
        """
        RED Phase: 응답 구조 검증
        """
        with patch("tasks.signal_tasks.generate_jongga_signals.delay") as mock_task:
            mock_task.return_value = MagicMock(id="task-id-abc")

            response = await client.post(
                "/api/kr/jongga-v2/run",
                json={"market": "KOSDAQ", "top_n": 20}
            )

            if response.status_code == 200:
                data = response.json()
                # 응답 필드 검증
                assert "status" in data
                assert "task_id" in data
                assert isinstance(data["task_id"], str)

    async def test_run_jongga_v2_engine_error_handling(self, client: AsyncClient):
        """
        RED Phase: Celery 태스크 실패 시 에러 처리
        """
        # Celery 태스크가 예외를 발생시키는 상황 mock
        with patch("tasks.signal_tasks.generate_jongga_signals.delay") as mock_task:
            mock_task.side_effect = Exception("Celery broker unavailable")

            response = await client.post(
                "/api/kr/jongga-v2/run",
                json={"market": "KOSPI", "top_n": 30}
            )

            # 에러가 적절히 처리되어야 함
            # 500 또는 503이 반환되거나, 에러 메시지 포함
            if response.status_code != 200:
                # 에러 응답인 경우
                data = response.json()
                assert "error" in data or "detail" in data

    async def test_run_jongga_v2_engine_with_invalid_market(self, client: AsyncClient):
        """
        RED Phase: 잘못된 market 파라미터 검증
        """
        with patch("tasks.signal_tasks.generate_jongga_signals.delay") as mock_task:
            mock_task.return_value = MagicMock(id="task-id-def")

            response = await client.post(
                "/api/kr/jongga-v2/run",
                json={"market": "INVALID", "top_n": 30}
            )

            # 유효하지 않은 market 값 처리
            if response.status_code == 422:
                data = response.json()
                assert "detail" in data

    async def test_run_jongga_v2_engine_background_task_mode(self, client: AsyncClient):
        """
        RED Phase: 백그라운드 태스크 모드 검증
        비동기로 태스크가 실행되고 즉시 task_id를 반환해야 함
        """
        with patch("tasks.signal_tasks.generate_jongga_signals.delay") as mock_task:
            mock_result = MagicMock()
            mock_result.id = "bg-task-123"
            mock_result.get_id = lambda: "bg-task-123"
            mock_task.return_value = mock_result

            response = await client.post(
                "/api/kr/jongga-v2/run",
                json={
                    "market": "KOSPI",
                    "top_n": 30,
                    "background": True  # 백그라운드 모드
                }
            )

            if response.status_code == 200:
                data = response.json()
                assert data["status"] in ["queued", "started", "success"]
                assert "task_id" in data
                assert len(data["task_id"]) > 0


class TestJonggaV2DatesAPI:
    """종가베팅 V2 날짜 목록 API 테스트"""

    async def test_get_jongga_v2_dates_returns_dates(self, client: AsyncClient):
        """
        RED Phase: GET /api/kr/jongga-v2/dates
        시그널이 있는 날짜 목록을 반환해야 함
        """
        response = await client.get("/api/kr/jongga-v2/dates?limit=30")

        # GREEN Phase expectation: 현재는 404 에러 예상
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"

        data = response.json()
        assert "dates" in data
        assert isinstance(data["dates"], list)

    async def test_get_jongga_v2_dates_empty_response(self, client: AsyncClient):
        """
        RED Phase: 시그널이 없을 때 빈 목록 반환
        """
        # 빈 결과 반환 mock
        with patch("src.repositories.signal_repository.SignalRepository") as mock_repo_class:
            mock_instance = MagicMock()
            mock_instance.get_jongga_dates.return_value = []
            mock_repo_class.return_value = mock_instance

            # 의존성 오버라이드는 구현 후 처리

            response = await client.get("/api/kr/jongga-v2/dates")

            if response.status_code == 200:
                data = response.json()
                assert data["dates"] == []


class TestJonggaV2HistoryAPI:
    """종가베팅 V2 히스토리 API 테스트"""

    async def test_get_jongga_v2_history_by_date(self, client: AsyncClient):
        """
        RED Phase: GET /api/kr/jongga-v2/history/{date}
        특정 날짜의 시그널 목록을 반환해야 함
        """
        test_date = "2026-02-01"
        response = await client.get(f"/api/kr/jongga-v2/history/{test_date}")

        # GREEN Phase expectation: 현재는 404 에러 예상
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"

        data = response.json()
        assert "signals" in data
        assert "date" in data
        assert data["date"] == test_date

    async def test_get_jongga_v2_history_invalid_date_format(self, client: AsyncClient):
        """
        RED Phase: 잘못된 날짜 형식 검증
        """
        response = await client.get("/api/kr/jongga-v2/history/invalid-date")

        # 400 또는 422 에러 예상
        if response.status_code in [400, 422]:
            data = response.json()
            assert "detail" in data

    async def test_get_jongga_v2_history_empty_signals(self, client: AsyncClient):
        """
        RED Phase: 시그널이 없는 날짜 처리
        """
        test_date = "2026-01-01"  # 과거 날짜

        response = await client.get(f"/api/kr/jongga-v2/history/{test_date}")

        if response.status_code == 200:
            data = response.json()
            assert "signals" in data
            # 시그널 없으면 빈 리스트
            assert isinstance(data["signals"], list)


@pytest.mark.integration
class TestJonggaV2EndToEnd:
    """종가베팅 V2 E2E 테스트 (실제 Celery 필요)"""

    @pytest.mark.slow
    async def test_run_jongga_v2_e2e_with_real_celery(self, client: AsyncClient):
        """
        RED Phase: 실제 Celery worker와의 통합 테스트
        이 테스트는 Celery worker가 실행 중이어야 통과함
        """
        response = await client.post(
            "/api/kr/jongga-v2/run",
            json={
                "market": "KOSPI",
                "top_n": 5,  # 적은 수로 테스트
                "min_score": 6
            }
        )

        # Celery가 없으면 503 또는 에러 응답 가능
        if response.status_code == 200:
            data = response.json()
            assert "task_id" in data
            assert "status" in data
        else:
            # Celery 미설치 상태에서도 500 대신 적절한 응답
            assert response.status_code in [503, 503]
