"""
Signal Scorer - 종가베팅 V2 점수 계산
12점 만점 시스템
"""

from dataclasses import dataclass
from typing import List, Optional, TYPE_CHECKING
from enum import Enum
import logging

if TYPE_CHECKING:
    from src.repositories.daily_price_repository import DailyPriceRepository
    from src.analysis.vcp_analyzer import VCPAnalyzer

logger = logging.getLogger(__name__)


class Grade(Enum):
    """등급"""
    S = "S"  # 10점 이상
    A = "A"  # 8점 이상
    B = "B"  # 6점 이상
    C = "C"  # 6점 미만


@dataclass
class ScoreDetail:
    """점수 상세"""
    total: int  # 총점 (0-12)
    news: int = 0  # 뉴스 (0-3)
    volume: int = 0  # 거래대금 (0-3)
    chart: int = 0  # 차트패턴 (0-2)
    candle: int = 0  # 캔들 (0-1)
    period: int = 0  # 기간조정 (0-1)
    flow: int = 0  # 수급 (0-2)

    def to_dict(self):
        return {
            "total": self.total,
            "news": self.news,
            "volume": self.volume,
            "chart": self.chart,
            "candle": self.candle,
            "period": self.period,
            "flow": self.flow,
        }


@dataclass
class JonggaSignal:
    """종가베팅 시그널"""
    ticker: str
    name: str
    score: ScoreDetail
    grade: Grade
    position_size: int  # 주식 수
    entry_price: int  # 진입 가격
    target_price: int  # 목표가
    stop_loss: int  # 손절가
    reasons: List[str]  # 매매 사유
    created_at: str

    def to_dict(self):
        return {
            "ticker": self.ticker,
            "name": self.name,
            "score": self.score.to_dict(),
            "grade": self.grade.value,
            "position_size": self.position_size,
            "entry_price": self.entry_price,
            "target_price": self.target_price,
            "stop_loss": self.stop_loss,
            "reasons": self.reasons,
            "created_at": self.created_at,
        }


class SignalScorer:
    """
    종가베팅 점수 계산기

    Args:
        daily_price_repo: DailyPriceRepository 인스턴스 (선택사항)
        vcp_analyzer: VCPAnalyzer 인스턴스 (선택사항)
    """

    def __init__(
        self,
        daily_price_repo: Optional["DailyPriceRepository"] = None,
        vcp_analyzer: Optional["VCPAnalyzer"] = None,
    ):
        self.logger = logger
        self._daily_price_repo = daily_price_repo
        self._vcp_analyzer = vcp_analyzer

    def _get_daily_price_repo(self) -> Optional["DailyPriceRepository"]:
        """DailyPriceRepository lazy loading"""
        if self._daily_price_repo is None:
            try:
                from src.repositories.daily_price_repository import DailyPriceRepository
                from src.database.session import SessionLocal
                self._daily_price_repo = DailyPriceRepository(SessionLocal())
            except ImportError:
                logger.warning("DailyPriceRepository import 실패")
                return None
        return self._daily_price_repo

    def _get_vcp_analyzer(self) -> Optional["VCPAnalyzer"]:
        """VCPAnalyzer lazy loading"""
        if self._vcp_analyzer is None:
            try:
                from src.analysis.vcp_analyzer import VCPAnalyzer
                self._vcp_analyzer = VCPAnalyzer()
            except ImportError:
                logger.warning("VCPAnalyzer import 실패")
                return None
        return self._vcp_analyzer

    def calculate(self, ticker: str, name: str, price: int) -> Optional[JonggaSignal]:
        """
        시그널 점수 계산

        Args:
            ticker: 종목코드
            name: 종목명
            price: 현재가

        Returns:
            JonggaSignal 또는 None
        """
        try:
            # 각 항목 점수 계산
            news_score = self._calculate_news_score(ticker)
            volume_score = self._calculate_volume_score(ticker, price)
            chart_score = self._calculate_chart_score(ticker)
            candle_score = self._calculate_candle_score(ticker)
            period_score = self._calculate_period_score(ticker)
            flow_score = self._calculate_flow_score(ticker)

            # 총점 계산
            total = news_score + volume_score + chart_score + candle_score + period_score + flow_score

            score_detail = ScoreDetail(
                total=total,
                news=news_score,
                volume=volume_score,
                chart=chart_score,
                candle=candle_score,
                period=period_score,
                flow=flow_score,
            )

            # 등급 산정
            grade = self._calculate_grade(total)

            # 포지션 사이징
            capital = 10_000_000  # 1000만원 기준
            position_size = self._calculate_position_size(capital, price, grade)

            # 가격 목표 설정
            target_price = int(price * 1.15)  # +15%
            stop_loss = int(price * 0.95)  # -5%

            # 매매 사유 생성
            reasons = self._generate_reasons(score_detail)

            from datetime import datetime
            signal = JonggaSignal(
                ticker=ticker,
                name=name,
                score=score_detail,
                grade=grade,
                position_size=position_size,
                entry_price=price,
                target_price=target_price,
                stop_loss=stop_loss,
                reasons=reasons,
                created_at=datetime.now().isoformat(),
            )

            return signal

        except Exception as e:
            self.logger.error(f"시그널 계산 실패 ({ticker}): {e}")
            return None

    def _calculate_news_score(self, ticker: str) -> int:
        """
        뉴스 점수 (0-3점)

        - 긍정적 뉴스 3개 이상: 3점
        - 긍정적 뉴스 2개: 2점
        - 긍정적 뉴스 1개: 1점

        NewsScorer를 사용하여 뉴스 감성 분석 후 점수화
        """
        try:
            from datetime import date
            from src.collectors.news_collector import NewsCollector
            from src.analysis.news_scorer import NewsScorer

            # 뉴스 수집 (최근 7일, 최대 10건)
            collector = NewsCollector()
            articles = collector.fetch_stock_news(
                ticker=ticker,
                days=7,
                max_articles=10,
            )

            if not articles:
                self.logger.warning(f"{ticker} 뉴스 수집 실패, 기본 점수 0점")
                return 0

            # 뉴스 점수 계산
            scorer = NewsScorer()
            articles_dict = [collector.to_dict(a) for a in articles]
            result = scorer.calculate_daily_score(
                ticker=ticker,
                articles=articles_dict,
                target_date=date.today(),
            )

            score = int(result.total_score)
            self.logger.info(
                f"{ticker} 뉴스 점수: {score} "
                f"(긍정: {result.positive_count}, 부정: {result.negative_count})"
            )

            return score

        except Exception as e:
            self.logger.error(f"{ticker} 뉴스 점수 계산 실패: {e}")
            # 실패 시 기본 점수 0점
            return 0

    def _calculate_volume_score(self, ticker: str, price: int) -> int:
        """
        거래대금 점수 (0-3점)

        - 거래대금 5,000억 원 이상: 3점 (대형주 우량주)
        - 거래대금 1,000억 원 이상: 2점 (중형주)
        - 거래대금 300억 원 이상: 1점 (소형주)
        - 거래대금 300억 원 미만: 0점
        - 데이터 없음: 0점

        Args:
            ticker: 종목코드
            price: 현재가 (향후 확장성 고려)

        Returns:
            점수 (0-3)
        """
        try:
            repo = self._get_daily_price_repo()
            if repo is None:
                self.logger.warning(f"{ticker} Repository 없음, 기본 점수 0점")
                return 0

            # 최신 거래대금 조회
            from datetime import date, timedelta
            end_date = date.today()
            start_date = end_date - timedelta(days=7)

            prices = repo.get_by_ticker_and_date_range(ticker, start_date, end_date)
            if not prices:
                self.logger.warning(f"{ticker} 가격 데이터 없음, 기본 점수 0점")
                return 0

            # 최신 날짜의 거래대금 계산 (종가 * 거래량)
            latest = prices[-1]
            trading_value = latest.close_price * latest.volume

            # 점수 산정 (단위: 원)
            # 5,000억 = 500,000,000,000
            # 1,000억 = 100,000,000,000
            # 300억 = 30,000,000,000
            if trading_value >= 5_000_000_000_000:  # 5,000억 원 (5조)
                return 3
            elif trading_value >= 1_000_000_000_000:  # 1,000억 원 (1조)
                return 2
            elif trading_value >= 300_000_000_000:  # 300억 원 (3,000억)
                return 1
            else:
                return 0

        except Exception as e:
            self.logger.error(f"{ticker} 거래대금 점수 계산 실패: {e}")
            return 0

    def _calculate_chart_score(self, ticker: str) -> int:
        """
        차트패턴 점수 (0-2점)

        - VCP 패턴 + 52주 고가 근접: 2점
        - 둘 중 하나만 충족: 1점
        - 둘 다 미충족: 0점

        Args:
            ticker: 종목코드

        Returns:
            점수 (0-2)
        """
        try:
            analyzer = self._get_vcp_analyzer()
            if analyzer is None:
                return 0

            # VCP 패턴 감지
            is_vcp = analyzer.detect_vcp_pattern(ticker)
            # 52주 고가 근접 여부 (현재가가 52주 고가의 95% 이상)
            is_near_high = analyzer.is_near_52w_high(ticker, threshold=0.95)

            if is_vcp and is_near_high:
                return 2
            elif is_vcp or is_near_high:
                return 1
            else:
                return 0

        except Exception as e:
            self.logger.error(f"{ticker} 차트 점수 계산 실패: {e}")
            return 0

    def _calculate_candle_score(self, ticker: str) -> int:
        """
        캔들 점수 (0-1점)

        - 장대양봉 돌파: 1점
        - 기타: 0점

        Args:
            ticker: 종목코드

        Returns:
            점수 (0-1)
        """
        try:
            repo = self._get_daily_price_repo()
            if repo is None:
                return 0

            # 최근 3일 데이터 조회
            from datetime import date, timedelta
            end_date = date.today()
            start_date = end_date - timedelta(days=5)

            prices = repo.get_by_ticker_and_date_range(ticker, start_date, end_date)
            if len(prices) < 2:
                return 0

            # 최신 양봉 확인: 오늘 양봉이고 어제 종가보다 상승
            latest = prices[-1]
            previous = prices[-2]

            is_bullish = (
                latest.close_price > latest.open_price and  # 양봉
                latest.close_price > previous.close_price and  # 상승
                (latest.close_price - latest.open_price) / latest.open_price > 0.01  # 1% 이상 상승
            )

            return 1 if is_bullish else 0

        except Exception as e:
            self.logger.error(f"{ticker} 캔들 점수 계산 실패: {e}")
            return 0

    def _calculate_period_score(self, ticker: str) -> int:
        """
        기간조정 점수 (0-1점)

        - 첫 하락 이후 3일 이내 반등: 1점
        - 기타: 0점

        Args:
            ticker: 종목코드

        Returns:
            점수 (0-1)
        """
        try:
            repo = self._get_daily_price_repo()
            if repo is None:
                return 0

            # 최근 10일 데이터 조회
            from datetime import date, timedelta
            end_date = date.today()
            start_date = end_date - timedelta(days=14)

            prices = repo.get_by_ticker_and_date_range(ticker, start_date, end_date)
            if len(prices) < 5:
                return 0

            # 하락 후 반등 패턴 찾기
            # 1. 최근 저점 찾기
            min_price = min(prices, key=lambda p: p.low_price)
            min_idx = prices.index(min_price)

            # 2. 저점 이후 3일 이내 반등 여부
            if min_idx + 3 < len(prices):
                after_prices = prices[min_idx+1:min_idx+4]
                # 반등: 저점 이후 3일 내 종가가 저점 종가보다 3% 이상 상승
                rebound = any(
                    p.close_price >= min_price.close_price * 1.03
                    for p in after_prices
                )
                return 1 if rebound else 0

            return 0

        except Exception as e:
            self.logger.error(f"{ticker} 기간 점수 계산 실패: {e}")
            return 0

    def _calculate_flow_score(self, ticker: str) -> int:
        """
        수급 점수 (0-2점)

        - 외국인+기관 동시 순매수: 2점
        - 둘 중 하나만 순매수: 1점
        - 기타: 0점

        Args:
            ticker: 종목코드

        Returns:
            점수 (0-2)
        """
        try:
            repo = self._get_daily_price_repo()
            if repo is None:
                return 0

            # 최근 3일 데이터 조회
            from datetime import date, timedelta
            end_date = date.today()
            start_date = end_date - timedelta(days=7)

            prices = repo.get_by_ticker_and_date_range(ticker, start_date, end_date)
            if not prices:
                return 0

            # 최신 데이터 확인
            latest = prices[-1]

            # 외국인, 기관 수급 확인 (DailyPrice 테이블의 foreign_net_buy, inst_net_buy)
            foreign_buying = latest.foreign_net_buy or 0
            inst_buying = latest.inst_net_buy or 0

            # 외국인+기관 동시 순매수: 2점
            if foreign_buying > 0 and inst_buying > 0:
                self.logger.info(f"{ticker} 수급: 외국인+기관 동시 순매수 (+2)")
                return 2
            # 둘 중 하나만 순매수: 1점
            elif foreign_buying > 0 or inst_buying > 0:
                self.logger.info(f"{ticker} 수급: 일부 순매수 (+1)")
                return 1

            return 0

        except Exception as e:
            self.logger.error(f"{ticker} 수급 점수 계산 실패: {e}")
            return 0

    def _calculate_grade(self, total: int) -> Grade:
        """등급 산정"""
        if total >= 10:
            return Grade.S
        elif total >= 8:
            return Grade.A
        elif total >= 6:
            return Grade.B
        else:
            return Grade.C

    def _calculate_position_size(self, capital: int, price: int, grade: Grade) -> int:
        """
        포지션 크기 계산

        - S급: 15%
        - A급: 12%
        - B급: 10%
        - C급: 5%
        """
        grade_ratio = {
            Grade.S: 0.15,
            Grade.A: 0.12,
            Grade.B: 0.10,
            Grade.C: 0.05,
        }

        ratio = grade_ratio.get(grade, 0.05)
        amount = capital * ratio
        return int(amount / price)

    def _generate_reasons(self, score: ScoreDetail) -> List[str]:
        """매매 사유 생성"""
        reasons = []

        if score.news >= 2:
            reasons.append("긍정적 뉴스 다수")
        if score.volume >= 2:
            reasons.append("거래대금 급증")
        if score.chart >= 1:
            reasons.append("차트 패턴 우수")
        if score.flow >= 1:
            reasons.append("수급 개선")
        if score.candle >= 1:
            reasons.append("양봉 돌파")

        return reasons if reasons else ["종목 분석 완료"]
