"""
News Sentiment Analysis Test Script
뉴스 감성 분석 테스트
"""

import sys
from pathlib import Path
from datetime import date

# 상위 디렉토리 경로 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.analysis.sentiment_analyzer import SentimentAnalyzer, Sentiment
from src.analysis.news_scorer import NewsScorer


def test_sentiment_analyzer():
    """감성 분석 테스트"""
    print("=" * 60)
    print("🤖 테스트 1: 뉴스 감성 분석")
    print("=" * 60)

    analyzer = SentimentAnalyzer()

    # 테스트 뉴스 데이터
    test_articles = [
        {
            "title": "삼성전자, 4분기 실적 시장 예상 상회",
            "content": "삼성전자가 4분기 매출과 영업이익이 시장 예상을 상회할 것으로 전망되었다. 반도체 불황에도 불구하고 HBM 수요가 견조했다.",
        },
        {
            "title": "SK하이닉스, NAND 플래시 가격 하락으로 실적 부진",
            "content": "SK하이닉스의 4분기 영업이익이 시장 예상에 못 미쳤다. NAND 플래시 가격 지속 하락이 영향을 미쳤다.",
        },
        {
            "title": "NAVER, 2분기 매출 전년 동기 대비 10% 증가",
            "content": "NAVER가 2분기 매출이 전년 동기 대비 10% 증가했다. 커머스와 핀테크 부문이 견조한 성장을 보였다.",
        },
    ]

    print("\n뉴스 감성 분석 결과:\n")

    for i, article in enumerate(test_articles, 1):
        result = analyzer.analyze(article["title"], article["content"])

        sentiment_label = {
            Sentiment.POSITIVE: "🟢 긍정",
            Sentiment.NEGATIVE: "🔴 부정",
            Sentiment.NEUTRAL: "⚪ 중립",
        }[result.sentiment]

        print(f"[{i}] {article['title']}")
        print(f"    감성: {sentiment_label} (신뢰도: {result.confidence:.2f}, 점수: {result.score:.2f})")
        print(f"    키워드: {', '.join(result.keywords)}")
        print(f"    요약: {result.summary}")
        print()

    return True


def test_news_scorer():
    """뉴스 점수화 테스트"""
    print("=" * 60)
    print("📊 테스트 2: 일일 뉴스 점수 계산")
    print("=" * 60)

    scorer = NewsScorer()

    # 테스트 뉴스 (긍정 3개, 부정 1개, 중립 1개)
    test_articles = [
        {
            "title": "삼성전자, HBM3e 양산 시작... AI 반도체 시장 선점",
            "content": "삼성전자가 HBM3e 양산을 시작하며 AI 반도체 시장에서 SK하이닉스와 경쟁에 나선다.",
            "source": "Reuters",
        },
        {
            "title": "삼성전자, 2분기 영업이익 10조원 돌파... 시장 예상 상회",
            "content": "삼성전자가 2분기 영업이익이 10조원을 넘어설 것으로 전망된다. 반도체 부문 실적 호조가 주도했다.",
            "source": "Bloomberg",
        },
        {
            "title": "삼성전자, 신사업 투자 확대... 미래 성장 동력 확보",
            "content": "삼성전자가 바이오, 자동차 반도체 등 신사업 분야에 투자를 확대한다.",
            "source": "Korea Economic Daily",
        },
        {
            "title": "삼성전자, 파업으로 생산 차질 우려",
            "content": "삼성전자 노조가 파업을 진행하면서 반도체 생산 라인에 차질이 우려된다.",
            "source": "Yonhap News",
        },
        {
            "title": "삼성전자, 주주 환원 정책 발표",
            "content": "삼성전자가 주주 환원율을 높이기 위한 정책을 발표했다.",
            "source": "MoneyToday",
        },
    ]

    target_date = date.today()
    result = scorer.calculate_daily_score("005930", test_articles, target_date)

    print(f"\n📅 날짜: {result.date}")
    print(f"📈 총점: {result.total_score:.1f}점 / 3.0점")
    print(f"  🟢 긍정: {result.positive_count}개")
    print(f"  🔴 부정: {result.negative_count}개")
    print(f"  ⚪ 중립: {result.neutral_count}개")

    print("\n상세 결과:")
    for i, detail in enumerate(result.details, 1):
        sentiment_emoji = {
            "positive": "🟢",
            "negative": "🔴",
            "neutral": "⚪",
        }[detail["sentiment"]]

        print(f"  [{i}] {detail['title']}")
        print(f"      {sentiment_emoji} {detail['sentiment']} (신뢰도: {detail['confidence']:.2f})")
        print(f"      키워드: {', '.join(detail['keywords'])}")
        print()

    # 긍정 뉴스 3개 이상이면 3점
    if result.total_score >= 3.0:
        print("✅ 종가베팅 S급 뉴스 점수!")
        return True
    elif result.total_score >= 2.0:
        print("✅ 종가베팅 A급 뉴스 점수!")
        return True
    else:
        print("⚠️  낮은 뉴스 점수")
        return False


def test_keyword_extraction():
    """키워드 추출 테스트"""
    print("=" * 60)
    print("🔑 테스트 3: 뉴스 키워드 추출")
    print("=" * 60)

    scorer = NewsScorer()

    test_articles = [
        {
            "title": "삼성전자, HBM3e 양산 시작",
            "content": "삼성전자가 HBM3e 양산을 시작한다.",
        },
        {
            "title": "SK하이닉스, HBM3e 개발 성공",
            "content": "SK하이닉스가 HBM3e 개발에 성공했다.",
        },
        {
            "title": "삼성전자, AI 반도체 시장 공략",
            "content": "삼성전자가 AI 반도체 시장을 공략한다.",
        },
    ]

    keywords = scorer.extract_keywords(test_articles)

    print(f"\n추출된 키워드 (상위 10개):")
    for i, keyword in enumerate(keywords, 1):
        print(f"  {i}. {keyword}")

    return len(keywords) > 0


def main():
    """메인 테스트 실행"""
    print("\n🚀 뉴스 감성 분석 테스트 시작\n")

    results = {
        "감성 분석": test_sentiment_analyzer(),
        "뉴스 점수화": test_news_scorer(),
        "키워드 추출": test_keyword_extraction(),
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
