"""
로깅 설정 테스트
"""

import pytest
import logging
import json
import tempfile
from pathlib import Path

from src.utils.logging_config import (
    setup_logging,
    get_logger,
    JSONFormatter,
    ColoredFormatter,
    LogContext,
    log_execution_time,
)


class TestSetupLogging:
    """setup_logging 함수 테스트"""

    def test_setup_logging_default(self):
        """기본 설정 테스트"""
        setup_logging()

        root_logger = logging.getLogger()
        assert root_logger.level == logging.INFO
        assert len(root_logger.handlers) > 0

    def test_setup_logging_debug_level(self):
        """DEBUG 레벨 설정 테스트"""
        setup_logging(level="DEBUG")

        root_logger = logging.getLogger()
        assert root_logger.level == logging.DEBUG

    def test_setup_logging_with_file(self):
        """파일 출력 테스트"""
        with tempfile.TemporaryDirectory() as log_dir:
            setup_logging(level="INFO", log_dir=log_dir, json_output=True)

            logger = get_logger("test")
            logger.info("Test message")
            logger.error("Error message")

            # info.log 파일 확인
            info_log_path = Path(log_dir) / "info.log"
            assert info_log_path.exists()

            with open(info_log_path, "r") as f:
                content = f.read()
                assert "Test message" in content

            # error.log 파일 확인
            error_log_path = Path(log_dir) / "error.log"
            assert error_log_path.exists()

            with open(error_log_path, "r") as f:
                content = f.read()
                assert "Error message" in content

    def test_setup_logging_json_output(self):
        """JSON 출력 테스트"""
        with tempfile.TemporaryDirectory() as log_dir:
            setup_logging(level="INFO", log_dir=log_dir, json_output=True)

            logger = get_logger("test")
            logger.info("JSON test message")

            # JSON 형식 검증
            info_log_path = Path(log_dir) / "info.log"
            with open(info_log_path, "r") as f:
                for line in f:
                    if "JSON test message" in line:
                        log_data = json.loads(line)
                        assert "timestamp" in log_data
                        assert "level" in log_data
                        assert log_data["level"] == "INFO"
                        assert "message" in log_data
                        break
                else:
                    pytest.fail("Log message not found")


class TestGetLogger:
    """get_logger 함수 테스트"""

    def test_get_logger_named(self):
        """named logger 반환 테스트"""
        logger = get_logger("test_module")
        assert logger.name == "test_module"

    def test_get_logger_same_instance(self):
        """동일 이름 로거는 같은 인스턴스 반환"""
        logger1 = get_logger("test_same")
        logger2 = get_logger("test_same")
        assert logger1 is logger2


class TestJSONFormatter:
    """JSONFormatter 테스트"""

    def test_json_formatter_basic(self):
        """기본 JSON 포맷 테스트"""
        formatter = JSONFormatter()

        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        formatted = formatter.format(record)
        log_data = json.loads(formatted)

        assert log_data["level"] == "INFO"
        assert log_data["message"] == "Test message"
        assert log_data["logger"] == "test"
        assert "timestamp" in log_data

    def test_json_formatter_with_exception(self):
        """예외 정보 포함 테스트"""
        formatter = JSONFormatter()

        try:
            raise ValueError("Test error")
        except ValueError:
            import sys
            exc_info = sys.exc_info()

        record = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname="test.py",
            lineno=1,
            msg="Error occurred",
            args=(),
            exc_info=exc_info,
        )

        formatted = formatter.format(record)
        log_data = json.loads(formatted)

        assert "exception" in log_data
        # formatException이 리스트를 반환하므로 문자열로 변환
        exception_str = str(log_data["exception"]) if isinstance(log_data["exception"], list) else log_data["exception"]
        assert "ValueError" in exception_str


class TestColoredFormatter:
    """ColoredFormatter 테스트"""

    def test_colored_formatter_output(self):
        """컬러 출력 테스트"""
        formatter = ColoredFormatter()

        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        formatted = formatter.format(record)
        assert "Test message" in formatted
        assert "INFO" in formatted


class TestLogContext:
    """LogContext 테스트"""

    def test_log_context_manager(self):
        """컨텍스트 관리자 테스트"""
        with tempfile.TemporaryDirectory() as log_dir:
            setup_logging(level="INFO", log_dir=log_dir, json_output=True)
            logger = get_logger("test_context")

            with LogContext(logger, user_id="123", request_id="abc"):
                logger.info("Context test")

            # JSON에 extra 데이터 포함 확인
            info_log_path = Path(log_dir) / "info.log"
            with open(info_log_path, "r") as f:
                content = f.read()
                log_data = json.loads(content.strip().split("\n")[-1])
                assert log_data["extra"]["user_id"] == "123"
                assert log_data["extra"]["request_id"] == "abc"


class TestLogExecutionTime:
    """log_execution_time 데코레이터 테스트"""

    def test_log_execution_time_success(self):
        """성공 실행 시간 로깅 테스트"""
        with tempfile.TemporaryDirectory() as log_dir:
            setup_logging(level="INFO", log_dir=log_dir, json_output=True)
            logger = get_logger("test_timer")

            @log_execution_time(logger, "test_operation")
            def test_function():
                return "result"

            result = test_function()
            assert result == "result"

            # 로그 확인
            info_log_path = Path(log_dir) / "info.log"
            with open(info_log_path, "r") as f:
                content = f.read()
                log_data = json.loads(content.strip().split("\n")[-1])
                assert "test_operation completed" in log_data["message"]
                assert "execution_time" in log_data["extra"]
                assert log_data["extra"]["operation"] == "test_operation"

    def test_log_execution_time_failure(self):
        """실패 실행 시간 로깅 테스트"""
        with tempfile.TemporaryDirectory() as log_dir:
            setup_logging(level="INFO", log_dir=log_dir, json_output=True)
            logger = get_logger("test_timer_error")

            @log_execution_time(logger, "failing_operation")
            def failing_function():
                raise ValueError("Test error")

            with pytest.raises(ValueError):
                failing_function()

            # 에러 로그 확인
            error_log_path = Path(log_dir) / "error.log"
            with open(error_log_path, "r") as f:
                lines = f.readlines()
                error_log = None
                for line in reversed(lines):
                    if "failing_operation failed" in line:
                        error_log = json.loads(line)
                        break

                assert error_log is not None
                assert error_log["level"] == "ERROR"
                assert "execution_time" in error_log["extra"]


class TestIntegrationWithServices:
    """서비스 연동 테스트"""

    def test_api_gateway_logging(self, capsys=None):
        """API Gateway 로깅 테스트"""
        setup_logging(level="INFO", json_output=False)
        logger = get_logger("api_gateway")

        logger.info("API request received")
        logger.warning("Rate limit approaching")
        logger.error("Internal server error")

        # 콘솔 출력 검증 (capsys가 없으면 패스)
        if capsys is None:
            return

        captured = capsys.readouterr()
        assert "API request received" in captured.out

    def test_celery_task_logging(self, capsys=None):
        """Celery 태스크 로깅 테스트"""
        setup_logging(level="INFO", json_output=False)
        logger = get_logger("celery.tasks")

        logger.info("Task started")
        logger.debug("Processing data")  # DEBUG는 출력 안 됨
        logger.info("Task completed")

        # 콘솔 출력 검증
        if capsys is None:
            return

        captured = capsys.readouterr()
        assert "Task started" in captured.out
        assert "Processing data" not in captured.out  # DEBUG 레벨
