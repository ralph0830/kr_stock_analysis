"""
구조화된 로깅 설정
Python logging 기반 JSON 포맷 로그 시스템
"""

import logging
import sys
import json
import time
from datetime import datetime, timezone
from typing import Any, Dict
from pathlib import Path


class JSONFormatter(logging.Formatter):
    """JSON 포맷 로그 포매터"""

    def format(self, record: logging.LogRecord) -> str:
        """로그 레코드를 JSON으로 변환"""
        log_data = {
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # 예외 정보 추가
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # extra 필드 추가 (extra_data 또는 __dict__에서 extra 찾기)
        if hasattr(record, "extra_data"):
            log_data["extra"] = record.extra_data
        else:
            # record의 모든 속성 중 표준 로그 속성이 아닌 것들을 extra로 추가
            standard_attrs = {
                "name", "msg", "args", "levelname", "levelno", "pathname", "filename",
                "module", "exc_info", "exc_text", "stack_info", "lineno", "funcName",
                "created", "msecs", "relativeCreated", "thread", "threadName",
                "processName", "process", "message", "asctime", "color_name",
            }
            extra_attrs = {}
            for key, value in record.__dict__.items():
                if key not in standard_attrs:
                    extra_attrs[key] = value
            if extra_attrs:
                log_data["extra"] = extra_attrs

        return json.dumps(log_data, ensure_ascii=False)


class ColoredFormatter(logging.Formatter):
    """컬러 콘솔 로그 포매터 (개발용)"""

    # ANSI 색상 코드
    COLORS = {
        "DEBUG": "\033[36m",    # 청록색
        "INFO": "\033[32m",     # 녹색
        "WARNING": "\033[33m",  # 노란색
        "ERROR": "\033[31m",    # 빨간색
        "CRITICAL": "\033[35m", # 마젠타색
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        """로그 레코드에 색상 적용"""
        levelname = record.levelname
        if levelname in self.COLORS:
            record.levelname = f"{self.COLORS[levelname]}{levelname}{self.RESET}"

        # 기본 포맷: [시간] [레벨] [로거] 메시지
        formatter = logging.Formatter(
            fmt="%(asctime)s [%(levelname)-8s] [%(name)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        return formatter.format(record)


def setup_logging(
    level: str = "INFO",
    log_file: str = None,
    json_output: bool = False,
    service_name: str = "kr_stock",
) -> None:
    """
    로깅 시스템 초기화

    Args:
        level: 로그 레벨 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: 로그 파일 경로 (None이면 파일 출력 없음)
        json_output: JSON 포맷 여부 (False이면 컬러 콘솔)
        service_name: 서비스 이름 (로거 식별용)
    """
    # 루트 로거 설정
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    # 기존 핸들러 제거
    root_logger.handlers.clear()

    # 콘솔 핸들러
    console_handler = logging.StreamHandler(sys.stdout)

    if json_output:
        # JSON 포맷 (프로덕션)
        console_handler.setFormatter(JSONFormatter())
    else:
        # 컬러 포맷 (개발)
        console_handler.setFormatter(ColoredFormatter())

    root_logger.addHandler(console_handler)

    # 파일 핸들러 (선택)
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(JSONFormatter())
        root_logger.addHandler(file_handler)

    # 서드파티 라이브러리 로그 레벨 조정
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("celery").setLevel(logging.WARNING)
    logging.getLogger("kombu").setLevel(logging.WARNING)

    # 시작 로그
    root_logger.info(f"Logging initialized: {service_name}, level={level}")


def get_logger(name: str) -> logging.Logger:
    """
    named logger 반환

    Args:
        name: 로거 이름 (보통 __name__ 사용)

    Returns:
        logging.Logger 인스턴스
    """
    return logging.getLogger(name)


class LogContext:
    """로그 컨텍스트 관리자 (extra 데이터 추가)"""

    def __init__(self, logger: logging.Logger, **extra_data):
        self.logger = logger
        self.extra_data = extra_data
        self.old_factory = None

    def __enter__(self):
        # 커스텀 레코드 팩토리 설정
        def record_factory(name, level, fn, lno, msg, args, exc_info, func=None, sinfo=None):
            record = self.old_factory(name, level, fn, lno, msg, args, exc_info, func, sinfo)
            record.extra_data = self.extra_data
            return record

        self.old_factory = logging.getLogRecordFactory()
        logging.setLogRecordFactory(record_factory)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        logging.setLogRecordFactory(self.old_factory)


def log_execution_time(logger: logging.Logger, operation: str):
    """
    실행 시간 측정 데코레이터

    Args:
        logger: 로거 인스턴스
        operation: 작업 이름

    Usage:
        @log_execution_time(logger, "API 호출")
        def fetch_data():
            ...
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                execution_time = time.time() - start_time
                logger.info(
                    f"{operation} completed",
                    extra={"execution_time": execution_time, "operation": operation}
                )
                return result
            except Exception as e:
                execution_time = time.time() - start_time
                logger.error(
                    f"{operation} failed: {str(e)}",
                    extra={"execution_time": execution_time, "operation": operation, "error": str(e)}
                )
                raise
        return wrapper
    return decorator
