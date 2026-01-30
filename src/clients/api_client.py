"""
Ralph Stock API Client
API Gateway와 통신하기 위한 HTTP 클라이언트
"""

from typing import Optional, Dict, Any, List
from dataclasses import dataclass
import httpx


@dataclass
class Signal:
    """VCP 시그널 데이터 모델"""

    ticker: str
    name: str
    signal_type: str
    score: float
    grade: str
    entry_price: Optional[float] = None
    target_price: Optional[float] = None
    created_at: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Signal":
        """딕셔너리から Signal 객체 생성"""
        return cls(
            ticker=data.get("ticker", ""),
            name=data.get("name", ""),
            signal_type=data.get("signal_type", ""),
            score=data.get("score", 0.0),
            grade=data.get("grade", ""),
            entry_price=data.get("entry_price"),
            target_price=data.get("target_price"),
            created_at=data.get("created_at"),
        )


@dataclass
class MarketGateStatus:
    """Market Gate 상태 모델"""

    status: str  # GREEN, YELLOW, RED
    level: int
    kospi_status: str
    kosdaq_status: str
    updated_at: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MarketGateStatus":
        """딕셔너리에서 MarketGateStatus 객체 생성"""
        return cls(
            status=data.get("status", "YELLOW"),
            level=data.get("level", 2),
            kospi_status=data.get("kospi_status", "YELLOW"),
            kosdaq_status=data.get("kosdaq_status", "YELLOW"),
            updated_at=data.get("updated_at"),
        )


@dataclass
class StockPrice:
    """종목 가격 데이터 모델"""

    ticker: str
    name: str
    price: float
    change: float
    change_percent: float
    volume: int
    timestamp: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StockPrice":
        """딕셔너리에서 StockPrice 객체 생성"""
        return cls(
            ticker=data.get("ticker", ""),
            name=data.get("name", ""),
            price=data.get("price", 0.0),
            change=data.get("change", 0.0),
            change_percent=data.get("change_percent", 0.0),
            volume=data.get("volume", 0),
            timestamp=data.get("timestamp"),
        )


class APIClient:
    """
    Ralph Stock API Gateway용 HTTP 클라이언트

    사용 예:
        client = APIClient(base_url="http://localhost:5111")
        signals = await client.get_signals(limit=10)
        market_gate = await client.get_market_gate()
    """

    def __init__(
        self,
        base_url: str = "http://localhost:5111",
        api_key: Optional[str] = None,
        timeout: float = 30.0,
    ):
        """
        API 클라이언트 초기화

        Args:
            base_url: API Gateway 기본 URL
            api_key: API 인증 키 (선택)
            timeout: 요청 타임아웃 (초)
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.headers = {"Content-Type": "application/json"}

        if api_key:
            self.headers["X-API-Key"] = api_key

    async def _request(
        self,
        method: str,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        HTTP 요청 전송

        Args:
            method: HTTP 메서드 (GET, POST, etc.)
            path: 요청 경로
            params: 쿼리 파라미터
            json_data: JSON 요청 본문

        Returns:
            응답 JSON 데이터

        Raises:
            httpx.HTTPStatusError: HTTP 에러 발생 시
            httpx.RequestError: 요청 실패 시
        """
        url = f"{self.base_url}{path}"

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.request(
                method=method,
                url=url,
                params=params,
                json=json_data,
                headers=self.headers,
            )
            response.raise_for_status()
            return response.json()

    async def health_check(self) -> Dict[str, Any]:
        """
        헬스 체크

        Returns:
            서비스 상태 정보
        """
        return await self._request("GET", "/health")

    async def get_signals(
        self,
        limit: int = 20,
        status: Optional[str] = None,
        min_score: Optional[float] = None,
    ) -> List[Signal]:
        """
        활성 VCP 시그널 조회

        Args:
            limit: 반환할 최대 시그널 수 (1-100)
            status: 시그널 상태 필터
            min_score: 최소 점수 필터

        Returns:
            시그널 목록
        """
        params = {"limit": limit}
        if status:
            params["status"] = status
        if min_score is not None:
            params["min_score"] = min_score

        data = await self._request("GET", "/api/kr/signals", params=params)

        if isinstance(data, list):
            return [Signal.from_dict(item) for item in data]
        return []

    async def get_market_gate(self) -> MarketGateStatus:
        """
        Market Gate 상태 조회

        Returns:
            Market Gate 상태
        """
        data = await self._request("GET", "/api/kr/market-gate")
        return MarketGateStatus.from_dict(data)

    async def get_jongga_v2_latest(self) -> List[Signal]:
        """
        최신 종가베팅 V2 시그널 조회

        Returns:
            종가베팅 V2 시그널 목록
        """
        data = await self._request("GET", "/api/kr/jongga-v2/latest")

        if isinstance(data, list):
            return [Signal.from_dict(item) for item in data]
        return []

    async def get_realtime_prices(
        self,
        tickers: List[str],
        max_age_seconds: int = 60,
    ) -> Dict[str, StockPrice]:
        """
        실시간 가격 일괄 조회

        Args:
            tickers: 종목코드 목록
            max_age_seconds: 데이터 최대 허용 연령 (초)

        Returns:
            종목코드별 가격 데이터 맵
        """
        data = await self._request(
            "POST",
            "/api/kr/realtime-prices",
            json_data={"tickers": tickers, "max_age_seconds": max_age_seconds},
        )

        prices = data.get("prices", {})
        return {
            ticker: StockPrice.from_dict(price_data)
            for ticker, price_data in prices.items()
        }

    async def get_stock_chart(
        self,
        ticker: str,
        period: str = "6mo",
    ) -> Dict[str, Any]:
        """
        종목 차트 데이터 조회

        Args:
            ticker: 종목코드
            period: 기간 (1mo, 3mo, 6mo, 1y)

        Returns:
            차트 데이터
        """
        return await self._request(
            "GET",
            f"/api/kr/stock-chart/{ticker}",
            params={"period": period},
        )

    async def get_metrics(
        self,
        metric_type: Optional[str] = None,
        limit: int = 10,
    ) -> Dict[str, Any]:
        """
        메트릭 조회

        Args:
            metric_type: 필터링할 메트릭 타입 (counter, gauge, histogram)
            limit: 반환할 메트릭 수

        Returns:
            메트릭 데이터
        """
        params = {"limit": limit}
        if metric_type:
            params["metric_type"] = metric_type

        return await self._request("GET", "/api/metrics", params=params)

    async def get_dashboard_overview(self) -> Dict[str, Any]:
        """
        대시보드 개요 조회

        Returns:
            시스템 개요 정보
        """
        return await self._request("GET", "/api/dashboard/overview")

    async def get_connection_info(self) -> Dict[str, Any]:
        """
        WebSocket 연결 정보 조회

        Returns:
            연결 정보
        """
        return await self._request("GET", "/api/dashboard/connections")

    async def get_signal_summary(
        self,
        limit: int = 20,
    ) -> Dict[str, Any]:
        """
        시그널 요약 조회

        Args:
            limit: 반환할 시그널 수

        Returns:
            시그널 요약 정보
        """
        return await self._request(
            "GET",
            "/api/dashboard/signals",
            params={"limit": limit},
        )


# 동기식 래퍼 (간단한 사용을 위한 별도 클래스)
class SyncAPIClient:
    """
    동기식 API 클라이언트 (단순 스크립트용)

    비동기 코드가 필요 없는 간단한 스크립트에서 사용합니다.
    """

    def __init__(
        self,
        base_url: str = "http://localhost:5111",
        api_key: Optional[str] = None,
        timeout: float = 30.0,
    ):
        import asyncio

        self._async_client = APIClient(base_url, api_key, timeout)
        self._loop = asyncio.new_event_loop()

    def _run_async(self, coro):
        """비동기 함수를 동기적으로 실행"""
        import asyncio

        try:
            return asyncio.run(coro)
        except RuntimeError:
            # 이미 실행 중인 이벤트 루프가 있는 경우
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures

                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, coro)
                    return future.result()
            return asyncio.run(coro)

    def health_check(self) -> Dict[str, Any]:
        return self._run_async(self._async_client.health_check())

    def get_signals(self, limit: int = 20) -> List[Signal]:
        return self._run_async(self._async_client.get_signals(limit))

    def get_market_gate(self) -> MarketGateStatus:
        return self._run_async(self._async_client.get_market_gate())

    def get_jongga_v2_latest(self) -> List[Signal]:
        return self._run_async(self._async_client.get_jongga_v2_latest())

    def get_dashboard_overview(self) -> Dict[str, Any]:
        return self._run_async(self._async_client.get_dashboard_overview())
