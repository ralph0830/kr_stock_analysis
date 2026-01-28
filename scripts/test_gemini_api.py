"""
Gemini API 연결 테스트 스크립트

사용법:
    python scripts/test_gemini_api.py

환경 변수:
    GEMINI_API_KEY: Gemini API 키
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


def test_gemini_api():
    """Gemini API 연결 테스트"""

    # API 키 확인
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or api_key == "your_gemini_api_key_here":
        logger.error("❌ GEMINI_API_KEY가 설정되지 않았습니다.")
        logger.info("📝 .env 파일에 GEMINI_API_KEY를 설정해주세요.")
        logger.info("   API 키 발급: https://aistudio.google.com/app/apikey")
        return False

    # 패키지 설치 확인
    try:
        import google.generativeai as genai
    except ImportError:
        logger.error("❌ google-generativeai 패키지가 설치되지 않았습니다.")
        logger.info("📦 설치 명령: uv add google-generativeai")
        return False

    try:
        # API 설정
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-pro")
        logger.info("✅ Gemini API 초기화 성공")

        # 간단한 테스트 요청
        test_prompt = """
        다음 뉴스 기사를 분석해주세요.

        **뉴스 제목:** 삼성전자, 4분기 실적 호조
        **뉴스 내용:** 삼성전자가 4분기 매출 80조원, 영업이익 10조원을 달성하며 시장 기대치를 상회했습니다.

        **분석 요청:**
        1. 감성 분류 (긍정/부정/중립)
        2. 신뢰도 (0~1 사이 값)
        3. 핵심 키워드 (3~5개)
        4. 1문장 요약

        **출력 형식 (JSON):**
        {
            "sentiment": "positive|negative|neutral",
            "confidence": 0.8,
            "keywords": ["키워드1", "키워드2", "키워드3"],
            "summary": "뉴스 요약 1문장"
        }
        """

        logger.info("🔄 테스트 요청 전송 중...")
        response = model.generate_content(test_prompt)
        result_text = response.text

        logger.info("✅ API 응답 수신 성공")
        logger.info(f"📄 응답 내용:\n{result_text}")

        # JSON 파싱 테스트
        import json

        # 마크다운 코드 블록 제거
        if "```json" in result_text:
            result_text = result_text.split("```json")[1].split("```")[0].strip()
        elif "```" in result_text:
            result_text = result_text.split("```")[1].split("```")[0].strip()

        result = json.loads(result_text)
        logger.info("✅ JSON 파싱 성공")
        logger.info("📊 분석 결과:")
        logger.info(f"   - 감성: {result.get('sentiment')}")
        logger.info(f"   - 신뢰도: {result.get('confidence')}")
        logger.info(f"   - 키워드: {result.get('keywords')}")
        logger.info(f"   - 요약: {result.get('summary')}")

        return True

    except Exception as e:
        logger.error(f"❌ Gemini API 테스트 실패: {e}")
        logger.info("🔍 확인 사항:")
        logger.info("   1. API 키가 올바른지 확인")
        logger.info("   2. 인터넷 연결 상태 확인")
        logger.info("   3. API 할당량 확인 (Free Tier: 분당 15 요청)")
        return False


def test_sentiment_analyzer():
    """SentimentAnalyzer 모듈 테스트"""
    logger.info("\n" + "=" * 60)
    logger.info("📊 SentimentAnalyzer 모듈 테스트")
    logger.info("=" * 60)

    try:
        from src.analysis.sentiment_analyzer import SentimentAnalyzer

        analyzer = SentimentAnalyzer()
        logger.info("✅ SentimentAnalyzer 초기화 성공")

        # 테스트 뉴스
        test_articles = [
            {
                "title": "삼성전자, 4분기 실적 시장 기대치 상회",
                "content": "삼성전자가 4분기 매출 80조원, 영업이익 10조원을 달성하며 시장 기대치를 상회했습니다."
            },
            {
                "title": "SK하이닉스, HBM 생산 확대",
                "content": "SK하이닉스가 AI 수요 증가에 따라 HBM 생산을 2배로 확대한다고 발표했습니다."
            }
        ]

        logger.info("🔄 감성 분석 시작...")
        results = analyzer.analyze_batch(test_articles)

        for i, result in enumerate(results, 1):
            logger.info(f"\n📰 기사 {i}:")
            logger.info(f"   - 감성: {result.sentiment.value}")
            logger.info(f"   - 신뢰도: {result.confidence:.2f}")
            logger.info(f"   - 감성 점수: {result.score:.2f}")
            logger.info(f"   - 키워드: {result.keywords}")
            logger.info(f"   - 요약: {result.summary}")

        logger.info("\n✅ 모든 테스트 통과!")
        return True

    except Exception as e:
        logger.error(f"❌ SentimentAnalyzer 테스트 실패: {e}")
        return False


def main():
    """메인 함수"""
    logger.info("🚀 Gemini API 테스트 시작")
    logger.info("=" * 60)

    # API 연결 테스트
    api_success = test_gemini_api()

    if not api_success:
        logger.error("\n❌ API 연결 테스트 실패로 종료합니다.")
        sys.exit(1)

    # SentimentAnalyzer 모듈 테스트
    module_success = test_sentiment_analyzer()

    if not module_success:
        logger.error("\n⚠️  모듈 테스트 실패 (API 연결은 성공)")
        sys.exit(1)

    logger.info("\n" + "=" * 60)
    logger.info("🎉 모든 테스트 통과!")
    logger.info("=" * 60)
    logger.info("📋 다음 단계:")
    logger.info("   1. 뉴스 수집기 구현 (Task 2)")
    logger.info("   2. 감성 분석 파이프라인 구축 (Task 3)")


if __name__ == "__main__":
    main()
