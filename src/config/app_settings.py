#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KR Market Application Settings
Pydantic Settings v2 기반 환경변수 설정 관리
"""
from functools import lru_cache
from typing import Literal
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    """
    애플리케이션 설정 클래스

    Pydantic Settings v2를 사용하여 .env 파일에서 환경변수를 로드합니다.
    싱글톤 패턴으로 동작하여 애플리케이션 전체에서 동일한 설정 인스턴스를 사용합니다.
    """

    # === Pydantic Settings v2 설정 ===
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # === Database 설정 ===
    database_url: str = Field(
        default="postgresql://postgres:postgres@localhost:5433/kr_stock",
        description="PostgreSQL 데이터베이스 연결 URL",
    )

    # === Redis 설정 ===
    redis_url: str = Field(
        default="redis://localhost:6380/0",
        description="Redis 캐시 연결 URL",
    )

    # === Celery 설정 ===
    celery_broker_url: str = Field(
        default="redis://localhost:6380/1",
        description="Celery 메시지 브로커 URL",
    )
    celery_result_backend: str = Field(
        default="redis://localhost:6380/2",
        description="Celery 결과 저장 백엔드 URL",
    )

    # === Service URLs (마이크로서비스 간 통신) ===
    vcp_scanner_url: str = Field(
        default="http://localhost:5112",
        description="VCP Scanner 서비스 URL",
    )
    signal_engine_url: str = Field(
        default="http://localhost:5113",
        description="Signal Engine 서비스 URL",
    )
    market_analyzer_url: str = Field(
        default="http://localhost:5114",
        description="Market Analyzer 서비스 URL",
    )

    # === Gemini API 설정 ===
    gemini_api_key: str = Field(
        default="",
        description="Gemini API 키 (뉴스 감성 분석용)",
    )

    # === Kiwoom REST API 설정 ===
    kiwoom_app_key: str = Field(
        default="",
        description="Kiwoom REST API 앱 키",
    )
    kiwoom_secret_key: str = Field(
        default="",
        description="Kiwoom REST API 시크릿 키",
    )
    kiwoom_base_url: str = Field(
        default="https://api.kiwoom.com",
        description="Kiwoom REST API 기본 URL",
    )
    kiwoom_ws_url: str = Field(
        default="wss://api.kiwoom.com:10000/api/dostk/websocket",
        description="Kiwoom WebSocket URL",
    )
    use_kiwoom_rest: bool = Field(
        default=False,
        description="Kiwoom REST API 사용 여부",
    )
    use_kiwoom_mock: bool = Field(
        default=False,
        description="Kiwoom Mock 모드 사용 여부 (테스트용)",
    )

    # === Market Gate 환경변수 오버라이드 ===
    usd_krw_safe: float = Field(
        default=1350.0,
        description="Market Gate 안전 환율 (초록)",
    )
    usd_krw_warning: float = Field(
        default=1400.0,
        description="Market Gate 주의 환율 (노랑)",
    )
    usd_krw_danger: float = Field(
        default=1450.0,
        description="Market Gate 위험 환율 (빨강)",
    )

    # === Logging 설정 ===
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO",
        description="로그 레벨",
    )

    # === 유효성 검사 ===
    @field_validator("usd_krw_safe", "usd_krw_warning", "usd_krw_danger")
    @classmethod
    def validate_usd_krw_thresholds(cls, v: float, info) -> float:
        """환율 기준값 유효성 검사"""
        if v <= 0:
            raise ValueError(f"{info.field_name} must be positive")
        return v

    @field_validator("usd_krw_warning")
    @classmethod
    def validate_warning_threshold(cls, v: float, info) -> float:
        """경계 기준값이 안전 기준값보다 커야 함"""
        # safe 값에 접근하기 위해 info.data 사용
        if "usd_krw_safe" in info.data and v <= info.data["usd_krw_safe"]:
            raise ValueError("usd_krw_warning must be greater than usd_krw_safe")
        return v

    @field_validator("usd_krw_danger")
    @classmethod
    def validate_danger_threshold(cls, v: float, info) -> float:
        """위험 기준값이 경계 기준값보다 커야 함"""
        if "usd_krw_warning" in info.data and v <= info.data["usd_krw_warning"]:
            raise ValueError("usd_krw_danger must be greater than usd_krw_warning")
        return v

    # === 헬퍼 메서드 ===
    def is_kiwoom_available(self) -> bool:
        """Kiwoom API 사용 가능 여부 확인"""
        return self.use_kiwoom_rest and bool(self.kiwoom_app_key) and bool(self.kiwoom_secret_key)

    def is_gemini_available(self) -> bool:
        """Gemini API 사용 가능 여부 확인"""
        return bool(self.gemini_api_key)

    def get_market_gate_thresholds(self) -> tuple[float, float, float]:
        """Market Gate 환율 기준값 튜플 반환 (safe, warning, danger)"""
        return (self.usd_krw_safe, self.usd_krw_warning, self.usd_krw_danger)

    def get_service_urls(self) -> dict[str, str]:
        """모든 서비스 URL 딕셔너리 반환"""
        return {
            "vcp_scanner": self.vcp_scanner_url,
            "signal_engine": self.signal_engine_url,
            "market_analyzer": self.market_analyzer_url,
        }

    def get_celery_config(self) -> dict[str, str]:
        """Celery 설정 딕셔너리 반환"""
        return {
            "broker_url": self.celery_broker_url,
            "result_backend": self.celery_result_backend,
        }


# === 싱글톤 패턴 구현 ===
_settings: AppSettings | None = None


def get_settings() -> AppSettings:
    """
    싱글톤 패턴으로 AppSettings 인스턴스 반환

    최초 호출 시 .env 파일에서 환경변수를 로드하여 인스턴스를 생성하고,
    이후 호출에는 캐시된 인스턴스를 반환합니다.

    Returns:
        AppSettings: 애플리케이션 설정 인스턴스
    """
    global _settings
    if _settings is None:
        _settings = AppSettings()
    return _settings


def reload_settings() -> AppSettings:
    """
    환경변수를 다시 로드하여 새로운 AppSettings 인스턴스 생성

    .env 파일이 변경된 경우 설정을 갱신하기 위해 사용합니다.
    기존 싱글톤 인스턴스를 폐기하고 새로운 인스턴스를 생성합니다.

    Returns:
        AppSettings: 새로운 애플리케이션 설정 인스턴스
    """
    global _settings
    _settings = AppSettings()
    return _settings


# === lru_cache 기반 대안 (선택적 사용) ===
@lru_cache()
def get_cached_settings() -> AppSettings:
    """
    lru_cache를 사용한 싱글톤 패턴 (대안)

    참고: Pydantic Settings는 환경변수를 읽기 때문에
    lru_cache를 사용할 경우 캐시 무효화가 어려울 수 있습니다.
    일반적으로 get_settings() 함수 사용을 권장합니다.

    Returns:
        AppSettings: 애플리케이션 설정 인스턴스
    """
    return AppSettings()
