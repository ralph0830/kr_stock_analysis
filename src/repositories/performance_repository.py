"""
Performance Repository
누적 수익률 및 성과 지표 데이터 접근 계층
"""

from typing import List, Optional, Dict, Any
from datetime import date, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import select, and_, desc
from src.repositories.base import BaseRepository
from src.database.models import Signal, DailyPrice


class PerformanceRepository(BaseRepository[Signal]):
    """
    Performance Repository
    시그널 성과 분석 및 누적 수익률 계산
    """

    def __init__(self, session: Session):
        super().__init__(Signal, session)

    def calculate_cumulative_return(
        self,
        signal_type: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> List[Dict[str, Any]]:
        """
        누적 수익률 계산

        Args:
            signal_type: 시그널 타입 필터 (VCP/JONGGA_V2)
            start_date: 시작 날짜
            end_date: 종료 날짜

        Returns:
            날짜별 누적 수익률 리스트
        """
        # 기본 조건: CLOSED 상태의 시그널만 (실현된 수익률)
        query = select(Signal).where(Signal.status == "CLOSED")

        if signal_type:
            query = query.where(Signal.signal_type == signal_type)
        if start_date:
            query = query.where(Signal.signal_date >= start_date)
        if end_date:
            query = query.where(Signal.signal_date <= end_date)

        query = query.order_by(Signal.signal_date)

        result = self.session.execute(query)
        signals = list(result.scalars().all())

        # 날짜별 그룹화 및 수익률 계산
        daily_returns: Dict[str, List[float]] = {}

        for signal in signals:
            if not signal.entry_price or not signal.exit_time:
                continue

            # 종가 데이터에서 exit 시점의 가격 조회
            exit_date = signal.exit_time.date()
            price_query = select(DailyPrice).where(
                and_(
                    DailyPrice.ticker == signal.ticker,
                    DailyPrice.date == exit_date
                )
            )
            price_result = self.session.execute(price_query).first()

            if not price_result:
                continue

            exit_price = price_result.close_price

            # 수익률 계산
            return_pct = ((exit_price - signal.entry_price) / signal.entry_price) * 100

            signal_date_str = signal.signal_date.isoformat()
            if signal_date_str not in daily_returns:
                daily_returns[signal_date_str] = []
            daily_returns[signal_date_str].append(return_pct)

        # 누적 수익률 계산
        cumulative_returns = []
        cumulative_value = 100.0  # 기준 100
        sorted_dates = sorted(daily_returns.keys())

        for date_str in sorted_dates:
            returns = daily_returns[date_str]
            if returns:
                avg_return = sum(returns) / len(returns)
                cumulative_value *= (1 + avg_return / 100)
                cumulative_returns.append({
                    "date": date_str,
                    "daily_return_pct": avg_return,
                    "cumulative_return_pct": cumulative_value - 100,
                })

        return cumulative_returns

    def calculate_signal_performance(
        self,
        ticker: Optional[str] = None,
        signal_type: Optional[str] = None,
        days: int = 30,
    ) -> Dict[str, Any]:
        """
        시그널별 성과 계산

        Args:
            ticker: 종목 필터
            signal_type: 시그널 타입 필터
            days: 조회 기간 (일)

        Returns:
            성과 지표 딕셔너리
        """
        since_date = date.today() - timedelta(days=days)

        query = select(Signal).where(
            and_(
                Signal.signal_date >= since_date,
                Signal.status == "CLOSED"
            )
        )

        if ticker:
            query = query.where(Signal.ticker == ticker)
        if signal_type:
            query = query.where(Signal.signal_type == signal_type)

        result = self.session.execute(query)
        signals = list(result.scalars().all())

        if not signals:
            return {
                "total_signals": 0,
                "win_rate": 0.0,
                "avg_return": 0.0,
                "best_return": None,
                "worst_return": None,
            }

        # 각 시그널의 수익률 계산
        returns = []
        for signal in signals:
            if not signal.entry_price or not signal.exit_time:
                continue

            exit_date = signal.exit_time.date()
            price_query = select(DailyPrice).where(
                and_(
                    DailyPrice.ticker == signal.ticker,
                    DailyPrice.date == exit_date
                )
            )
            price_result = self.session.execute(price_query).first()

            if not price_result:
                continue

            exit_price = price_result.close_price
            return_pct = ((exit_price - signal.entry_price) / signal.entry_price) * 100
            returns.append(return_pct)

        if not returns:
            return {
                "total_signals": len(signals),
                "win_rate": 0.0,
                "avg_return": 0.0,
                "best_return": None,
                "worst_return": None,
            }

        wins = [r for r in returns if r > 0]

        return {
            "total_signals": len(signals),
            "closed_signals": len(returns),
            "win_rate": (len(wins) / len(returns) * 100) if returns else 0,
            "avg_return": sum(returns) / len(returns) if returns else 0,
            "best_return": max(returns) if returns else None,
            "worst_return": min(returns) if returns else None,
        }

    def calculate_sharpe_ratio(
        self,
        signal_type: Optional[str] = None,
        days: int = 30,
        risk_free_rate: float = 2.0,
    ) -> float:
        """
        샤프 비율 계산

        Args:
            signal_type: 시그널 타입 필터
            days: 조회 기간 (일)
            risk_free_rate: 무위험 이자율 (연율 %)

        Returns:
            샤프 비율
        """
        cumulative_returns = self.calculate_cumulative_return(
            signal_type=signal_type,
            start_date=date.today() - timedelta(days=days),
        )

        if len(cumulative_returns) < 2:
            return 0.0

        # 일일 수익률 추출
        daily_returns = [r["daily_return_pct"] for r in cumulative_returns]

        if not daily_returns:
            return 0.0

        # 평균과 표준편차 계산
        avg_return = sum(daily_returns) / len(daily_returns)
        variance = sum((r - avg_return) ** 2 for r in daily_returns) / len(daily_returns)
        std_dev = variance ** 0.5

        if std_dev == 0:
            return 0.0

        # 연율화 (252 거래일 기준)
        daily_risk_free = risk_free_rate / 252

        # 샤프 비율 = (평균 수익률 - 무위험 이자율) / 표준편차 * sqrt(252)
        sharpe = ((avg_return / 100) - daily_risk_free / 100) / (std_dev / 100)
        sharpe_annualized = sharpe * (252 ** 0.5)

        return sharpe_annualized

    def get_performance_by_period(
        self,
        period: str = "1mo",
        signal_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        기간별 성과 조회

        Args:
            period: 기간 (1w, 2w, 1mo, 3mo, 6mo, 1y)
            signal_type: 시그널 타입 필터

        Returns:
            기간별 성과 지표
        """
        period_days = {
            "1w": 7,
            "2w": 14,
            "1mo": 30,
            "3mo": 90,
            "6mo": 180,
            "1y": 365,
        }
        days = period_days.get(period, 30)

        performance = self.calculate_signal_performance(
            signal_type=signal_type,
            days=days,
        )

        cumulative = self.calculate_cumulative_return(
            signal_type=signal_type,
            start_date=date.today() - timedelta(days=days),
        )

        # 전체 누적 수익률
        total_cumulative = cumulative[-1]["cumulative_return_pct"] if cumulative else 0.0

        # 최대 낙폭 (MDD) 계산
        mdd = 0.0
        peak = 100.0
        for item in cumulative:
            peak = max(peak, 100 + item["cumulative_return_pct"])
            drawdown = (peak - (100 + item["cumulative_return_pct"])) / peak * 100
            mdd = max(mdd, drawdown)

        return {
            "period": period,
            "total_signals": performance["total_signals"],
            "win_rate": performance["win_rate"],
            "avg_return": performance["avg_return"],
            "cumulative_return": total_cumulative,
            "mdd": mdd,
            "best_return": performance["best_return"],
            "worst_return": performance["worst_return"],
            "sharpe_ratio": self.calculate_sharpe_ratio(signal_type=signal_type, days=days),
        }

    def get_top_performers(
        self,
        signal_type: Optional[str] = None,
        limit: int = 10,
        days: int = 30,
    ) -> List[Dict[str, Any]]:
        """
        최고 성과 종목 조회

        Args:
            signal_type: 시그널 타입 필터
            limit: 최대 반환 수
            days: 조회 기간

        Returns:
            최고 성과 종목 리스트
        """
        since_date = date.today() - timedelta(days=days)

        # 서브쿼리로 수익률 계산 후 정렬 - 더 최적화된 방법
        query = select(Signal).where(
            and_(
                Signal.signal_date >= since_date,
                Signal.status == "CLOSED",
                Signal.entry_price.isnot(None),
                Signal.exit_time.isnot(None)
            )
        )

        if signal_type:
            query = query.where(Signal.signal_type == signal_type)

        query = query.order_by(desc(Signal.signal_date))

        result = self.session.execute(query)
        signals = list(result.scalars().all())

        # 수익률 계산 및 정렬
        performers = []
        for signal in signals:
            exit_date = signal.exit_time.date()
            price_query = select(DailyPrice.close_price).where(
                and_(
                    DailyPrice.ticker == signal.ticker,
                    DailyPrice.date == exit_date
                )
            )
            price_result = self.session.execute(price_query).first()

            if price_result and signal.entry_price:
                return_pct = ((price_result - signal.entry_price) / signal.entry_price) * 100
                performers.append({
                    "ticker": signal.ticker,
                    "signal_type": signal.signal_type,
                    "entry_price": signal.entry_price,
                    "exit_price": price_result,
                    "return_pct": round(return_pct, 2),
                    "signal_date": signal.signal_date.isoformat(),
                })

        # 수익률 기준 정렬
        performers.sort(key=lambda x: x["return_pct"], reverse=True)

        return performers[:limit]
