#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
src/config/app_settings.py 테스트

Pydantic Settings v2 기반 AppSettings 클래스 테스트
- 기본값 테스트
- 환경변수 오버라이드 테스트
- API Key 존재 확인 테스트
- get_settings() 싱글톤 테스트
- reload_settings() 테스트
"""

import os
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from src.config.app_settings import (
    AppSettings,
    get_settings,
    reload_settings,
)


# =============================================================================
# AppSettings 기본값 테스트
# =============================================================================
class TestAppSettingsDefaults:
    """AppSettings 기본값 테스트"""

    def test_database_defaults(self):
        """Database 기본값 확인"""
        settings = AppSettings()

        assert settings.database_url == "postgresql://postgres:postgres@localhost:5433/ralph_stock"

    def test_redis_defaults(self):
        """Redis 기본값 확인"""
        settings = AppSettings()

        assert settings.redis_url == "redis://localhost:6380/0"

    def test_celery_defaults(self):
        """Celery 기본값 확인"""
        settings = AppSettings()

        assert settings.celery_broker_url == "redis://localhost:6380/1"
        assert settings.celery_result_backend == "redis://localhost:6380/2"

    def test_service_url_defaults(self):
        """서비스 URL 기본값 확인"""
        settings = AppSettings()

        assert settings.vcp_scanner_url == "http://localhost:5112"
        assert settings.signal_engine_url == "http://localhost:5113"
        assert settings.market_analyzer_url == "http://localhost:5114"

    def test_kiwoom_defaults(self):
        """Kiwoom REST API 기본값 확인"""
        # .env 파일 로드 방지를 위해 환경변수를 빈 값으로 설정
        with patch.dict(os.environ, {"KIWOOM_APP_KEY": "", "KIWOOM_SECRET_KEY": "", "USE_KIWOOM_REST": "false"}):
            settings = AppSettings()

            assert settings.kiwoom_app_key == ""
            assert settings.kiwoom_secret_key == ""
            assert settings.kiwoom_base_url == "https://api.kiwoom.com"
            assert settings.kiwoom_ws_url == "wss://api.kiwoom.com:10000/api/dostk/websocket"
            assert settings.use_kiwoom_rest is False
            assert settings.use_kiwoom_mock is False

    def test_market_gate_defaults(self):
        """Market Gate 환율 기준값 기본값 확인"""
        settings = AppSettings()

        assert settings.usd_krw_safe == 1350.0
        assert settings.usd_krw_warning == 1400.0
        assert settings.usd_krw_danger == 1450.0

    def test_log_level_default(self):
        """로그 레벨 기본값 확인"""
        settings = AppSettings()

        assert settings.log_level == "INFO"


# =============================================================================
# 환경변수 오버라이드 테스트
# =============================================================================
class TestEnvOverride:
    """환경변수 오버라이드 테스트"""

    def test_database_url_override(self):
        """DATABASE_URL 환경변수 오버라이드 테스트"""
        with patch.dict(os.environ, {"DATABASE_URL": "postgresql://user:pass@localhost:9999/test_db"}):
            settings = AppSettings()
            assert settings.database_url == "postgresql://user:pass@localhost:9999/test_db"

    def test_redis_url_override(self):
        """REDIS_URL 환경변수 오버라이드 테스트"""
        with patch.dict(os.environ, {"REDIS_URL": "redis://localhost:9999/5"}):
            settings = AppSettings()
            assert settings.redis_url == "redis://localhost:9999/5"

    def test_celery_urls_override(self):
        """Celery URL 환경변수 오버라이드 테스트"""
        with patch.dict(
            os.environ,
            {
                "CELERY_BROKER_URL": "redis://localhost:9999/9",
                "CELERY_RESULT_BACKEND": "redis://localhost:9999/10",
            },
        ):
            settings = AppSettings()
            assert settings.celery_broker_url == "redis://localhost:9999/9"
            assert settings.celery_result_backend == "redis://localhost:9999/10"

    def test_service_urls_override(self):
        """서비스 URL 환경변수 오버라이드 테스트"""
        with patch.dict(
            os.environ,
            {
                "VCP_SCANNER_URL": "http://scanner:5112",
                "SIGNAL_ENGINE_URL": "http://signal:5113",
                "MARKET_ANALYZER_URL": "http://analyzer:5114",
            },
        ):
            settings = AppSettings()
            assert settings.vcp_scanner_url == "http://scanner:5112"
            assert settings.signal_engine_url == "http://signal:5113"
            assert settings.market_analyzer_url == "http://analyzer:5114"

    def test_gemini_api_key_override(self):
        """GEMINI_API_KEY 환경변수 오버라이드 테스트"""
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test_gemini_key_12345"}):
            settings = AppSettings()
            assert settings.gemini_api_key == "test_gemini_key_12345"

    def test_kiwoom_settings_override(self):
        """Kiwoom REST API 환경변수 오버라이드 테스트"""
        with patch.dict(
            os.environ,
            {
                "KIWOOM_APP_KEY": "test_app_key",
                "KIWOOM_SECRET_KEY": "test_secret_key",
                "KIWOOM_BASE_URL": "https://test.kiwoom.com",
                "USE_KIWOOM_REST": "true",
            },
        ):
            settings = AppSettings()
            assert settings.kiwoom_app_key == "test_app_key"
            assert settings.kiwoom_secret_key == "test_secret_key"
            assert settings.kiwoom_base_url == "https://test.kiwoom.com"
            assert settings.use_kiwoom_rest is True

    def test_market_gate_thresholds_override(self):
        """Market Gate 환율 기준값 환경변수 오버라이드 테스트"""
        with patch.dict(
            os.environ,
            {
                "USD_KRW_SAFE": "1300.0",
                "USD_KRW_WARNING": "1350.0",
                "USD_KRW_DANGER": "1400.0",
            },
        ):
            settings = AppSettings()
            assert settings.usd_krw_safe == 1300.0
            assert settings.usd_krw_warning == 1350.0
            assert settings.usd_krw_danger == 1400.0

    def test_log_level_override(self):
        """LOG_LEVEL 환경변수 오버라이드 테스트"""
        with patch.dict(os.environ, {"LOG_LEVEL": "DEBUG"}):
            settings = AppSettings()
            assert settings.log_level == "DEBUG"


# =============================================================================
# 유효성 검사 테스트
# =============================================================================
class TestValidation:
    """유효성 검사 테스트"""

    def test_usd_krw_positive_values(self):
        """환율 기준값 양수 검증"""
        with pytest.raises(ValidationError):
            AppSettings(usd_krw_safe=-100.0)

    def test_warning_must_be_greater_than_safe(self):
        """경계 기준값이 안전 기준값보다 커야 함"""
        with pytest.raises(ValidationError):
            AppSettings(usd_krw_safe=1400.0, usd_krw_warning=1350.0)

    def test_danger_must_be_greater_than_warning(self):
        """위험 기준값이 경계 기준값보다 커야 함"""
        with pytest.raises(ValidationError):
            AppSettings(usd_krw_warning=1400.0, usd_krw_danger=1350.0)

    def test_valid_thresholds(self):
        """유효한 환율 기준값 생성 성공"""
        settings = AppSettings(usd_krw_safe=1300.0, usd_krw_warning=1350.0, usd_krw_danger=1400.0)
        assert settings.usd_krw_safe == 1300.0
        assert settings.usd_krw_warning == 1350.0
        assert settings.usd_krw_danger == 1400.0

    def test_log_level_enum_validation(self):
        """LOG_LEVEL Enum 유효성 검증"""
        # Pydantic v2에서는 Enum 타입에 맞지 않는 값이 들어오면 ValidationError 발생
        with pytest.raises(ValidationError):
            AppSettings(log_level="INVALID_LEVEL")

    def test_valid_log_levels(self):
        """유효한 LOG_LEVEL 값들"""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        for level in valid_levels:
            settings = AppSettings(log_level=level)
            assert settings.log_level == level


# =============================================================================
# 헬퍼 메서드 테스트
# =============================================================================
class TestHelperMethods:
    """헬퍼 메서드 테스트"""

    def test_is_kiwoom_available_with_all_settings(self):
        """Kiwoom 설정이 모두 있는 경우 True 반환"""
        settings = AppSettings(
            kiwoom_app_key="test_key",
            kiwoom_secret_key="test_secret",
            use_kiwoom_rest=True,
        )
        assert settings.is_kiwoom_available() is True

    def test_is_kiwoom_available_without_use_flag(self):
        """use_kiwoom_rest가 False인 경우 False 반환"""
        settings = AppSettings(
            kiwoom_app_key="test_key",
            kiwoom_secret_key="test_secret",
            use_kiwoom_rest=False,
        )
        assert settings.is_kiwoom_available() is False

    def test_is_kiwoom_available_without_keys(self):
        """API 키가 없는 경우 False 반환"""
        # .env 파일의 실제 API 키 로드 방지
        with patch.dict(os.environ, {"KIWOOM_APP_KEY": "", "KIWOOM_SECRET_KEY": ""}):
            settings = AppSettings(use_kiwoom_rest=True)
            assert settings.is_kiwoom_available() is False

    def test_is_gemini_available_with_key(self):
        """Gemini API 키가 있는 경우 True 반환"""
        settings = AppSettings(gemini_api_key="test_gemini_key")
        assert settings.is_gemini_available() is True

    def test_is_gemini_available_without_key(self):
        """Gemini API 키가 없는 경우 False 반환"""
        # .env 파일의 실제 API 키 로드 방지
        with patch.dict(os.environ, {"GEMINI_API_KEY": ""}):
            settings = AppSettings()
            assert settings.is_gemini_available() is False

    def test_get_market_gate_thresholds(self):
        """Market Gate 환율 기준값 튜플 반환 확인"""
        settings = AppSettings(
            usd_krw_safe=1300.0,
            usd_krw_warning=1350.0,
            usd_krw_danger=1400.0,
        )
        safe, warning, danger = settings.get_market_gate_thresholds()
        assert safe == 1300.0
        assert warning == 1350.0
        assert danger == 1400.0

    def test_get_service_urls(self):
        """서비스 URL 딕셔너리 반환 확인"""
        settings = AppSettings(
            vcp_scanner_url="http://scanner:5112",
            signal_engine_url="http://signal:5113",
            market_analyzer_url="http://analyzer:5114",
        )
        urls = settings.get_service_urls()
        assert urls["vcp_scanner"] == "http://scanner:5112"
        assert urls["signal_engine"] == "http://signal:5113"
        assert urls["market_analyzer"] == "http://analyzer:5114"

    def test_get_celery_config(self):
        """Celery 설정 딕셔너리 반환 확인"""
        settings = AppSettings(
            celery_broker_url="redis://broker:6379/1",
            celery_result_backend="redis://backend:6379/2",
        )
        config = settings.get_celery_config()
        assert config["broker_url"] == "redis://broker:6379/1"
        assert config["result_backend"] == "redis://backend:6379/2"


# =============================================================================
# 싱글톤 패턴 테스트
# =============================================================================
class TestSingleton:
    """싱글톤 패턴 테스트"""

    def test_get_settings_singleton(self):
        """get_settings() 싱글톤 패턴 확인"""
        # 전역 싱글톤 초기화
        from src.config import app_settings

        # 기존 싱글톤 초기화 (다른 테스트의 영향 제거)
        app_settings._settings = None

        settings1 = get_settings()
        settings2 = get_settings()

        # 두 인스턴스가 동일한 객체인지 확인
        assert settings1 is settings2

    def test_get_settings_returns_same_instance(self):
        """get_settings()가 항상 동일한 인스턴스 반환 확인"""
        from src.config import app_settings

        app_settings._settings = None

        settings = get_settings()
        assert isinstance(settings, AppSettings)

        # 여러 호출해도 동일한 인스턴스
        for _ in range(5):
            assert get_settings() is settings

    def test_reload_settings_creates_new_instance(self):
        """reload_settings()가 새 인스턴스 생성 확인"""
        from src.config import app_settings

        app_settings._settings = None

        settings1 = get_settings()
        settings2 = reload_settings()

        # 새 인스턴스이므로 다른 객체여야 함
        assert settings1 is not settings2

        # 하지만 기본값은 동일해야 함
        assert settings1.database_url == settings2.database_url

    def test_reload_with_env_change(self):
        """환경변수 변경 후 reload_settings()로 값 갱신 확인"""
        from src.config import app_settings

        app_settings._settings = None

        # 초기 설정
        settings1 = get_settings()
        original_url = settings1.vcp_scanner_url

        # 환경변수 변경 후 재로드
        with patch.dict(os.environ, {"VCP_SCANNER_URL": "http://new-scanner:9999"}):
            settings2 = reload_settings()
            assert settings2.vcp_scanner_url == "http://new-scanner:9999"
            assert settings2.vcp_scanner_url != original_url


# =============================================================================
# 통합 테스트
# =============================================================================
class TestIntegration:
    """통합 동작 테스트"""

    def test_full_settings_from_env(self):
        """.env 파일로부터 전체 설정 로드 확인"""
        # 실제 환경에서 실행되는 경우, .env 파일의 값이 로드되어야 함
        # 이 테스트는 기본값 검증 위주로 작성
        settings = get_settings()

        # 설정이 정상적으로 로드되었는지 확인
        assert settings is not None
        assert isinstance(settings, AppSettings)

        # 필수 필드가 존재하는지 확인
        assert hasattr(settings, "database_url")
        assert hasattr(settings, "redis_url")
        assert hasattr(settings, "celery_broker_url")
        assert hasattr(settings, "vcp_scanner_url")
        assert hasattr(settings, "signal_engine_url")

    def test_settings_immutability_for_single_instance(self):
        """단일 인스턴스 내에서 값 변경 가능 확인"""
        settings = AppSettings()

        # Pydantic v2는 기본적으로 불변이 아님
        # 따라서 값 직접 수정 가능 (frozen=True가 아님)
        original_url = settings.vcp_scanner_url
        settings.vcp_scanner_url = "http://modified:9999"

        assert settings.vcp_scanner_url == "http://modified:9999"
        assert settings.vcp_scanner_url != original_url

    def test_multiple_independent_instances(self):
        """독립적인 인스턴스 생성 확인"""
        settings1 = AppSettings(vcp_scanner_url="http://instance1:5112")
        settings2 = AppSettings(vcp_scanner_url="http://instance2:5112")

        # 독립적인 인스턴스이므로 서로 다른 값 유지
        assert settings1.vcp_scanner_url == "http://instance1:5112"
        assert settings2.vcp_scanner_url == "http://instance2:5112"
        assert settings1 is not settings2


# =============================================================================
# Case Sensitivity 테스트
# =============================================================================
class TestCaseSensitivity:
    """대소문자 구분 테스트 (case_sensitive=False)"""

    def test_uppercase_env_vars(self):
        """대문자 환경변수로도 로드 가능해야 함"""
        # Pydantic Settings는 기본적으로 case_sensitive=False
        # 따라서 DATABASE_URL, database_url, Database_URL 모두 동일하게 처리
        with patch.dict(os.environ, {"DATABASE_URL": "postgresql://test:123@host/db"}):
            settings = AppSettings()
            assert settings.database_url == "postgresql://test:123@host/db"

    def test_lowercase_env_vars(self):
        """소문자 환경변수로도 로드 가능해야 함"""
        with patch.dict(os.environ, {"database_url": "postgresql://test:456@host/db2"}):
            settings = AppSettings()
            assert settings.database_url == "postgresql://test:456@host/db2"


# =============================================================================
# Extra Fields 테스트
# =============================================================================
class TestExtraFields:
    """추가 필드 처리 테스트 (extra="ignore")"""

    def test_unknown_fields_ignored(self):
        """알 수 없는 필드는 무시되어야 함"""
        # Pydantic Settings의 extra="ignore" 설정으로
        # 정의되지 않은 필드는 무시됨
        # 직접 생성 시에는 ValidationError 발생하지 않음
        settings = AppSettings(
            database_url="postgresql://localhost/test",
            unknown_field="should_be_ignored",
        )

        # 정의된 필드만 존재
        assert hasattr(settings, "database_url")
        assert not hasattr(settings, "unknown_field")
