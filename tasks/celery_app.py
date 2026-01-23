"""
Celery Application Configuration
비동기 작업 처리를 위한 Celery 설정
"""

from celery import Celery
import os

# Redis URL 설정
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Celery 앱 생성
celery_app = Celery(
    "kr_stock_tasks",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=[
        "tasks.scan_tasks",
        "tasks.signal_tasks",
        "tasks.market_tasks",
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
        # VCP 스캔 - 매일 오후 3시 30분
        "scan-vcp-daily": {
            "task": "tasks.scan_tasks.scan_vcp_patterns",
            "schedule": 15 * 60,  # 15분 (테스트용)
            # "schedule": crontab(hour=15, minute=30),
            "args": ("KOSPI", 30),
        },
        # 종가베팅 시그널 - 매일 오후 4시
        "generate-signals-daily": {
            "task": "tasks.signal_tasks.generate_jongga_signals",
            "schedule": 30 * 60,  # 30분 (테스트용)
            # "schedule": crontab(hour=16, minute=0),
            "args": (10_000_000, 30),
        },
        # Market Gate 업데이트 - 매일 오전 9시, 오후 3시
        "update-market-gate": {
            "task": "tasks.market_tasks.update_market_gate",
            "schedule": 60 * 60,  # 1시간 (테스트용)
            # "schedule": crontab(hour="9,15", minute=0),
        },
    },
)


@celery_app.task(name="health.check")
def health_check():
    """헬스 체크 태스크"""
    return {"status": "healthy", "service": "celery"}


if __name__ == "__main__":
    celery_app.start()
