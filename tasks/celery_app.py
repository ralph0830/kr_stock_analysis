"""
Celery Application Configuration
비동기 작업 처리를 위한 Celery 설정
"""

from celery import Celery
# from celery.schedules import crontab  # 운영 시 주석 해제
import os

# Redis URL 설정
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Celery 앱 생성
celery_app = Celery(
    "ralph_stock_tasks",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=[
        "tasks.scan_tasks",
        "tasks.signal_tasks",
        "tasks.market_tasks",
        "tasks.news_tasks",  # 뉴스 태스크 추가
        "tasks.sync_tasks",  # 종목 동기화 태스크 추가
        "tasks.ohlc_tasks",  # OHLC 수집 태스크 추가
        "src.tasks.collection_tasks",  # 일봉/수급 데이터 수집 태스크 추가
    ]
)

# Celery 설정
celery_app.conf.update(
    # 태스크 설정
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Seoul",
    enable_utc=True,

    # 태스크 실행 설정
    task_track_started=True,
    task_time_limit=30 * 60,  # 30분
    task_soft_time_limit=25 * 60,  # 25분
    worker_prefetch_multiplier=4,
    worker_concurrency=4,

    # 결과 설정
    result_expires=3600,  # 1시간
    result_extended=True,

    # 재시도 설정
    task_acks_late=True,
    task_reject_on_worker_lost=True,

    # Beat 스케줄러 설정
    beat_schedule={
        # ============================================================================
        # 일일 정기 작업 (테스트용 - 주석 해제하여 운영 전환)
        # ============================================================================

        # 종목 동기화 - 매일 오전 8시
        # "sync-stock-list-daily": {
        #     "task": "tasks.sync_tasks.sync_stock_list",
        #     "schedule": crontab(hour=8, minute=0),
        #     "args": (["KOSPI", "KOSDAQ"],),
        # },

        # VCP 스캔 - 매일 오후 4시
        # "scan-vcp-daily": {
        #     "task": "tasks.sync_tasks.trigger_vcp_scan_via_api",
        #     "schedule": crontab(hour=16, minute=0),
        # },

        # 테스트용: 1시간 간격
        "sync-stock-list-test": {
            "task": "tasks.sync_tasks.sync_stock_list",
            "schedule": 60 * 60,
            "args": (["KOSPI", "KOSDAQ"],),
        },

        "scan-vcp-test": {
            "task": "tasks.sync_tasks.trigger_vcp_scan_via_api",
            "schedule": 30 * 60,
        },

        # ============================================================================
        # 기존 스케줄
        # ============================================================================

        # 종가베팅 시그널 - 매일 오후 4시 30분
        "generate-signals-daily": {
            "task": "tasks.signal_tasks.generate_jongga_signals",
            "schedule": 30 * 60,  # 테스트용: 30분 간격
            # "schedule": crontab(hour=16, minute=30),  # 운영: 매일 16:30
            "args": (10_000_000, 30),
        },

        # Market Gate 업데이트 - 5분 간격 실시간 업데이트
        "update-market-gate": {
            "task": "tasks.market_tasks.update_market_gate",
            "schedule": 5 * 60,  # 5분 간격 (실시간 WebSocket 브로드캐스트)
            # "schedule": crontab(hour="9,15", minute=0),  # 운영: 매일 09:00, 15:00
        },

        # ============================================================================
        # 뉴스 수집 스케줄
        # ============================================================================

        # KOSPI 뉴스 수집
        "news-collection-kospi": {
            "task": "tasks.news_tasks.scheduled_daily_collection",
            "schedule": 60 * 60,  # 테스트용: 1시간 간격
            # "schedule": crontab(hour="9,15", minute=0),  # 운영: 매일 09:00, 15:00
            "args": ("KOSPI", 7, 30),
        },

        # KOSDAQ 뉴스 수집
        "news-collection-kosdaq": {
            "task": "tasks.news_tasks.scheduled_daily_collection",
            "schedule": 60 * 60,  # 테스트용: 1시간 간격
            # "schedule": crontab(hour=14, minute=0),  # 운영: 매일 14:00
            "args": ("KOSDAQ", 7, 30),
        },

        # ============================================================================
        # 일별 시세 수집 스케줄
        # ============================================================================

        # 전 종목 일별 시세 수집 - 매일 오후 4시 (장 마감 후)
        "collect-daily-prices-daily": {
            "task": "tasks.sync_all_data",  # src.tasks.collection_tasks에서 @shared_task로 등록됨
            "schedule": 60 * 60,  # 테스트용: 1시간 간격
            # "schedule": crontab(hour=16, minute=0),  # 운영: 매일 16:00
        },

        # ============================================================================
        # OHLC 실시간 수집 스케줄
        # ============================================================================

        # 장 시작 OHLC 수집 (테스트용: 30분마다 상태 확인)
        "ohlc-status-check": {
            "task": "ohlc.get_status",  # @shared_task(name="ohlc.get_status")
            "schedule": 30 * 60,  # 30분 간격
        },

        # OHLC 스냅샷 저장 (1분 간격)
        "ohlc-save-snapshot": {
            "task": "ohlc.save_snapshot",  # @shared_task(name="ohlc.save_snapshot")
            "schedule": 1 * 60,  # 1분 간격
        },
    },
)


@celery_app.task(name="health.check")
def health_check():
    """헬스 체크 태스크"""
    return {"status": "healthy", "service": "celery"}


if __name__ == "__main__":
    celery_app.start()
