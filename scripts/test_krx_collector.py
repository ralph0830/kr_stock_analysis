"""
KRX Collector Test Script
데이터 수집기 테스트
"""

import sys
from pathlib import Path
from datetime import date, timedelta

# 상위 디렉토리 경로 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.collectors.krx_collector import KRXCollector
from src.database.session import SessionLocal, text


def test_stock_list():
    """종목 목록 수집 테스트"""
    print("=" * 60)
    print("📋 테스트 1: 종목 목록 수집")
    print("=" * 60)

    collector = KRXCollector()
    stocks = collector.fetch_stock_list("KOSPI")

    print(f"\n✅ 수집된 종목 수: {len(stocks)}개")
    print("\n상위 5개 종목:")
    for stock in stocks[:5]:
        print(
            f"  {stock['ticker']} | {stock['name']} | {stock['market']} | {stock['sector']}"
        )

    return len(stocks) > 0


def test_daily_prices():
    """일별 시세 수집 테스트"""
    print("\n" + "=" * 60)
    print("📊 테스트 2: 일별 시세 수집")
    print("=" * 60)

    collector = KRXCollector()
    end_date = date.today()
    start_date = end_date - timedelta(days=5)

    df = collector.fetch_daily_prices("005930", start_date, end_date)

    print(f"\n✅ 수집된 일봉 데이터: {len(df)}개")
    if not df.empty:
        print("\n최근 3일 시세:")
        print(df.tail(3).to_string())
        return True
    else:
        print("⚠️  데이터가 없습니다")
        return False


def test_supply_demand():
    """수급 데이터 수집 테스트"""
    print("\n" + "=" * 60)
    print("💰 테스트 3: 외국인/기관 수급 데이터 수집")
    print("=" * 60)

    collector = KRXCollector()
    end_date = date.today()
    start_date = end_date - timedelta(days=5)

    df = collector.fetch_supply_demand("005930", start_date, end_date)

    print(f"\n✅ 수집된 수급 데이터: {len(df)}개")
    if not df.empty:
        print("\n최근 3일 수급:")
        print(df.tail(3).to_string())
        return True
    else:
        print("⚠️  데이터가 없습니다")
        return False


def verify_database():
    """데이터베이스 저장 확인"""
    print("\n" + "=" * 60)
    print("🗄️  테스트 4: 데이터베이스 확인")
    print("=" * 60)

    with SessionLocal() as session:
        # 종목 수 확인
        stock_count = session.execute(text("SELECT COUNT(*) FROM stocks")).scalar()
        print(f"\n📋 저장된 종목 수: {stock_count}개")

        # 일봉 수 확인
        price_count = session.execute(
            text("SELECT COUNT(*) FROM daily_prices")
        ).scalar()
        print(f"📊 저장된 일봉 수: {price_count}개")

        # 최신 데이터 확인
        latest = session.execute(
            text("""
                SELECT ticker, date, close_price
                FROM daily_prices
                ORDER BY date DESC
                LIMIT 3
            """)
        ).fetchall()

        if latest:
            print("\n최신 데이터:")
            for row in latest:
                print(f"  {row[0]} | {row[1]} | ₩{row[2]:,.0f}")

        return stock_count > 0 and price_count > 0


def main():
    """메인 테스트 실행"""
    print("\n🚀 KRX Collector 테스트 시작\n")

    results = {
        "종목 목록 수집": test_stock_list(),
        "일별 시세 수집": test_daily_prices(),
        "수급 데이터 수집": test_supply_demand(),
        "데이터베이스 확인": verify_database(),
    }

    print("\n" + "=" * 60)
    print("📊 테스트 결과 요약")
    print("=" * 60)

    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {test_name}")

    total = len(results)
    passed = sum(results.values())
    print(f"\n총계: {passed}/{total} 테스트 통과")

    if passed == total:
        print("\n🎉 모든 테스트 통과!")
    else:
        print(f"\n⚠️  {total - passed}개 테스트 실패")


if __name__ == "__main__":
    main()
