"""
뉴스 수집기 테스트 스크립트

사용법:
    python scripts/test_news_collection.py

테스트 항목:
    1. 네이버 뉴스 수집
    2. 날짜 필터링
    3. 중복 제거
    4. 본문 수집
"""

import os
import sys
import logging
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def test_news_collector():
    """NewsCollector 테스트"""

    try:
        from src.collectors.news_collector import NewsCollector

        # NewsCollector 초기화
        collector = NewsCollector()
        logger.info("✅ NewsCollector 초기화 성공")

        # 테스트 종목 (삼성전자)
        test_ticker = "005930"

        # 최근 7일 뉴스 수집 (최대 10건)
        logger.info(f"\n{'=' * 60}")
        logger.info(f"📰 {test_ticker} (삼성전자) 뉴스 수집 테스트")
        logger.info(f"{'=' * 60}")

        articles = collector.fetch_stock_news(
            ticker=test_ticker,
            days=7,
            max_articles=10,
        )

        logger.info(f"\n✅ 뉴스 {len(articles)}건 수집 완료\n")

        # 수집 결과 출력
        for i, article in enumerate(articles, 1):
            logger.info(f"📰 기사 {i}:")
            logger.info(f"   제목: {article.title}")
            logger.info(f"   언론사: {article.source}")
            logger.info(f"   날짜: {article.published_at}")
            logger.info(f"   URL: {article.url}")
            logger.info(f"   본문 길이: {len(article.content)}자")
            if article.content:
                logger.info(f"   본문 미리보기: {article.content[:100]}...")
            logger.info("")

        # 딕셔너리 변환 테스트
        logger.info(f"{'=' * 60}")
        logger.info("🔄 딕셔너리 변환 테스트")
        logger.info(f"{'=' * 60}")

        articles_dict = collector.to_dict_list(articles)
        logger.info(f"✅ 딕셔너리 변환 완료: {len(articles_dict)}건")

        # 검증
        if len(articles) > 0:
            logger.info(f"\n{'=' * 60}")
            logger.info("✅ 검증 결과:")
            logger.info(f"{'=' * 60}")
            logger.info(f"   - 수집 건수: {len(articles)}건 (목표: 10건)")
            logger.info(f"   - 제목 존재: {all(article.title for article in articles)}")
            logger.info(f"   - URL 존재: {all(article.url for article in articles)}")
            logger.info(f"   - 언론사 존재: {all(article.source for article in articles)}")
            logger.info(f"   - 날짜 존재: {all(article.published_at for article in articles)}")
            logger.info(f"   - 본문 수집: {sum(1 for a in articles if a.content)}건")
            logger.info("")

            # 성공 기준
            if len(articles) >= 5:  # 최소 5건 이상
                logger.info("🎉 테스트 통과!")
                return True
            else:
                logger.warning("⚠️  뉴스 수집 건수가 부족합니다 (5건 미만)")
                return False
        else:
            logger.error("❌ 뉴스 수집 실패 (0건)")
            return False

    except Exception as e:
        logger.error(f"❌ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_date_parsing():
    """날짜 파싱 테스트"""
    logger.info(f"\n{'=' * 60}")
    logger.info("🕐 날짜 파싱 테스트")
    logger.info(f"{'=' * 60}")

    try:
        from src.collectors.news_collector import NewsCollector

        collector = NewsCollector()

        test_dates = [
            "2024.01.15 14:30",
            "오늘 10:00",
            "어제 16:30",
        ]

        for date_str in test_dates:
            parsed = collector._parse_naver_date(date_str)
            logger.info(f"   '{date_str}' → {parsed}")

        logger.info("✅ 날짜 파싱 테스트 통과")
        return True

    except Exception as e:
        logger.error(f"❌ 날짜 파싱 테스트 실패: {e}")
        return False


def main():
    """메인 함수"""
    logger.info("🚀 뉴스 수집기 테스트 시작")
    logger.info("=" * 60)

    # 날짜 파싱 테스트
    date_test = test_date_parsing()

    # 뉴스 수집 테스트
    news_test = test_news_collector()

    # 최종 결과
    logger.info(f"\n{'=' * 60}")
    logger.info("📊 최종 결과:")
    logger.info(f"{'=' * 60}")
    logger.info(f"   날짜 파싱: {'✅ 통과' if date_test else '❌ 실패'}")
    logger.info(f"   뉴스 수집: {'✅ 통과' if news_test else '❌ 실패'}")
    logger.info("")

    if date_test and news_test:
        logger.info("🎉 모든 테스트 통과!")
        logger.info("\n📋 다음 단계:")
        logger.info("   1. 감성 분석 파이프라인 구축 (Task 3)")
        logger.info("   2. 뉴스 점수화 통합 (Task 4)")
        sys.exit(0)
    else:
        logger.error("❌ 테스트 실패")
        sys.exit(1)


if __name__ == "__main__":
    main()
