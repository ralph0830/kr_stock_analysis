#!/usr/bin/env python
"""
키움 REST API 테스트 스크립트

1. 토큰 발급 테스트
2. 현재가 조회 테스트
3. 차트 데이터 조회 테스트
4. 일별 가격 데이터 수집 테스트
"""

import asyncio
import os
import sys
from datetime import datetime

# 프로젝트 루트 경로 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.kiwoom.base import KiwoomConfig
from src.kiwoom.rest_api import KiwoomAPIError


async def test_token_issuance():
    """토큰 발급 테스트"""
    print("=" * 60)
    print("1. 토큰 발급 테스트")
    print("=" * 60)

    try:
        config = KiwoomConfig.from_env()
        print("✅ 설정 로드 성공")
        print(f"   - Base URL: {config.base_url}")
        print(f"   - App Key: {config.app_key[:20]}...{config.app_key[-10:]}")
        print(f"   - Use Mock: {config.use_mock}")

        from src.kiwoom.rest_api import KiwoomRestAPI
        api = KiwoomRestAPI(config)

        # 토큰 발급
        print("\n토큰 발급 요청 중...")
        result = await api.issue_token()

        if result:
            print("✅ 토큰 발급 성공!")
            print(f"   - Access Token: {api._access_token[:30]}...")
            print(f"   - 만료 시간: {datetime.fromtimestamp(api._token_expires_at)}")
            print(f"   - 유효성: {api.is_token_valid()}")
            return api
        else:
            print("❌ 토큰 발급 실패")
            return None

    except KiwoomAPIError as e:
        print(f"❌ KiwoomAPIError: {e.message}")
        return None
    except Exception as e:
        print(f"❌ 오류: {e}")
        import traceback
        traceback.print_exc()
        return None


async def test_current_price(api):
    """현재가 조회 테스트"""
    print("\n" + "=" * 60)
    print("2. 현재가 조회 테스트 (삼성전자 005930)")
    print("=" * 60)

    try:
        price = await api.get_current_price("005930")

        if price:
            print("✅ 현재가 조회 성공!")
            print(f"   - 티커: {price.ticker}")
            print(f"   - 가격: {price.price:,}원")
            print(f"   - 전일비: {price.change:,}원")
            print(f"   - 등락률: {price.change_rate:.2f}%")
            print(f"   - 거래량: {price.volume:,}주")
            print(f"   - 매수호가: {price.bid_price:,}원")
            print(f"   - 매도호가: {price.ask_price:,}원")
        else:
            print("❌ 현재가 조회 실패")

    except Exception as e:
        print(f"❌ 오류: {e}")
        import traceback
        traceback.print_exc()


async def test_investor_chart(api):
    """투자자별 차트 데이터 조회 테스트"""
    print("\n" + "=" * 60)
    print("3. 투자자별 차트 데이터 조회 테스트")
    print("=" * 60)

    try:
        # 오늘 날짜
        today = datetime.now().strftime("%Y%m%d")
        print(f"조회 일자: {today}")

        chart_data = await api.get_investor_chart(
            ticker="005930",
            date=today,
        )

        if chart_data and chart_data.get("data"):
            data_list = chart_data["data"]
            print("✅ 차트 데이터 조회 성공!")
            print(f"   - 데이터 개수: {len(data_list)}")

            # 첫 번째 데이터 출력
            if data_list:
                first = data_list[0]
                print("\n첫 번째 데이터:")
                print(f"   - 일자: {first.get('dt')}")
                print(f"   - 현재가: {first.get('cur_prc')}")
                print(f"   - 거래량: {first.get('acc_trde_prica')}")
                print(f"   - 개인: {first.get('ind_invsr')}")
                print(f"   - 외국인: {first.get('frgnr_invsr')}")
                print(f"   - 기관: {first.get('orgn')}")
        else:
            print("❌ 차트 데이터 조회 실패 또는 데이터 없음")

    except Exception as e:
        print(f"❌ 오류: {e}")
        import traceback
        traceback.print_exc()


async def test_daily_prices(api):
    """일별 가격 데이터 수집 테스트"""
    print("\n" + "=" * 60)
    print("4. 일별 가격 데이터 수집 테스트 (최근 5일)")
    print("=" * 60)

    try:
        prices = await api.get_daily_prices(
            ticker="005930",
            days=5,
        )

        if prices:
            print("✅ 일별 가격 데이터 수집 성공!")
            print(f"   - 데이터 개수: {len(prices)}")

            print("\n수집된 데이터:")
            for p in prices:
                print(f"   - {p['date']}: {p['price']:,}원 "
                      f"(거래량: {p['volume']:,}, "
                      f"외국인: {p['foreign']:,}, "
                      f"기관: {p['institution']:,})")
        else:
            print("❌ 일별 가격 데이터 수집 실패")

    except Exception as e:
        print(f"❌ 오류: {e}")
        import traceback
        traceback.print_exc()


async def main():
    """메인 함수"""
    print("🔑 키움 REST API 테스트 시작")
    print(f"현재 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # 토큰 발급
    api = await test_token_issuance()

    if not api or not api.is_token_valid():
        print("\n⚠️ 토큰 발급 실패로 테스트를 중단합니다.")
        return

    # 현재가 조회
    await test_current_price(api)

    # 차트 데이터 조회
    await test_investor_chart(api)

    # 일별 가격 데이터 수집
    await test_daily_prices(api)

    # 연결 종료
    await api.close()

    print("\n" + "=" * 60)
    print("✅ 테스트 완료")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
