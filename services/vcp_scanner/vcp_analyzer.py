"""
VCP Analyzer
VCP 패턴 감지 및 SmartMoney 분석
"""

from dataclasses import dataclass
from typing import Optional, List, Dict, Any, Tuple
from datetime import date, datetime, timedelta
import logging
import asyncio
import numpy as np

from sqlalchemy import select, or_, desc
from src.database.session import SessionLocal
from src.database.models import Stock, DailyPrice, InstitutionalFlow

logger = logging.getLogger(__name__)


@dataclass
class VCPResult:
    """VCP 패턴 분석 결과"""
    ticker: str
    name: str
    vcp_score: float  # 0-100
    smartmoney_score: float  # 0-100
    total_score: float  # 0-100
    pattern_detected: bool
    signals: List[str]
    analysis_date: date
    current_price: Optional[float] = None  # 현재가 추가

    def to_dict(self) -> Dict[str, Any]:
        """Dict 변환"""
        return {
            "ticker": self.ticker,
            "name": self.name,
            "vcp_score": self.vcp_score,
            "smartmoney_score": self.smartmoney_score,
            "total_score": self.total_score,
            "pattern_detected": self.pattern_detected,
            "signals": self.signals,
            "analysis_date": self.analysis_date.isoformat(),
            "current_price": self.current_price,
        }


class VCPAnalyzer:
    """VCP 패턴 분석기"""

    def __init__(self):
        self.logger = logger

    async def analyze(self, ticker: str, name: str) -> Optional[VCPResult]:
        """
        종목 VCP 분석

        Args:
            ticker: 종목코드
            name: 종목명

        Returns:
            VCPResult 또는 None (데이터 부족)
        """
        try:
            vcp_score = await self._calculate_vcp_score(ticker)
            smartmoney_score = await self._calculate_smartmoney_score(ticker)
            current_price = await self._get_current_price(ticker)

            # 총점: VCP(50%) + SmartMoney(50%)
            total_score = (vcp_score * 0.5) + (smartmoney_score * 0.5)

            signals = []
            if vcp_score > 60:
                signals.append("VCP 수축 감지")
            if smartmoney_score > 60:
                signals.append("SmartMoney 유입")

            pattern_detected = total_score >= 60

            return VCPResult(
                ticker=ticker,
                name=name,
                vcp_score=vcp_score,
                smartmoney_score=smartmoney_score,
                total_score=total_score,
                pattern_detected=pattern_detected,
                signals=signals,
                analysis_date=date.today(),
                current_price=current_price,
            )

        except Exception as e:
            self.logger.error(f"VCP 분석 실패 ({ticker}): {e}")
            return None

    async def _get_current_price(self, ticker: str) -> Optional[float]:
        """현재가 조회"""
        def fetch_price() -> Optional[float]:
            session = SessionLocal()
            try:
                query = select(DailyPrice.close_price)
                query = query.where(DailyPrice.ticker == ticker)
                query = query.order_by(desc(DailyPrice.date))
                query = query.limit(1)
                result = session.execute(query)
                price = result.scalar_one_or_none()
                return float(price) if price else None
            finally:
                session.close()

        return await asyncio.to_thread(fetch_price)

    async def _calculate_vcp_score(self, ticker: str) -> float:
        """
        VCP 점수 계산 (0-100)

        - 볼린저밴드 수축 (30%)
        - 거래량 감소 (20%)
        - 가격 변동성 감소 (20%)
        - RSI 중립 (15%)
        - MACD 정렬 (15%)
        """
        def fetch_prices() -> List[Tuple]:
            """최근 20일 가격 데이터 조회"""
            session = SessionLocal()
            try:
                cutoff_date = date.today() - timedelta(days=60)
                query = select(DailyPrice)
                query = query.where(DailyPrice.ticker == ticker)
                query = query.where(DailyPrice.date >= cutoff_date)
                query = query.order_by(DailyPrice.date)
                result = session.execute(query)
                prices = result.scalars().all()
                # 필요한 컬럼만 반환
                return [(p.date, p.close_price, p.high_price, p.low_price, p.volume) for p in prices]
            finally:
                session.close()

        prices_data = await asyncio.to_thread(fetch_prices)

        if len(prices_data) < 10:
            logger.warning(f"{ticker}: 데이터 부족 ({len(prices_data)}일)")
            return 0.0

        closes = np.array([float(p[1]) for p in prices_data if p[1] is not None])
        highs = np.array([float(p[2]) for p in prices_data if p[2] is not None])
        lows = np.array([float(p[3]) for p in prices_data if p[3] is not None])
        volumes = np.array([float(p[4]) for p in prices_data if p[4] is not None])

        if len(closes) < 10:
            return 0.0

        scores = []

        # 1. 볼린저밴드 수축 (30%)
        try:
            bb_period = 20
            if len(closes) >= bb_period:
                sma = np.mean(closes[-bb_period:])
                std = np.std(closes[-bb_period:])
                bb_width = (std * 2) / sma * 100 if sma > 0 else 0

                # 밴드폭이 5% 미만이면 수축으로 판단
                if bb_width < 5:
                    bb_score = 100
                elif bb_width < 8:
                    bb_score = 70
                elif bb_width < 10:
                    bb_score = 40
                else:
                    bb_score = 10
                scores.append(("bb", bb_score, 30))
            else:
                scores.append(("bb", 50, 30))
        except Exception:
            scores.append(("bb", 50, 30))

        # 2. 거래량 감소 (20%)
        try:
            if len(volumes) >= 10:
                recent_vol = np.mean(volumes[-5:])
                past_vol = np.mean(volumes[-10:-5]) if len(volumes) >= 10 else recent_vol
                vol_ratio = (recent_vol / past_vol * 100) if past_vol > 0 else 100

                # 거래량이 감소했을 때 점수
                if vol_ratio < 70:
                    vol_score = 100
                elif vol_ratio < 90:
                    vol_score = 70
                elif vol_ratio < 110:
                    vol_score = 50
                else:
                    vol_score = 20
                scores.append(("vol", vol_score, 20))
            else:
                scores.append(("vol", 50, 20))
        except Exception:
            scores.append(("vol", 50, 20))

        # 3. 가격 변동성 감소 (20%)
        try:
            if len(closes) >= 10:
                recent_std = np.std(closes[-5:])
                past_std = np.std(closes[-10:-5]) if len(closes) >= 10 else recent_std
                vol_ratio = (recent_std / past_std * 100) if past_std > 0 else 100

                # 변동성이 감소했을 때 점수
                if vol_ratio < 70:
                    volat_score = 100
                elif vol_ratio < 90:
                    volat_score = 70
                elif vol_ratio < 110:
                    volat_score = 50
                else:
                    volat_score = 20
                scores.append(("volat", volat_score, 20))
            else:
                scores.append(("volat", 50, 20))
        except Exception:
            scores.append(("volat", 50, 20))

        # 4. RSI 중립 (15%)
        try:
            if len(closes) >= 14:
                deltas = np.diff(closes[-14:])
                gains = np.where(deltas > 0, deltas, 0)
                losses = np.where(deltas < 0, -deltas, 0)
                avg_gain = np.mean(gains)
                avg_loss = np.mean(losses)
                rs = avg_gain / avg_loss if avg_loss > 0 else 0
                rsi = 100 - (100 / (1 + rs))

                # RSI가 30-70 사이면 점수
                if 40 <= rsi <= 60:
                    rsi_score = 100
                elif 30 <= rsi <= 70:
                    rsi_score = 70
                elif 25 <= rsi <= 75:
                    rsi_score = 40
                else:
                    rsi_score = 10
                scores.append(("rsi", rsi_score, 15))
            else:
                scores.append(("rsi", 50, 15))
        except Exception:
            scores.append(("rsi", 50, 15))

        # 5. MACD 정렬 (15%)
        try:
            if len(closes) >= 12:
                # 단순 MACD 계산 (12-day EMA - 26-day EMA)
                def ema(data, period):
                    alpha = 2 / (period + 1)
                    return np.array([data[0]] + [
                        alpha * data[i] + (1 - alpha) * result[-1]
                        for i in range(1, len(data))
                    ])

                ema12 = ema(closes[-26:], 12) if len(closes) >= 26 else ema(closes, 12)
                ema26 = ema(closes[-26:], 26) if len(closes) >= 26 else ema(closes, min(26, len(closes)))

                macd = ema12[-1] - ema26[-1] if len(ema12) > 0 and len(ema26) > 0 else 0
                macd_signal = macd  # 단순화

                # MACD가 양수이면 점수
                if macd > 0 and macd_signal > 0:
                    macd_score = 100
                elif macd > 0:
                    macd_score = 60
                elif macd > -closes[-1] * 0.02:
                    macd_score = 40
                else:
                    macd_score = 10
                scores.append(("macd", macd_score, 15))
            else:
                scores.append(("macd", 50, 15))
        except Exception:
            scores.append(("macd", 50, 15))

        # 가중 평균 계산
        total_score = sum(score * weight / 100 for _, score, weight in scores)
        return max(0, min(100, total_score))

    async def _calculate_smartmoney_score(self, ticker: str) -> float:
        """
        SmartMoney 점수 계산 (0-100)

        - 외국인 수급 (40%)
        - 기관 수급 (30%)
        - 수급 종합 점수 (30%)
        """
        def fetch_flows() -> List[Tuple]:
            """최근 수급 데이터 조회"""
            session = SessionLocal()
            try:
                cutoff_date = date.today() - timedelta(days=60)
                query = select(InstitutionalFlow)
                query = query.where(InstitutionalFlow.ticker == ticker)
                query = query.where(InstitutionalFlow.date >= cutoff_date)
                query = query.order_by(InstitutionalFlow.date)
                result = session.execute(query)
                flows = result.scalars().all()
                return [
                    (f.foreign_net_buy, f.inst_net_buy, f.supply_demand_score)
                    for f in flows
                ]
            finally:
                session.close()

        flows_data = await asyncio.to_thread(fetch_flows)

        if len(flows_data) < 3:
            logger.warning(f"{ticker}: 수급 데이터 부족 ({len(flows_data)}일)")
            return 50.0  # 기본 점수

        scores = []

        # 1. 외국인 수급 (40%)
        try:
            recent_foreign = [float(f[0]) for f in flows_data[-5:] if f[0] is not None]
            if len(recent_foreign) > 0:
                avg_foreign = np.mean(recent_foreign)
                # 순매수 금액이 크면 점수 높음
                if avg_foreign > 100000:
                    foreign_score = 100
                elif avg_foreign > 50000:
                    foreign_score = 80
                elif avg_foreign > 0:
                    foreign_score = 60
                elif avg_foreign > -50000:
                    foreign_score = 40
                else:
                    foreign_score = 10
                scores.append(("foreign", foreign_score, 40))
            else:
                scores.append(("foreign", 50, 40))
        except Exception:
            scores.append(("foreign", 50, 40))

        # 2. 기관 수급 (30%)
        try:
            recent_inst = [float(f[1]) for f in flows_data[-5:] if f[1] is not None]
            if len(recent_inst) > 0:
                avg_inst = np.mean(recent_inst)
                if avg_inst > 100000:
                    inst_score = 100
                elif avg_inst > 50000:
                    inst_score = 80
                elif avg_inst > 0:
                    inst_score = 60
                elif avg_inst > -50000:
                    inst_score = 40
                else:
                    inst_score = 10
                scores.append(("inst", inst_score, 30))
            else:
                scores.append(("inst", 50, 30))
        except Exception:
            scores.append(("inst", 50, 30))

        # 3. 수급 종합 점수 (30%) - supply_demand_score 사용
        try:
            latest_score = flows_data[-1][2] if flows_data and flows_data[-1][2] is not None else None
            if latest_score is not None:
                score = float(latest_score)
                # 수급 점수가 높으면 점수
                if score >= 80:
                    supply_score = 100
                elif score >= 60:
                    supply_score = 80
                elif score >= 40:
                    supply_score = 60
                elif score >= 20:
                    supply_score = 40
                else:
                    supply_score = 20
                scores.append(("supply", supply_score, 30))
            else:
                scores.append(("supply", 50, 30))
        except Exception:
            scores.append(("supply", 50, 30))

        # 가중 평균 계산
        total_score = sum(score * weight / 100 for _, score, weight in scores)
        return max(0, min(100, total_score))

    async def scan_market(
        self,
        market: str = "ALL",
        top_n: int = 30,
        min_score: float = 0.0
    ) -> List[VCPResult]:
        """
        시장 전체 스캔

        Args:
            market: KOSPI, KOSDAQ, 또는 ALL (전체)
            top_n: 상위 N개 종목 반환 (0 = 전체)
            min_score: 최소 VCP 점수 (이하 필터링)

        Returns:
            VCPResult 리스트 (점수순 정렬)
        """
        results = []

        # DB에서 전체 종목 조회 (스레드 풀 사용)
        def fetch_stocks() -> List[tuple]:
            """동기 DB 작업을 스레드에서 실행"""
            session = SessionLocal()
            try:
                # 시장 필터
                query = select(Stock)
                if market == "KOSPI":
                    query = query.where(Stock.market == "KOSPI")
                elif market == "KOSDAQ":
                    query = query.where(Stock.market == "KOSDAQ")
                # ALL인 경우 필터 없이 전체 조회

                # 관리종목 제외 (NULL 또는 False만 포함)
                query = query.where(or_(Stock.is_admin == False, Stock.is_admin.is_(None)))

                result = session.execute(query)
                stocks = result.scalars().all()
                # 종목 정보를 튜플로 반환 (Session 종료 후에도 사용 가능)
                return [(s.ticker, s.name) for s in stocks]
            finally:
                session.close()

        # 스레드 풀에서 DB 작업 실행
        stock_list = await asyncio.to_thread(fetch_stocks)

        self.logger.info(f"VCP 스캔 시작: {market} 시장, {len(stock_list)} 종목")

        # 병렬 분석 (세마포어로 동시 수 제한)
        semaphore = asyncio.Semaphore(10)  # 최대 10개 동시 분석

        async def analyze_with_semaphore(ticker_name: tuple) -> Optional[VCPResult]:
            """세마포어로 제어된 분석"""
            async with semaphore:
                ticker, name = ticker_name
                return await self.analyze(ticker, name)

        # 전체 종목 비동기 분석
        tasks = [analyze_with_semaphore(ticker_name) for ticker_name in stock_list]
        analysis_results = await asyncio.gather(*tasks, return_exceptions=True)

        # 결과 수집
        for item in analysis_results:
            if isinstance(item, Exception):
                self.logger.warning(f"분석 중 예외 발생: {item}")
                continue
            if item is not None:
                # 최소 점수 필터
                if item.total_score >= min_score:
                    results.append(item)

        # 점수순 정렬
        results.sort(key=lambda x: -x.total_score)

        # top_n 제한 (0이면 전체)
        if top_n > 0:
            results = results[:top_n]

        self.logger.info(f"VCP 스캔 완료: {len(results)}개 시그널 발견 (최소 점수: {min_score})")

        return results
