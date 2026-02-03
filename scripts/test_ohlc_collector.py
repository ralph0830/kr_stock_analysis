#!/usr/bin/env python
"""
OHLC 수집기 테스트 스크립트

실시간 체결 데이터를 수집하여 OHLC로 집계합니다.

사용법:
    python scripts/test_ohlc_collector.py              # 기본 5종목 60초 수집
    python scripts/test_ohlc_collector.py --duration 300  # 5분 수집
    python scripts/test_ohlc_collector.py --tickers 005930 000660  # 종목 지정
"""

import asyncio
import argparse
import logging
from datetime import datetime, timezone

from src.kiwoom.ohlc_collector import OHLCCollector, collect_ohlc_for_tickers
from src.utils.logging_config import setup_logging

# 기본 수집 종목 (대표적 종목)
DEFAULT_TICKERS = [
    "005930",  # 삼성전자
    "000660",  # SK하이닉스
    "035420",  # NAVER
    "051910",  # LG화학
    "068270",  # 셀트리온
]

logger = logging.getLogger(__name__)


async def test_ohlc_collector(tickers: list[str], duration: int, save_interval: int = 60):
    """
    OHLC 수집기 테스트

    Args:
        tickers: 수집할 종목 리스트
        duration: 수집 시간 (초)
        save_interval: DB 저장 간격 (초)
    """
    from src.kiwoom.base import KiwoomConfig
    from src.kiwoom.ohlc_collector import OHLCCollectorConfig

    logger.info(f"=== OHLC 수집기 테스트 시작 ===")
    logger.info(f"종목: {tickers}")
    logger.info(f"수집 시간: {duration}초")
    logger.info(f"저장 간격: {save_interval}초")

    # 설정 생성
    config = KiwoomConfig.from_env()
    collector_config = OHLCCollectorConfig(
        tickers=tickers,
        save_interval=save_interval,
    )

    # 수집기 생성
    collector = OHLCCollector(config, collector_config)

    # 체결 데이터 콜백 등록 (디버깅용)
    def on_trade(price_data):
        from src.kiwoom.base import RealtimePrice
        if isinstance(price_data, RealtimePrice):
            logger.info(
                f"📊 체결: [{price_data.ticker}] {price_data.price:,}원 "
                f"({price_data.change:+,}원, {price_data.change_rate:+.2f}%) "
                f"V:{price_data.volume:,}"
            )

    collector.add_trade_callback(on_trade)

    try:
        # 수집 시작
        if not await collector.start():
            logger.error("수집기 시작 실패")
            return

        logger.info("✅ 수집기 시작 완료")

        # 지정된 시간 동안 수집
        start_time = datetime.now(timezone.utc)
        last_print = start_time

        while collector.is_running():
            await asyncio.sleep(1)

            # 현재 상태 출력 (10초마다)
            now = datetime.now(timezone.utc)
            if (now - last_print).total_seconds() >= 10:
                elapsed = int((now - start_time).total_seconds())
                ohlc_bars = collector.get_all_ohlc()

                logger.info(f"⏱️  경과: {elapsed}초 | 수집 중: {len(ohlc_bars)}종목")

                for ticker, bar in ohlc_bars.items():
                    logger.info(
                        f"  [{ticker}] O:{bar.open_price:,} "
                        f"H:{bar.high_price:,} L:{bar.low_price:,} "
                        f"C:{bar.close_price:,} V:{bar.volume:,} "
                        f"({bar.trade_count}건)"
                    )

                last_print = now

            # 최대 시간 확인
            elapsed = (now - start_time).total_seconds()
            if elapsed >= duration:
                logger.info(f"⏰ 최대 수집 시간 ({duration}초) 도달")
                break

        # 최종 결과 출력
        final_bars = collector.get_all_ohlc()
        logger.info(f"=== 최종 수집 결과 ({len(final_bars)}종목) ===")

        for ticker, bar in final_bars.items():
            logger.info(
                f"[{ticker}] O:{bar.open_price:,} H:{bar.high_price:,} "
                f"L:{bar.low_price:,} C:{bar.close_price:,} V:{bar.volume:,} "
                f"({bar.trade_count}건)"
            )

    finally:
        # 수집기 중지 (최종 저장 포함)
        await collector.stop()
        logger.info("=== OHLC 수집기 테스트 종료 ===")


async def test_simple_collect(tickers: list[str], duration: int):
    """
    간단한 수집 테스트 (collect_ohlc_for_tickers 함수 사용)

    Args:
        tickers: 수집할 종목 리스트
        duration: 수집 시간 (초)
    """
    logger.info(f"=== 간단 수집 테스트 ===")
    logger.info(f"종목: {tickers}, 시간: {duration}초")

    ohlc_data = await collect_ohlc_for_tickers(tickers, duration)

    logger.info(f"=== 수집 완료 ({len(ohlc_data)}종목) ===")

    for ticker, bar in ohlc_data.items():
        logger.info(
            f"[{ticker}] O:{bar.open_price:,} H:{bar.high_price:,} "
            f"L:{bar.low_price:,} C:{bar.close_price:,} V:{bar.volume:,}"
        )


def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(description="OHLC 수집기 테스트")
    parser.add_argument(
        "--tickers",
        nargs="+",
        default=DEFAULT_TICKERS,
        help="수집할 종목 코드 (예: 005930 000660)",
    )
    parser.add_argument(
        "--duration",
        type=int,
        default=60,
        help="수집 시간 (초, 기본 60)",
    )
    parser.add_argument(
        "--save-interval",
        type=int,
        default=60,
        help="DB 저장 간격 (초, 기본 60)",
    )
    parser.add_argument(
        "--simple",
        action="store_true",
        help="간단 모드 (콜백 없이 수집만)",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="디버그 모드 (상세 로그)",
    )

    args = parser.parse_args()

    # 로깅 설정
    log_level = logging.DEBUG if args.debug else logging.INFO
    setup_logging(level=log_level)

    # 비동기 실행
    if args.simple:
        asyncio.run(test_simple_collect(args.tickers, args.duration))
    else:
        asyncio.run(test_ohlc_collector(args.tickers, args.duration, args.save_interval))


if __name__ == "__main__":
    main()
