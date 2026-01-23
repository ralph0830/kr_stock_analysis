"""
Signal Scorer - 종가베팅 V2 점수 계산
12점 만점 시스템
"""

from dataclasses import dataclass
from typing import List, Optional
from enum import Enum
import logging

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
    """종가베팅 점수 계산기"""

    def __init__(self):
        self.logger = logger

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
        """
        # TODO: LLM 뉴스 감성 분석
        import random
        return random.randint(0, 3)

    def _calculate_volume_score(self, ticker: str, price: int) -> int:
        """
        거래대금 점수 (0-3점)

        - 거래대금 500억 이상: 3점
        - 거래대금 300억 이상: 2점
        - 거래대금 100억 이상: 1점
        """
        # TODO: 실제 거래대금 조회
        import random
        return random.randint(0, 3)

    def _calculate_chart_score(self, ticker: str) -> int:
        """
        차트패턴 점수 (0-2점)

        - VCP 패턴 + 52주 고가 근접: 2점
        - 둘 중 하나: 1점
        """
        # TODO: 차트 패턴 분석
        import random
        return random.randint(0, 2)

    def _calculate_candle_score(self, ticker: str) -> int:
        """
        캔들 점수 (0-1점)

        - 양봉 돌파: 1점
        """
        # TODO: 캔들 패턴 분석
        import random
        return random.randint(0, 1)

    def _calculate_period_score(self, ticker: str) -> int:
        """
        기간조정 점수 (0-1점)

        - 첫 하락 이후 3일 이내 반등: 1점
        """
        # TODO: 기간 분석
        import random
        return random.randint(0, 1)

    def _calculate_flow_score(self, ticker: str) -> int:
        """
        수급 점수 (0-2점)

        - 외국인/기관 동시 순매수: 2점
        - 둘 중 하나: 1점
        """
        # TODO: 수급 데이터 분석
        import random
        return random.randint(0, 2)

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
