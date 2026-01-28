"""
Backtest Repository
백테스트 결과 데이터 접근 계층
"""

from typing import List, Optional, Dict, Any
from datetime import date, datetime
from sqlalchemy.orm import Session
from sqlalchemy import select, and_, desc, func
from src.repositories.base import BaseRepository
from src.database.models import BacktestResult


class BacktestRepository(BaseRepository[BacktestResult]):
    """
    Backtest Repository
    백테스트 결과 CRUD 작업 처리
    """

    def __init__(self, session: Session):
        super().__init__(BacktestResult, session)

    def get_latest(
        self,
        config_name: Optional[str] = None,
        limit: int = 20
    ) -> List[BacktestResult]:
        """
        최신 백테스트 결과 조회

        Args:
            config_name: 설정명 필터 (선택)
            limit: 최대 반환 수

        Returns:
            최신 BacktestResult 리스트 (created_at 내림차순)
        """
        query = select(BacktestResult)

        # 설정명 필터
        if config_name:
            query = query.where(BacktestResult.config_name == config_name)

        # created_at 내림차순 정렬
        query = query.order_by(desc(BacktestResult.created_at)).limit(limit)

        result = self.session.execute(query)
        return list(result.scalars().all())

    def get_summary(self, config_name: Optional[str] = None) -> Dict[str, Any]:
        """
        백테스트 결과 요약 통계

        Args:
            config_name: 설정명 필터 (선택)

        Returns:
            통계 정보 딕셔너리
        """
        query = select(BacktestResult)

        if config_name:
            query = query.where(BacktestResult.config_name == config_name)

        result = self.session.execute(query)
        results = list(result.scalars().all())

        if not results:
            return {
                "total_backtests": 0,
                "avg_return_pct": 0.0,
                "avg_win_rate": 0.0,
                "best_return_pct": 0.0,
                "worst_return_pct": 0.0,
                "avg_sharpe_ratio": 0.0,
                "avg_max_drawdown_pct": 0.0,
            }

        # 통계 계산
        total_backtests = len(results)
        avg_return_pct = sum(r.total_return_pct for r in results) / total_backtests

        # win_rate가 있는 결과만 평균 계산
        win_rates = [r.win_rate for r in results if r.win_rate is not None]
        avg_win_rate = sum(win_rates) / len(win_rates) if win_rates else 0.0

        best_return_pct = max(r.total_return_pct for r in results)
        worst_return_pct = min(r.total_return_pct for r in results)

        # sharpe_ratio 평균
        sharpe_ratios = [r.sharpe_ratio for r in results if r.sharpe_ratio is not None]
        avg_sharpe_ratio = sum(sharpe_ratios) / len(sharpe_ratios) if sharpe_ratios else 0.0

        # max_drawdown_pct 평균
        drawdowns = [r.max_drawdown_pct for r in results if r.max_drawdown_pct is not None]
        avg_max_drawdown_pct = sum(drawdowns) / len(drawdowns) if drawdowns else 0.0

        return {
            "total_backtests": total_backtests,
            "avg_return_pct": round(avg_return_pct, 2),
            "avg_win_rate": round(avg_win_rate, 2),
            "best_return_pct": round(best_return_pct, 2),
            "worst_return_pct": round(worst_return_pct, 2),
            "avg_sharpe_ratio": round(avg_sharpe_ratio, 2),
            "avg_max_drawdown_pct": round(avg_max_drawdown_pct, 2),
        }

    def get_best_result(
        self,
        config_name: Optional[str] = None
    ) -> Optional[BacktestResult]:
        """
        최고 수익률 백테스트 결과 조회

        Args:
            config_name: 설정명 필터 (선택)

        Returns:
            최고 수익률 BacktestResult 또는 None
        """
        query = select(BacktestResult)

        if config_name:
            query = query.where(BacktestResult.config_name == config_name)

        # total_return_pct 내림차순 정렬 후 1개만 조회
        query = query.order_by(desc(BacktestResult.total_return_pct)).limit(1)

        result = self.session.execute(query)
        return result.scalar_one_or_none()

    def get_history(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        config_name: Optional[str] = None,
        limit: int = 50
    ) -> List[BacktestResult]:
        """
        백테스트 히스토리 조회

        Args:
            start_date: 시작 날짜 (선택)
            end_date: 종료 날짜 (선택)
            config_name: 설정명 필터 (선택)
            limit: 최대 반환 수

        Returns:
            BacktestResult 리스트 (backtest_date 내림차순)
        """
        query = select(BacktestResult)

        # 날짜 범위 필터
        if start_date and end_date:
            query = query.where(
                and_(
                    BacktestResult.backtest_date >= start_date,
                    BacktestResult.backtest_date <= end_date
                )
            )
        elif start_date:
            query = query.where(BacktestResult.backtest_date >= start_date)
        elif end_date:
            query = query.where(BacktestResult.backtest_date <= end_date)

        # 설정명 필터
        if config_name:
            query = query.where(BacktestResult.config_name == config_name)

        # backtest_date 내림차순 정렬
        query = query.order_by(desc(BacktestResult.backtest_date)).limit(limit)

        result = self.session.execute(query)
        return list(result.scalars().all())

    def get_by_config_and_date(
        self,
        config_name: str,
        backtest_date: date
    ) -> Optional[BacktestResult]:
        """
        설정명과 날짜로 백테스트 결과 조회

        Args:
            config_name: 설정명
            backtest_date: 백테스트 날짜

        Returns:
            BacktestResult 또는 None
        """
        query = select(BacktestResult).where(
            and_(
                BacktestResult.config_name == config_name,
                BacktestResult.backtest_date == backtest_date
            )
        )

        result = self.session.execute(query)
        return result.scalar_one_or_none()

    def delete_by_config_and_date(
        self,
        config_name: str,
        backtest_date: date
    ) -> bool:
        """
        설정명과 날짜로 백테스트 결과 삭제

        Args:
            config_name: 설정명
            backtest_date: 백테스트 날짜

        Returns:
            삭제 성공 여부
        """
        result = self.get_by_config_and_date(config_name, backtest_date)
        if result:
            self.session.delete(result)
            self.session.commit()
            return True
        return False

    def get_configs(self) -> List[str]:
        """
        등록된 모든 설정명 조회

        Returns:
            설정명 리스트
        """
        query = select(BacktestResult.config_name).distinct()
        result = self.session.execute(query)
        return [row[0] for row in result.all()]
