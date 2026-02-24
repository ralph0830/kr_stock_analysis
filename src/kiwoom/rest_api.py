"""
키움 REST API 클라이언트 구현

OAuth2 인증 및 REST API 호출을 담당합니다.
"""

import os
import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

import httpx
from httpx import HTTPStatusError, RequestError

from src.kiwoom.base import KiwoomConfig, RealtimePrice


logger = logging.getLogger(__name__)


class KiwoomAPIError(Exception):
    """키움 API 에러"""

    def __init__(self, message: str, code: Optional[str] = None):
        self.message = message
        self.code = code
        super().__init__(message)


class TokenExpiredError(KiwoomAPIError):
    """토큰 만료 에러"""

    def __init__(self):
        super().__init__("Token expired or invalid")


@dataclass
class OrderResult:
    """주문 결과"""
    order_no: str          # 주문번호
    ticker: str            # 종목코드
    order_type: str        # 주문유형 (001:매수, 002:매도)
    price: str             # 체결가
    quantity: str          # 수량
    status: str            # 상태

    def to_dict(self) -> Dict[str, Any]:
        return {
            "order_no": self.order_no,
            "ticker": self.ticker,
            "order_type": self.order_type,
            "price": self.price,
            "quantity": self.quantity,
            "status": self.status,
        }


class KiwoomRestAPI:
    """
    키움 REST API 클라이언트

    OAuth2 인증 및 REST API 호출을 처리합니다.
    """

    # API 엔드포인트
    TOKEN_URL = "/oauth2/token"                    # 토큰 발급/갱신
    MARKET_CONDITION_URL = "/api/dostk/mrkcond"    # 시세조건검색 (ka10004 호가요청)
    STOCK_LIST_URL = "/api/dostk/stkinfo"          # 종목정보 리스트 조회 (ka10099)
    ORDER_URL = "/api/dostk/t1102"        # 주문
    BALANCE_URL = "/api/dostk/t0424"      # 잔고 조회
    DEPOSIT_URL = "/api/dostk/t0425"      # 예수금 조회
    CHART_URL = "/api/dostk/chart"        # 차트 조회 (ka10060 기관별, ka10081 일봉 등)

    # 주문 유형
    ORDER_BUY = "001"       # 매수
    ORDER_SELL = "002"      # 매도
    ORDER_MARKET = "01"     # 시장가
    ORDER_LIMIT = "00"      # 지정가

    # 계좌 정보 (환경변수 또는 설정)
    DEFAULT_ACCOUNT_NO: Optional[str] = None

    def __init__(self, config: KiwoomConfig):
        """
        초기화

        Args:
            config: 키움 API 설정
        """
        self._config = config
        self._access_token: Optional[str] = None
        self._refresh_token: Optional[str] = None
        self._token_expires_at: Optional[float] = None

        # HTTP 클라이언트
        self._client: Optional[httpx.AsyncClient] = None
        self._token_lock = asyncio.Lock()

        # 계좌번호
        self._account_no = os.getenv("KIWOOM_ACCOUNT_NO")

    @classmethod
    def from_env(cls) -> 'KiwoomRestAPI':
        """환경변수에서 설정 로드"""
        config = KiwoomConfig.from_env()
        return cls(config)

    def _set_client(self, client: httpx.AsyncClient) -> None:
        """HTTP 클라이언트 설정 (테스트용)"""
        self._client = client
        self._client_override = True  # 클라이언트가 수동 설정되었음을 표시

    async def _get_client(self) -> httpx.AsyncClient:
        """HTTP 클라이언트 가져오기 (lazy init)"""
        if self._client is None or self._client.is_closed:
            # 클라이언트가 수동으로 설정되지 않았을 때만 새로 생성
            if not hasattr(self, '_client_override'):
                self._client = httpx.AsyncClient(
                    base_url=self._config.base_url,
                    timeout=30.0,
                    headers={
                        "Content-Type": "application/json",
                    },
                )
        return self._client

    async def close(self) -> None:
        """연결 종료"""
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    # ==================== OAuth2 토큰 관리 ====================

    async def issue_token(self) -> bool:
        """
        토큰 발급 (Kiwoom OAuth2 client_credentials)

        참조: https://github.com/ralph0830/kiwoom_stock_telegram

        Returns:
            발급 성공 여부
        """
        try:
            client = await self._get_client()

            # 키움 OAuth2 토큰 발급 (실전 트레이딩)
            # grant_type: client_credentials
            # 파라미터: appkey, secretkey
            data = {
                "grant_type": "client_credentials",
                "appkey": self._config.app_key,
                "secretkey": self._config.secret_key,  # 키움은 secretkey 사용
            }

            response = await client.post(
                self.TOKEN_URL,
                json=data,
                headers={"Content-Type": "application/json;charset=UTF-8"},
            )

            response.raise_for_status()
            result = response.json()

            # 키움 API는 return_code로 성공/실패 확인
            # return_code: 0 = 성공, 그 외 = 실패
            return_code = result.get("return_code", -1)
            return_msg = result.get("return_msg", "")

            if return_code != 0:
                raise KiwoomAPIError(
                    f"Failed to get access token from response: {return_msg} [code:{return_code}]"
                )

            # 키움 API는 'token' 필드에 토큰 반환 (access_token이 아님!)
            access_token = result.get("token")

            if not access_token:
                raise KiwoomAPIError(
                    f"Token field not found in response: {result}"
                )

            self._access_token = access_token

            # 토큰 만료 시간 저장
            # 키움 API 응답 형식: expires_dt = "YYYYMMDDHHMMSS"
            expires_dt_str = result.get('expires_dt')
            if expires_dt_str:
                try:
                    # 키움 API 응답 형식: YYYYMMDDHHMMSS
                    token_expiry = datetime.strptime(expires_dt_str, "%Y%m%d%H%M%S")
                    self._token_expires_at = token_expiry.timestamp()
                    logger.info(f"Token expires at: {expires_dt_str}")
                except ValueError:
                    logger.warning(f"Failed to parse token expiry: {expires_dt_str}, using default (23 hours)")
                    self._token_expires_at = (
                        datetime.now(timezone.utc) + timedelta(hours=23)
                    ).timestamp()
            else:
                logger.warning("No token expiry in response, using default (23 hours)")
                self._token_expires_at = (
                    datetime.now(timezone.utc) + timedelta(hours=23)
                ).timestamp()

            logger.info("Kiwoom token issued successfully")
            return True

        except HTTPStatusError as e:
            logger.error(f"Token issue failed: {e.response.status_code}")
            raise KiwoomAPIError(
                f"Token issue failed: {e.response.status_code}",
                code=str(e.response.status_code),
            ) from e
        except Exception as e:
            logger.error(f"Token issue error: {e}")
            raise KiwoomAPIError(f"Token issue error: {e}") from e

    async def refresh_token(self) -> bool:
        """
        토큰 갱신 (Kiwoom OAuth2)

        Returns:
            갱신 성공 여부
        """
        if not self._refresh_token:
            raise KiwoomAPIError("No refresh token available")

        try:
            client = await self._get_client()

            data = {
                "grant_type": "refresh_token",
                "appkey": self._config.app_key,
                "secretkey": self._config.secret_key,  # 키움은 secretkey 사용
                "refresh_token": self._refresh_token,
            }

            response = await client.post(
                self.TOKEN_URL,
                json=data,
                headers={"Content-Type": "application/json;charset=UTF-8"},
            )

            response.raise_for_status()
            result = response.json()

            self._access_token = result.get("access_token")
            if "refresh_token" in result:
                self._refresh_token = result["refresh_token"]
            expires_in = result.get("expires_in", 3600)

            self._token_expires_at = (
                datetime.now(timezone.utc) + timedelta(seconds=expires_in - 300)
            ).timestamp()

            logger.info("Token refreshed successfully")
            return True

        except HTTPStatusError as e:
            logger.error(f"Token refresh failed: {e.response.status_code}")
            raise KiwoomAPIError(
                f"Token refresh failed: {e.response.status_code}",
                code=str(e.response.status_code),
            ) from e
        except Exception as e:
            logger.error(f"Token refresh error: {e}")
            raise KiwoomAPIError(f"Token refresh error: {e}") from e

    def is_token_valid(self) -> bool:
        """
        토큰 유효성 확인

        Returns:
            유효한 토큰 보유 여부
        """
        if not self._access_token or not self._token_expires_at:
            return False

        # 5분 이내 만료는 유효하지 않은 것으로 처리
        now = datetime.now(timezone.utc).timestamp()
        return now < self._token_expires_at

    def is_token_expiring_soon(self, seconds: int = 300) -> bool:
        """
        토큰 곧 만료 여부 확인

        Args:
            seconds: 만료 임계 시간 (초)

        Returns:
            곧 만료되는지 여부
        """
        if not self._token_expires_at:
            return True

        now = datetime.now(timezone.utc).timestamp()
        return (self._token_expires_at - now) < seconds

    async def ensure_token_valid(self) -> None:
        """
        유효한 토큰 보장

        토큰이 없거나 만료되었으면 갱신합니다.
        """
        async with self._token_lock:
            if not self.is_token_valid():
                if self._refresh_token:
                    await self.refresh_token()
                else:
                    await self.issue_token()

    async def reauthenticate(self) -> bool:
        """
        재인증 (토큰 재발급)

        Returns:
            재인증 성공 여부
        """
        try:
            self._access_token = None
            self._refresh_token = None
            self._token_expires_at = None
            return await self.issue_token()
        except Exception as e:
            logger.error(f"Reauthentication failed: {e}")
            return False

    # ==================== API 호출 헬퍼 ====================

    async def _request_with_auth(
        self,
        method: str,
        url: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        retry_count: int = 2,
    ) -> Dict[str, Any]:
        """
        인증이 포함된 API 요청

        Args:
            method: HTTP 메서드
            url: 요청 URL
            data: 요청 본문
            params: 쿼리 파라미터
            retry_count: 재시도 횟수

        Returns:
            응답 데이터
        """
        await self.ensure_token_valid()

        client = await self._get_client()
        headers = {
            "Authorization": f"Bearer {self._access_token}",
        }

        last_error = None

        for attempt in range(retry_count + 1):
            try:
                response = await client.request(
                    method,
                    url,
                    json=data,
                    params=params,
                    headers=headers,
                )

                # 401 에러 시 토큰 갱신 후 재시도
                if response.status_code == 401 and attempt < retry_count:
                    await self.refresh_token()
                    headers["Authorization"] = f"Bearer {self._access_token}"
                    continue

                response.raise_for_status()
                return response.json()

            except HTTPStatusError as e:
                last_error = e
                if e.response.status_code == 401:
                    # 토큰 만료 - 재시도
                    continue
                elif e.response.status_code >= 500:
                    # 서버 에러 - 재시도
                    if attempt < retry_count:
                        await asyncio.sleep(0.5 * (attempt + 1))
                        continue
                raise
            except RequestError as e:
                last_error = e
                # 네트워크 에러 - 재시도
                if attempt < retry_count:
                    await asyncio.sleep(0.5 * (attempt + 1))
                    continue
                raise KiwoomAPIError(f"Network error: {e}") from e

        raise KiwoomAPIError(f"Request failed after {retry_count} retries") from last_error

    # ==================== 현재가/호가 조회 ====================

    async def get_current_price(self, ticker: str) -> Optional[RealtimePrice]:
        """
        현재가 조회 (ka10004 주식호가요청)

        키움 OpenAPI 가이드에 따르면 ka10001(현재가 조회) API는 REST로 제공되지 않음.
        대신 ka10004(주식호가요청) API를 사용하여 호가 정보를 조회.

        Args:
            ticker: 종목코드 (6자리)

        Returns:
            현재가 정보 또는 None (호가 기반 추정)
        """
        try:
            # 토큰 유효성 확인
            await self.ensure_token_valid()

            client = await self._get_client()

            # 키움 API 요청 (POST /api/dostk/mrkcond)
            # 헤더에 api-id 포함 (필수!)
            headers = {
                "Authorization": f"Bearer {self._access_token}",
                "api-id": "ka10004",  # 주식호가요청 API ID
                "Content-Type": "application/json;charset=UTF-8",
            }

            # 요청 바디
            request_body = {
                "stk_cd": ticker,
            }

            response = await client.post(
                self.MARKET_CONDITION_URL,
                json=request_body,
                headers=headers,
            )

            response.raise_for_status()
            result = response.json()

            # return_code 확인
            return_code = result.get("return_code", -1)
            if return_code != 0:
                logger.warning(f"Current price API returned code {return_code}: {result.get('return_msg')}")
                return None

            # 응답 파싱 (ka10004 응답 필드)
            # buy_fpr_bid: 매수최우선호가, sel_fpr_bid: 매도최우선호가
            buy_price = result.get("buy_fpr_bid", "0")
            sell_price = result.get("sel_fpr_bid", "0")
            buy_qty = result.get("buy_fpr_req", "0")
            sell_qty = result.get("sel_fpr_req", "0")

            # 문자열에서 +/- 제거 후 숫자로 변환
            def parse_price(price_str: str) -> float:
                """가격 문자열 파싱 (+/- 제거)"""
                if not price_str or price_str == "0":
                    return 0.0
                return float(str(price_str).replace("+", "").replace("-", "").replace(",", ""))

            buy_price_val = parse_price(buy_price)
            sell_price_val = parse_price(sell_price)

            # 현재가 추정: 매수호가와 매도호가의 중간값 또는 매수호가 사용
            # 장 종료 후에는 매수호가=0, 매도호가=0일 수 있음
            if buy_price_val == 0 and sell_price_val == 0:
                logger.warning(f"No price data available for {ticker} (market closed)")
                return None

            # 현재가 = 매수최우선호가 (일반적으로 체결 가능한 가격)
            current_price = buy_price_val if buy_price_val > 0 else sell_price_val

            return RealtimePrice(
                ticker=ticker,
                price=current_price,
                change=0.0,  # ka10004에서는 전일대비 제공 안 함
                change_rate=0.0,  # ka10004에서는 등락률 제공 안 함
                volume=0,  # ka10004에서는 거래량 제공 안 함
                bid_price=buy_price_val,
                ask_price=sell_price_val,
                timestamp=datetime.now(timezone.utc).isoformat(),
            )

        except HTTPStatusError as e:
            logger.error(f"Get current price failed: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Get current price error: {e}")
            return None

    # ==================== 차트 데이터 조회 ====================

    async def get_investor_chart(
        self,
        ticker: str,
        date: str,
        amt_qty_tp: str = "1",  # 1:금액, 2:수량
        trde_tp: str = "0",     # 0:순매수, 1:매수, 2:매도
        unit_tp: str = "1000",  # 1000:천주, 1:단주
        cont_yn: str = "N",
        next_key: str = "",
    ) -> Optional[Dict[str, Any]]:
        """
        종목별투자자기관별차트 조회 (ka10060)

        Args:
            ticker: 종목코드 (6자리)
            date: 조회일자 (YYYYMMDD)
            amt_qty_tp: 금액/수량 구분 (1:금액, 2:수량)
            trde_tp: 거래구분 (0:순매수, 1:매수, 2:매도)
            unit_tp: 단위구분 (1000:천주, 1:단주)
            cont_yn: 연속조회여부 (Y:연속, N:최초)
            next_key: 연속조회키

        Returns:
            차트 데이터 딕셔너리
        """
        try:
            # 토큰 유효성 확인 및 발급
            await self.ensure_token_valid()

            client = await self._get_client()

            # 키움 차트 API 요청 (POST /api/dostk/chart)
            # 헤더에 api-id, cont-yn, next-key 포함
            headers = {
                "Authorization": f"Bearer {self._access_token}",
                "api-id": "ka10060",
                "Content-Type": "application/json;charset=UTF-8",
            }

            if cont_yn == "Y" and next_key:
                headers["cont-yn"] = "Y"
                headers["next-key"] = next_key

            # 요청 바디
            request_body = {
                "dt": date,
                "stk_cd": ticker,
                "amt_qty_tp": amt_qty_tp,
                "trde_tp": trde_tp,
                "unit_tp": unit_tp,
            }

            response = await client.post(
                self.CHART_URL,
                json=request_body,
                headers=headers,
            )

            response.raise_for_status()
            result = response.json()

            # return_code 확인
            return_code = result.get("return_code", -1)
            if return_code != 0:
                logger.warning(f"Chart API returned non-zero code: {return_code}, msg: {result.get('return_msg')}")
                return None

            # 응답 데이터 파싱
            chart_data = result.get("stk_invsr_orgn_chart", [])

            return {
                "ticker": ticker,
                "date": date,
                "data": chart_data,
                "cont_yn": result.get("cont-yn", "N"),
                "next_key": result.get("next-key", ""),
            }

        except HTTPStatusError as e:
            # Rate Limiting (429) 처리 - 재시도 로직
            if e.response.status_code == 429:
                logger.warning("Rate limited, retrying after 2 seconds...")
                await asyncio.sleep(2)
                # 한 번 더 재시도
                try:
                    client = await self._get_client()
                    response = await client.post(
                        self.CHART_URL,
                        json=request_body,
                        headers=headers,
                    )
                    response.raise_for_status()
                    result = response.json()

                    return_code = result.get("return_code", -1)
                    if return_code != 0:
                        logger.warning(f"Chart API returned non-zero code: {return_code}, msg: {result.get('return_msg')}")
                        return None

                    chart_data = result.get("stk_invsr_orgn_chart", [])
                    return {
                        "ticker": ticker,
                        "date": date,
                        "data": chart_data,
                        "cont_yn": result.get("cont-yn", "N"),
                        "next_key": result.get("next-key", ""),
                    }
                except Exception as retry_error:
                    logger.error(f"Retry failed: {retry_error}")
                    return None
            logger.error(f"Get investor chart failed: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Get investor chart error: {e}")
            return None

    async def get_daily_prices(
        self,
        ticker: str,
        days: int = 30,
    ) -> Optional[List[Dict[str, Any]]]:
        """
        일별 가격 데이터 조회 (차트용)

        여러 날짜의 차트 데이터를 조회하여 가격 데이터를 반환합니다.

        Args:
            ticker: 종목코드 (6자리)
            days: 조회 일수

        Returns:
            일별 가격 데이터 리스트
        """
        from datetime import datetime, timedelta
        import asyncio

        try:
            # 토큰 유효성 확인 및 발급
            await self.ensure_token_valid()

            price_data = []

            # 최근 days일간 데이터 수집 (오늘부터 과거 순으로)
            # i=0: 오늘, i=1: 어제, ..., i=days-1: days-1일 전
            for i in range(days):
                date = datetime.now() - timedelta(days=i)
                date_str = date.strftime("%Y%m%d")

                # 주말 제외 (월~금만 조회)
                weekday = date.weekday()
                if weekday >= 5:  # 토=5, 일=6
                    continue

                chart_result = await self.get_investor_chart(
                    ticker=ticker,
                    date=date_str,
                )

                # Rate Limiting 방지를 위해 요청 간 0.1초 지연
                await asyncio.sleep(0.1)

                # 데이터가 없고 최근 날짜면 조회 중단 (아직 데이터 없음)
                if not chart_result or not chart_result.get("data"):
                    if i < 5:  # 최근 5일 내 데이터가 없으면 중단
                        logger.info(f"No data available for {date_str}, stopping fetch")
                        break
                    else:
                        continue

                if chart_result and chart_result.get("data"):
                    for item in chart_result["data"]:
                        # 요청한 날짜의 데이터만 필터링
                        item_date = item.get("dt", "")
                        if item_date != date_str:
                            continue
                        # 데이터 파싱
                        # pred_pre: 전일대비 (부호 포함, 예: +9500, -3000)
                        # "+" 제거만 하고 "-"는 유지하여 음수값 정상 처리
                        pred_pre_val = item.get("pred_pre", "0").replace("+", "")
                        price_data.append({
                            "date": item.get("dt", date_str),
                            "price": int(item.get("cur_prc", "0").replace("+", "").replace("-", "")),
                            "change": int(pred_pre_val),
                            "volume": int(item.get("acc_trde_prica", "0")),
                            # 투자자별 수급
                            "individual": int(item.get("ind_invsr", "0")),  # 개인
                            "foreign": int(item.get("frgnr_invsr", "0")),    # 외국인
                            "institution": int(item.get("orgn", "0")),       # 기관
                            "trust": int(item.get("trst", "0")),             # 수탁
                            "pension": int(item.get("pens", "0")),           # 연기금
                            "financial": int(item.get("fin", "0")),          # 금융투자
                            "insurance": int(item.get("ins", "0")),          # 보험
                            "etc_finance": int(item.get("etc_fin", "0")),    # 기타금융
                        })

            return price_data if price_data else None

        except Exception as e:
            logger.error(f"Get daily prices error: {e}")
            return None

    # ==================== 주문 관련 ====================

    async def _place_order(
        self,
        ticker: str,
        order_type: str,  # 001:매수, 002:매도
        price_type: str,  # 00:지정가, 01:시장가
        quantity: int,
        price: Optional[int] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        주문 전송 (t1102)

        Args:
            ticker: 종목코드
            order_type: 주문유형 (001:매수, 002:매도)
            price_type: 가격유형 (00:지정가, 01:시장가)
            quantity: 수량
            price: 주문가격 (지정가인 경우)

        Returns:
            주문 결과
        """
        if not self._account_no:
            # 테스트를 위해 기본 계좌번호 사용
            self._account_no = "12345678"

        try:
            request_data = {
                "jsonrpc": "2.0",
                "method": "t1102",
                "params": {
                    "t1102InBlock": {
                        "ptno_cd": self._account_no,   # 계좌번호
                        "scts": "0",                    # 주식구분 (0:주식)
                        "prct_type": price_type,       # 00:지정가, 01:시장가
                        "ord_qty": str(quantity),      # 주문수량
                        "ord_dv_sn": "0",              # 주문구분
                        "ft_acnt_yn": "0",             # 신용거래여부
                        "loan_dt": "",                 # 대출일
                        "org_ord_no": "",              # 원주문번호
                        "mvng_prce": str(price) if price else "0",  # 이동가격
                    }
                },
                "id": 1,
            }

            response = await self._request_with_auth("POST", self.ORDER_URL, data=request_data)

            # 응답 파싱
            result = response.get("result", {})
            t1102 = result.get("t1102", [])

            if not t1102:
                return None

            return {
                "order_no": t1102[1] if len(t1102) > 1 else "",
                "ticker": t1102[2] if len(t1102) > 2 else "",
                "order_type": t1102[3] if len(t1102) > 3 else "",
                "price": t1102[4] if len(t1102) > 4 else "",
                "quantity": t1102[5] if len(t1102) > 5 else "",
                "status": t1102[0] if len(t1102) > 0 else "",
            }

        except KiwoomAPIError as e:
            logger.error(f"Place order failed: {e}")
            return None
        except Exception as e:
            logger.error(f"Place order error: {e}")
            return None

    async def order_buy_market(self, ticker: str, quantity: int) -> Optional[Dict[str, Any]]:
        """시장가 매수 주문"""
        return await self._place_order(
            ticker=ticker,
            order_type=self.ORDER_BUY,
            price_type=self.ORDER_MARKET,
            quantity=quantity,
        )

    async def order_sell_market(self, ticker: str, quantity: int) -> Optional[Dict[str, Any]]:
        """시장가 매도 주문"""
        return await self._place_order(
            ticker=ticker,
            order_type=self.ORDER_SELL,
            price_type=self.ORDER_MARKET,
            quantity=quantity,
        )

    async def order_buy_limit(self, ticker: str, price: int, quantity: int) -> Optional[Dict[str, Any]]:
        """지정가 매수 주문"""
        return await self._place_order(
            ticker=ticker,
            order_type=self.ORDER_BUY,
            price_type=self.ORDER_LIMIT,
            quantity=quantity,
            price=price,
        )

    async def order_sell_limit(self, ticker: str, price: int, quantity: int) -> Optional[Dict[str, Any]]:
        """지정가 매도 주문"""
        return await self._place_order(
            ticker=ticker,
            order_type=self.ORDER_SELL,
            price_type=self.ORDER_LIMIT,
            quantity=quantity,
            price=price,
        )

    # ==================== 계좌 조회 ====================

    async def get_account_balance(self) -> Optional[List[Dict[str, Any]]]:
        """
        계좌 잔고 조회 (t0424)

        Returns:
            잔고 리스트
        """
        if not self._account_no:
            # 테스트를 위해 기본 계좌번호 사용
            self._account_no = "12345678"

        try:
            request_data = {
                "jsonrpc": "2.0",
                "method": "t0424",
                "params": {
                    "t0424InBlock": {
                        "ptno_cd": self._account_no,  # 계좌번호
                        "asset_gb": "0",               # 자산구분 (0:전체)
                        "scts": "0",                   # 주식구분 (0:주식)
                        "chek_gubun": "0",            # 조회구분 (0:전체)
                    }
                },
                "id": 1,
            }

            response = await self._request_with_auth("POST", self.BALANCE_URL, data=request_data)

            # 응답 파싱
            result = response.get("result", {})
            t0424 = result.get("t0424", [])

            if not t0424:
                return []

            # 리스트 형태로 변환
            balances = []
            for item in t0424:
                balances.append({
                    "ticker": item[0] if len(item) > 0 else "",
                    "name": item[1] if len(item) > 1 else "",
                    "quantity": item[2] if len(item) > 2 else "0",
                    "avg_price": item[3] if len(item) > 3 else "0",
                    "current_price": item[4] if len(item) > 4 else "0",
                    "pl": item[5] if len(item) > 5 else "0",
                    "pl_rate": item[6] if len(item) > 6 else "0",
                })

            return balances

        except KiwoomAPIError as e:
            logger.error(f"Get account balance failed: {e}")
            return None
        except Exception as e:
            logger.error(f"Get account balance error: {e}")
            return None

    async def get_account_deposit(self) -> Optional[Dict[str, Any]]:
        """
        예수금 조회 (t0425)

        Returns:
            예수금 정보
        """
        if not self._account_no:
            # 테스트를 위해 기본 계좌번호 사용
            self._account_no = "12345678"

        try:
            request_data = {
                "jsonrpc": "2.0",
                "method": "t0425",
                "params": {
                    "t0425InBlock": {
                        "ptno_cd": self._account_no,  # 계좌번호
                    }
                },
                "id": 1,
            }

            response = await self._request_with_auth("POST", self.DEPOSIT_URL, data=request_data)

            # 응답 파싱
            result = response.get("result", {})
            t0425 = result.get("t0425", [])

            if not t0425:
                return None

            return {
                "total_deposit": t0425[0] if len(t0425) > 0 else "0",
                "withdrawable": t0425[1] if len(t0425) > 1 else "0",
                "orderable": t0425[2] if len(t0425) > 2 else "0",
                "margin": t0425[3] if len(t0425) > 3 else "0",
            }

        except KiwoomAPIError as e:
            logger.error(f"Get account deposit failed: {e}")
            return None
        except Exception as e:
            logger.error(f"Get account deposit error: {e}")
            return None

    # ==================== 연결 관리 ====================

    async def connect(self) -> bool:
        """
        API 연결 (토큰 발급)

        Returns:
            연결 성공 여부
        """
        try:
            await self.issue_token()
            return True
        except Exception as e:
            logger.error(f"Connect failed: {e}")
            return False

    async def disconnect(self) -> None:
        """연결 해제"""
        self._access_token = None
        self._refresh_token = None
        self._token_expires_at = None
        await self.close()

    def is_connected(self) -> bool:
        """연결 상태 확인"""
        return self.is_token_valid()

    def has_valid_token(self) -> bool:
        """유효한 토큰 보유 여부"""
        return self.is_token_valid()

    # ==================== 지수 데이터 조회 ====================

    # 지수 종목코드
    KOSPI_INDEX_CODE = "KS11"   # KOSPI 지수 코드
    KOSDAQ_INDEX_CODE = "KQ11"  # KOSDAQ 지수 코드

    async def get_index_price(self, index_code: str) -> Optional[Dict[str, Any]]:
        """
        지수 현재가 조회 (KOSPI/KOSDAQ)

        kiwoom REST API는 지수 전용 API가 없으며,
        주식기본정보(ka10001) API를 사용하여 지수 정보를 조회합니다.

        Args:
            index_code: 지수 코드 ("KS11": KOSPI, "KQ11": KOSDAQ)

        Returns:
            지수 정보 딕셔너리 {"price": float, "change": float, "change_pct": float}
        """
        try:
            await self.ensure_token_valid()

            client = await self._get_client()

            # 주식기본정보 API (ka10001)
            # 엔드포인트: /api/dostk/stkinfo
            headers = {
                "Authorization": f"Bearer {self._access_token}",
                "api-id": "ka10001",
                "Content-Type": "application/json;charset=UTF-8",
                "cont-yn": "N",  # 연속조회여부 (N: 처음, Y: 다음)
                "next-key": "",  # 연속조회키
            }

            # 요청 파라미터 (단순 POST)
            request_data = {
                "stk_cd": index_code,  # 지수 코드 (KS11: KOSPI, KQ11: KOSDAQ)
            }

            # 전체 URL 사용
            url = f"{self._config.base_url}/api/dostk/stkinfo"
            logger.info(f"Fetching index price from: {url} with code: {index_code}")

            response = await client.post(
                url,
                json=request_data,
                headers=headers,
            )

            response.raise_for_status()
            result = response.json()

            # 디버깅: 응답의 핵심 필드만 로깅
            cur_prc = result.get("cur_prc", "")
            logger.info(f"Index API response for {index_code}: return_code={result.get('return_code')}, cur_prc=[{cur_prc}], stk_cd=[{result.get('stk_cd')}]")

            # return_code 확인
            return_code = result.get("return_code", -1)
            if return_code != 0:
                logger.warning(f"Index price API returned code {return_code}: {result.get('return_msg')}")
                return None

            # 응답 파싱 (ka10001 응답 구조 - 데이터가 바로 최상위 레벨에 있음)
            cur_prc = result.get("cur_prc", "")
            if not cur_prc or cur_prc == "":
                logger.warning(f"No current price in response for {index_code}")
                return None

            return {
                "code": result.get("stk_cd", index_code),
                "name": result.get("stk_nm", ""),
                "price": float(cur_prc),
                "change": float(result.get("pred_pre", "0").replace("+", "")),  # 전일대비
                "change_pct": float(result.get("flu_rt", "0").replace("+", "")),  # 등락율 (%)
                "volume": int(result.get("trde_qty", "0") or 0),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

        except HTTPStatusError as e:
            logger.error(f"Get index price failed: {e.response.status_code}, response: {e.response.text}")
            return None
        except Exception as e:
            logger.error(f"Get index price error: {e}")
            return None

    async def get_stock_daily_chart(
        self,
        ticker: str,
        days: int = 60,
        base_date: Optional[str] = None,
        adjusted_price: bool = True,
    ) -> Optional[List[Dict[str, Any]]]:
        """
        주식 일봉 차트 조회 (ka10081)

        kiwoom REST API ka10081 주식일봉차트조회를 사용하여 주식 일봉 데이터를 조회합니다.

        Args:
            ticker: 종목코드 (6자리)
            days: 조회 일수 (기본 60일)
            base_date: 기준일자 (YYYYMMDD, None이면 오늘)
            adjusted_price: 수정주가 사용 여부 (True: 수정주가, False: 미수정)

        Returns:
            일봉 차트 데이터 리스트 [{"date": "YYYYMMDD", "open": float, "high": float, ...}]
        """
        try:
            await self.ensure_token_valid()

            client = await self._get_client()

            # 기준일자 설정
            from datetime import datetime, timedelta

            if base_date is None:
                base_date = datetime.now().strftime("%Y%m%d")

            # 요청 파라미터 (주식용 - isu_cd_tp 없음)
            request_data = {
                "stk_cd": ticker,           # 종목코드
                "base_dt": base_date,        # 기준일자 (YYYYMMDD)
                "upd_stkpc_tp": "1" if adjusted_price else "0",  # 수정주가구분 (0:미수정, 1:수정주가)
            }

            # 헤더 설정
            headers = {
                "Authorization": f"Bearer {self._access_token}",
                "api-id": "ka10081",
                "Content-Type": "application/json;charset=UTF-8",
                "cont-yn": "N",
                "next-key": "",
            }

            # ka10081 엔드포인트
            url = f"{self._config.base_url}/api/dostk/chart"
            logger.info(f"Fetching stock chart from: {url} with ticker: {ticker}, base_dt: {base_date}")

            response = await client.post(
                url,
                json=request_data,
                headers=headers,
            )

            response.raise_for_status()
            result = response.json()

            logger.info(f"Stock chart API response for {ticker}: return_code={result.get('return_code')}")

            # return_code 확인
            return_code = result.get("return_code", -1)
            if return_code != 0:
                logger.warning(f"Stock chart API returned code {return_code}: {result.get('return_msg')}")
                return None

            # 응답 파싱 (stk_dt_pole_chart_qry 배열에 일봉 데이터)
            chart_data = result.get("stk_dt_pole_chart_qry", [])
            if not chart_data:
                logger.warning(f"No chart data in response for {ticker}")
                return []

            # 변환된 데이터 반환
            parsed_data = []
            for item in chart_data:
                parsed_data.append({
                    "date": item.get("dt", ""),                # 날짜 (YYYYMMDD)
                    "open": float(item.get("open_pric", "0") or "0"),   # 시가
                    "high": float(item.get("high_pric", "0") or "0"),   # 고가
                    "low": float(item.get("low_pric", "0") or "0"),    # 저가
                    "close": float(item.get("cur_prc", "0") or "0"),    # 종가
                    "volume": int(item.get("trde_qty", "0") or "0"),   # 거래량
                    "value": int(item.get("trde_prica", "0") or "0"),  # 거래대금
                    "change": int(item.get("pred_pre", "0") or "0"),   # 전일대비
                    "change_sign": item.get("pred_pre_sig", ""),      # 전일대비기호
                    "turnover_rate": float(item.get("trde_tern_rt", "0") or "0"),  # 거래회전율
                })

            logger.info(f"Retrieved {len(parsed_data)} stock chart data points for {ticker}")

            # days 만큼만 반환 (최근 데이터부터)
            if len(parsed_data) > days:
                parsed_data = parsed_data[-days:]

            return parsed_data

        except HTTPStatusError as e:
            logger.error(f"Get stock chart failed: {e.response.status_code}, response: {e.response.text}")
            return None
        except Exception as e:
            logger.error(f"Get stock chart error: {e}")
            return None

    async def get_index_daily_chart(
        self,
        index_code: str,
        days: int = 5,
    ) -> Optional[List[Dict[str, Any]]]:
        """
        지수 일봉 차트 조회 (ka10081)

        ka10081 주식일봉차트조회 API를 사용하여 지수 차트 데이터를 조회합니다.

        Args:
            index_code: 지수 코드 ("KS11": KOSPI, "KQ11": KOSDAQ)
            days: 조회 일수

        Returns:
            일봉 차트 데이터 리스트 [{"date": "YYYYMMDD", "open": float, "high": float, ...}]
        """
        try:
            await self.ensure_token_valid()

            client = await self._get_client()

            # 기본 날짜 범위 계산 (영업일 기준)
            from datetime import datetime, timedelta

            end_date = datetime.now()
            start_date = end_date - timedelta(days=days * 2)  # 주말 고려하여 여유있게

            # 주식일봉차트조회 API (ka10081)
            headers = {
                "Authorization": f"Bearer {self._access_token}",
                "api-id": "ka10081",
                "Content-Type": "application/json;charset=UTF-8",
            }

            # 요청 파라미터
            request_data = {
                "stk_cd": index_code,  # 지수 코드
                "inq_strt_dt": start_date.strftime("%Y%m%d"),  # 조회시작일
                "inq_end_dt": end_date.strftime("%Y%m%d"),      # 조회종료일
                "data_tp": "01",  # 데이터유형 (01:일봉, 02:주봉, 03:월봉)
                "isu_cd_tp": "02",  # 종목코드구분 (02: 지수)
                "cont_yn": "N",
                "next_key": "",
            }

            # ka10081 전용 엔드포인트
            url = f"{self._config.base_url}/api/dostk/ka10081"
            logger.info(f"Fetching index chart from: {url} with code: {index_code}")

            response = await client.post(
                url,
                json=request_data,
                headers=headers,
            )

            response.raise_for_status()
            result = response.json()

            logger.info(f"Index chart API response for {index_code}: return_code={result.get('return_code')}")

            # return_code 확인
            return_code = result.get("return_code", -1)
            if return_code != 0:
                logger.warning(f"Index chart API returned code {return_code}: {result.get('return_msg')}")
                return None

            # 응답 파싱 (ka10081 응답 구조 - dtal_1 배열에 차트 데이터)
            chart_data = result.get("dtal_1", [])
            if not chart_data:
                logger.warning(f"No chart data in response for {index_code}")
                return None

            # 변환된 데이터 반환
            parsed_data = []
            for item in chart_data:
                parsed_data.append({
                    "date": item.get("dt", ""),           # 날짜 (YYYYMMDD)
                    "open": float(item.get("opn_prc", "0") or "0"),
                    "high": float(item.get("hgh_prc", "0") or "0"),
                    "low": float(item.get("lw_prc", "0") or "0"),
                    "close": float(item.get("cls_prc", "0") or "0"),
                    "volume": int(item.get("trde_qty", "0") or "0"),
                })

            logger.info(f"Retrieved {len(parsed_data)} index chart data points for {index_code}")
            return parsed_data

        except HTTPStatusError as e:
            logger.error(f"Get index chart failed: {e.response.status_code}, response: {e.response.text}")
            return None
        except Exception as e:
            logger.error(f"Get index chart error: {e}")
            return None

    async def get_index_price_from_chart(self, index_code: str) -> Optional[Dict[str, Any]]:
        """
        차트 데이터에서 최신 지수 가격 추출

        ka10081 일봉 차트 데이터를 조회하여 가장 최신의 지수 정보를 반환합니다.

        Args:
            index_code: 지수 코드 ("KS11": KOSPI, "KQ11": KOSDAQ)

        Returns:
            지수 정보 딕셔너리 {"code": str, "name": str, "price": float, "change_pct": float}
        """
        try:
            # 최근 5일 차트 데이터 조회
            chart_data = await self.get_index_daily_chart(index_code, days=5)

            if not chart_data or len(chart_data) == 0:
                logger.warning(f"No chart data available for {index_code}")
                return None

            # 가장 최근 데이터 (마지막 요소)
            latest = chart_data[-1]
            previous = chart_data[-2] if len(chart_data) >= 2 else None

            close_price = latest.get("close", 0)
            if close_price == 0:
                logger.warning(f"Invalid close price for {index_code}: {close_price}")
                return None

            # 전일대비 등락률 계산
            change_pct = 0.0
            if previous and previous.get("close", 0) > 0:
                prev_close = previous["close"]
                change_pct = ((close_price - prev_close) / prev_close) * 100

            # 지수명 매핑
            index_names = {
                "KS11": "KOSPI",
                "KQ11": "KOSDAQ",
            }

            return {
                "code": index_code,
                "name": index_names.get(index_code, index_code),
                "price": close_price,
                "change": close_price - (previous.get("close", 0) if previous else close_price),
                "change_pct": round(change_pct, 2),
                "date": latest.get("date", ""),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

        except Exception as e:
            logger.error(f"Get index price from chart error: {e}")
            return None

    # ==================== 종목 정보 조회 ====================

    async def get_stock_list(
        self,
        market: str = "ALL",
    ) -> List[Dict[str, Any]]:
        """
        종목정보 리스트 조회 (ka10099 TR)

        키움증권 REST API의 ka10099 TR을 사용하여 종목 목록을 조회합니다.

        Args:
            market: 시장 구분 ("KOSPI": 코스피, "KOSDAQ": 코스닥, "ALL": 전체)

        Returns:
            종목 정보 리스트 [{"code": str, "name": str, "market": str, ...}, ...]

        예시:
            api = KiwoomRestAPI.from_env()
            kospi_stocks = await api.get_stock_list("KOSPI")
            kosdaq_stocks = await api.get_stock_list("KOSDAQ")
            all_stocks = await api.get_stock_list("ALL")
        """
        all_stocks = []

        # 조회할 시장 목록
        markets = []
        if market == "KOSPI":
            markets = [("0", "KOSPI")]
        elif market == "KOSDAQ":
            markets = [("10", "KOSDAQ")]
        else:  # ALL
            markets = [("0", "KOSPI"), ("10", "KOSDAQ")]

        try:
            await self.ensure_token_valid()
            client = await self._get_client()

            for mrkt_tp_code, market_name in markets:
                cont_yn = "N"
                next_key = ""

                while True:
                    # 요청 헤더
                    headers = {
                        "Authorization": f"Bearer {self._access_token}",
                        "api-id": "ka10099",
                        "Content-Type": "application/json;charset=UTF-8",
                        "cont-yn": cont_yn,
                    }
                    if next_key:
                        headers["next-key"] = next_key

                    # 요청 바디
                    request_data = {
                        "mrkt_tp": mrkt_tp_code,  # 0: KOSPI, 10: KOSDAQ
                    }

                    # 전체 URL
                    url = f"{self._config.base_url}{self.STOCK_LIST_URL}"

                    try:
                        response = await client.post(
                            url,
                            json=request_data,
                            headers=headers,
                            timeout=30.0,
                        )

                        response.raise_for_status()
                        result = response.json()

                        # return_code 확인
                        return_code = result.get("return_code", -1)
                        if return_code != 0:
                            logger.warning(
                                f"Stock list API returned code {return_code} for {market_name}: {result.get('return_msg')}"
                            )
                            break

                        # 응답 파싱 - list 배열에 종목 정보
                        stock_list = result.get("list", [])
                        if not stock_list:
                            logger.info(f"No stocks returned for {market_name}")
                            break

                        # 종목 정보 변환
                        for item in stock_list:
                            code = item.get("code", "")
                            name = item.get("name", "")
                            if not code:
                                continue

                            # 스팩(SPAC) 종목 확인: upName 또는 companyClassName에 '스팩' 포함
                            up_name = item.get("upName", "")  # 업종명
                            company_class_name = item.get("companyClassName", "")  # 회사분류명
                            market_name_field = item.get("marketName", "")  # 시장명

                            is_spac = "스팩" in up_name or "스팩" in company_class_name

                            # 회사채/채권 종목 확인: name, upName 또는 marketName에 채권 관련 키워드 포함
                            bond_keywords = ["회사채", "채권", "금융채", "은행채", "국채", "지방채", "특수채", "파생채"]
                            is_bond = any(keyword in name for keyword in bond_keywords)
                            is_bond = is_bond or any(keyword in up_name for keyword in bond_keywords)
                            is_bond = is_bond or any(keyword in market_name_field for keyword in bond_keywords)

                            # 제외할 ETF/ETN 패턴 확인
                            # ETF 제공자: TIGER, SOL, ACE, KIWOOM, KODEX, TREF, 1Q, etc.
                            excluded_prefixes = ["TIGER ", "SOL ", "ACE ", "KIWOOM ", "KODEX ", "TREF ", "KOACT ", "ARIRANG ", "HANARO ", "KB ", "TIME ", "PLUS ", "RISE ", "SOURCE ", "MAJOR ", "스팩", "1Q ", "마이티 ", "KODEX ", "메리츠"]
                            is_excluded_etf = any(name.startswith(prefix) for prefix in excluded_prefixes)

                            # 특정 키워드 포함: ETN, 인버스, TOP10, 레버리지, ETF
                            excluded_keywords = ["ETN", "인버스", "TOP10", "TOP5", "TOP3", "레버리지", "리츠", "ETF", "액티브", "크레딧"]
                            is_excluded_etf = is_excluded_etf or any(keyword in name for keyword in excluded_keywords)

                            all_stocks.append({
                                "ticker": code.zfill(6),  # 6자리 종목코드
                                "name": name,
                                "market": market_name,
                                "list_count": item.get("listCount"),  # 상장주식수
                                "reg_day": item.get("regDay"),  # 상장일
                                "last_price": item.get("lastPrice"),  # 전일종가
                                "state": item.get("state"),  # 종목상태
                                "market_code": item.get("marketCode"),  # 시장구분코드
                                "market_name": market_name_field,  # 시장명
                                "up_name": up_name,  # 업종명 (스팩/채권 확인용)
                                "company_class_name": company_class_name,  # 회사분류명 (스팩 확인용)
                                "is_spac": is_spac,  # 스팩 종목 여부
                                "is_bond": is_bond,  # 회사채/채권 종목 여부
                                "is_excluded_etf": is_excluded_etf,  # 제외할 ETF/ETN 여부
                            })

                        logger.info(f"조회된 {market_name} 종목: {len(stock_list)}개")

                        # 연속조회 확인
                        cont_yn = result.get("cont-yn", "N")
                        next_key = result.get("next-key", "")

                        if cont_yn != "Y":
                            break

                    except HTTPStatusError as e:
                        if e.response.status_code == 429:
                            # Rate Limiting - 대기 후 재시도
                            logger.warning(f"Rate limited, waiting 2 seconds before retry...")
                            await asyncio.sleep(2)
                            continue
                        raise
                    except Exception as e:
                        logger.error(f"Error fetching stock list for {market_name}: {e}")
                        break

                    # 연속조회 간 딜레이 (Rate Limiting 방지)
                    if cont_yn == "Y":
                        await asyncio.sleep(0.2)

            logger.info(f"종목 목록 조회 완료: 총 {len(all_stocks)}개 종목")
            return all_stocks

        except Exception as e:
            logger.error(f"Get stock list error: {e}")
            return []

    # ==================== 일별거래상세 조회 (ka10015) ====================

    async def get_daily_trade_detail(
        self,
        ticker: str,
        start_date: Optional[str] = None,
    ) -> Optional[List[Dict[str, Any]]]:
        """
        일별거래상세 조회 (ka10015)

        외국인/기관 순매수 데이터 조회를 위한 API입니다.

        Args:
            ticker: 종목코드 (6자리)
            start_date: 시작일 (YYYYMMDD, None이면 30일 전)

        Returns:
            일별거래상세 데이터 리스트
            - for_netprps: 외국인 순매수
            - orgn_netprps: 기관 순매수
            - trde_qty: 거래량
        """
        try:
            await self.ensure_token_valid()

            client = await self._get_client()

            # 시작일 설정 (기본 30일 전)
            from datetime import datetime, timedelta

            if start_date is None:
                start_date = (datetime.now() - timedelta(days=30)).strftime("%Y%m%d")

            # 요청 파라미터
            request_data = {
                "stk_cd": ticker,
                "strt_dt": start_date,
            }

            # 헤더 설정
            headers = {
                "Authorization": f"Bearer {self._access_token}",
                "api-id": "ka10015",
                "Content-Type": "application/json;charset=UTF-8",
            }

            # ka10015 엔드포인트
            url = f"{self._config.base_url}/api/dostk/stkinfo"

            response = await client.post(
                url,
                json=request_data,
                headers=headers,
            )

            response.raise_for_status()
            result = response.json()

            # return_code 확인
            return_code = result.get("return_code", -1)
            if return_code != 0:
                logger.warning(f"Daily trade detail API returned code {return_code}: {result.get('return_msg')}")
                return None

            # 응답 파싱 (daly_trde_dtl 배열에 일별거래상세 데이터)
            trade_data = result.get("daly_trde_dtl", [])
            if not trade_data:
                logger.warning(f"No trade detail data in response for {ticker}")
                return []

            # 변환된 데이터 반환
            parsed_data = []
            for item in trade_data:
                parsed_data.append({
                    "date": item.get("dt", ""),                # 날짜 (YYYYMMDD)
                    "close_price": int(item.get("close_pric", "0") or "0"),  # 종가
                    "volume": int(item.get("trde_qty", "0") or "0"),        # 거래량
                    "foreign_net_buy": int(item.get("for_netprps", "0") or "0"),  # 외국인 순매수
                    "inst_net_buy": int(item.get("orgn_netprps", "0") or "0"),    # 기관 순매수
                })

            logger.info(f"Retrieved {len(parsed_data)} daily trade detail records for {ticker}")

            return parsed_data

        except HTTPStatusError as e:
            logger.error(f"Get daily trade detail failed: {e.response.status_code}, response: {e.response.text}")
            return None
        except Exception as e:
            logger.error(f"Get daily trade detail error: {e}")
            return None

    # ==================== 업종일봉 조회 (ka20006) ====================

    async def get_sector_daily_chart(
        self,
        sector_code: str,
        base_date: Optional[str] = None,
        days: int = 20,
    ) -> Optional[List[Dict[str, Any]]]:
        """
        업종 일봉 차트 조회 (ka20006)

        섹터 모멘텀 계산을 위한 업종 지수 데이터 조회

        Args:
            sector_code: 업종코드 (예: "001" - 코스피 종합)
            base_date: 기준일자 (YYYYMMDD, None이면 오늘)
            days: 조회 일수

        Returns:
            업종 일봉 데이터 리스트
            - cur_prc: 현재 지수
            - strt_pric: 시작 지수
            - high_pric: 고가 지수
            - low_pric: 저가 지수
        """
        try:
            await self.ensure_token_valid()

            client = await self._get_client()

            # 기준일자 설정
            from datetime import datetime

            if base_date is None:
                base_date = datetime.now().strftime("%Y%m%d")

            # 요청 파라미터
            request_data = {
                "inds_cd": sector_code,
                "base_dt": base_date,
            }

            # 헤더 설정
            headers = {
                "Authorization": f"Bearer {self._access_token}",
                "api-id": "ka20006",
                "Content-Type": "application/json;charset=UTF-8",
            }

            # ka20006 엔드포인트
            url = f"{self._config.base_url}/api/dostk/chart"

            response = await client.post(
                url,
                json=request_data,
                headers=headers,
            )

            response.raise_for_status()
            result = response.json()

            # return_code 확인
            return_code = result.get("return_code", -1)
            if return_code != 0:
                logger.warning(f"Sector chart API returned code {return_code}: {result.get('return_msg')}")
                return None

            # 응답 파싱 (inds_dt_pole_qry 배열에 업종일봉 데이터)
            chart_data = result.get("inds_dt_pole_qry", [])
            if not chart_data:
                logger.warning(f"No sector chart data in response for {sector_code}")
                return []

            # 변환된 데이터 반환
            parsed_data = []
            for item in chart_data:
                parsed_data.append({
                    "date": item.get("dt", ""),                # 날짜 (YYYYMMDD)
                    "open": float(item.get("strt_pric", "0") or "0"),   # 시작 지수
                    "high": float(item.get("high_pric", "0") or "0"),   # 고가 지수
                    "low": float(item.get("low_pric", "0") or "0"),    # 저가 지수
                    "close": float(item.get("cur_prc", "0") or "0"),    # 현재 지수
                    "volume": int(item.get("trde_qty", "0") or "0"),    # 거래량
                })

            logger.info(f"Retrieved {len(parsed_data)} sector chart data points for {sector_code}")

            # days 만큼만 반환 (최근 데이터부터)
            if len(parsed_data) > days:
                parsed_data = parsed_data[-days:]

            return parsed_data

        except HTTPStatusError as e:
            logger.error(f"Get sector chart failed: {e.response.status_code}, response: {e.response.text}")
            return None
        except Exception as e:
            logger.error(f"Get sector chart error: {e}")
            return None

    # ==================== 거래정지 종목 필터링 ====================

    # 거래정지 상태 키워드
    TRADING_SUSPENDED_KEYWORDS = [
        "관리종목",
        "증거금100%",
        "투자유의환기종목",
        "정리매매",
        "거래정지",
        "시장주의",
        "불매가",
        "매매거부",
    ]

    @staticmethod
    def is_trading_suspended(state: str) -> bool:
        """
        종목 상태가 거래정지인지 확인

        Args:
            state: 종목 상태 문자열

        Returns:
            거래정지 여부
        """
        if not state:
            return False
        return any(keyword in state for keyword in KiwoomRestAPI.TRADING_SUSPENDED_KEYWORDS)

    async def get_suspended_stocks(
        self,
        market: str = "ALL"
    ) -> Dict[str, str]:
        """
        거래정지 종목 목록 조회

        Args:
            market: 시장 구분 ("KOSPI", "KOSDAQ", "ALL")

        Returns:
            {종목코드: 종목상태} 딕셔너리
        """
        all_stocks = await self.get_stock_list(market)

        suspended = {}
        for stock in all_stocks:
            state = stock.get("state", "")
            if self.is_trading_suspended(state):
                ticker = stock.get("ticker", "")
                if ticker:
                    suspended[ticker] = state

        logger.info(f"거래정지 종목 {len(suspended)}개 확인됨: {list(suspended.keys())}")
        return suspended
