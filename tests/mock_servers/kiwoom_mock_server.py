"""
Mock Kiwoom REST API Server
==========================

테스트용 키움 증권 REST API Mock 서버

주요 기능:
- OAuth2 토큰 발급/갱신 시뮬레이션
- 현재가 조회 Mock
- 차트 데이터 Mock
- 종목 목록 Mock
- 일봉 데이터 Mock
"""

from fastapi import FastAPI, HTTPException, Header
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class TokenRequest(BaseModel):
    """토큰 발급 요청"""
    grant_type: str
    appkey: str
    secretkey: str
    refresh_token: Optional[str] = None


class CurrentPriceRequest(BaseModel):
    """현재가 조회 요청"""
    jsonrpc: str = "2.0"
    method: str = "t0414"
    params: Dict[str, Any] = {}
    id: int = 1


class ChartRequest(BaseModel):
    """차트 조회 요청"""
    dt: str
    stk_cd: str
    amt_qty_tp: str = "1"
    trde_tp: str = "0"
    unit_tp: str = "1000"


class StockListRequest(BaseModel):
    """종목 목록 요청"""
    mrkt_tp: str = "0"  # 0: KOSPI, 10: KOSDAQ


class DailyChartRequest(BaseModel):
    """일봉 차트 요청 (ka10081)"""
    stk_cd: str
    base_dt: str
    upd_stkpc_tp: str = "1"  # 수정주가구분
    inq_strt_dt: Optional[str] = None
    inq_end_dt: Optional[str] = None
    data_tp: str = "01"  # 데이터유형 (01:일봉)
    isu_cd_tp: Optional[str] = None  # 종목코드구분 (02:지수)


class IndexPriceRequest(BaseModel):
    """지수 조회 요청"""
    stk_cd: str  # KS11: KOSPI, KQ11: KOSDAQ


# Mock 데이터 생성 헬퍼
def generate_token() -> Dict[str, Any]:
    """Mock 액세스 토큰 생성"""
    expires_at = datetime.now() + timedelta(hours=23)
    return {
        "return_code": "0",
        "return_msg": "정상처리되었습니다",
        "token": "mock_access_token_" + datetime.now().strftime("%Y%m%d%H%M%S"),
        "token_type": "Bearer",
        "expires_in": 82800,
        "expires_dt": expires_at.strftime("%Y%m%d%H%M%S"),
    }


def generate_current_price(ticker: str) -> Dict[str, Any]:
    """Mock 현재가 데이터 생성"""
    import random
    base_price = 50000 + random.randint(-10000, 10000)

    return {
        "return_code": "0",
        "return_msg": "정상처리되었습니다",
        "result": {
            "t0414": [
                ticker,  # [0] 종목코드
                "삼성전자",  # [1] 종목명
                str(base_price),  # [2] 현재가
                str(random.randint(-500, 500)),  # [3] 전일대비
                f"{random.uniform(-2, 2):.2f}",  # [4] 등락율
                str(base_price - 100),  # [5] 매수호가
                str(base_price + 100),  # [6] 매도호가
                str(random.randint(100000, 1000000)),  # [7] 거래량
            ]
        },
    }


def generate_chart_data(ticker: str, date: str) -> Dict[str, Any]:
    """Mock 차트 데이터 생성"""
    import random

    chart_data = []
    for i in range(10):  # 10개 데이터 포인트
        chart_data.append({
            "dt": date,
            "cur_prc": str(50000 + random.randint(-5000, 5000)),
            "pred_pre": "+" + str(random.randint(0, 1000)) if random.random() > 0.5 else str(-random.randint(0, 1000)),
            "flu_rt": f"{random.uniform(-2, 2):.2f}",
            "trde_qty": str(random.randint(100000, 1000000)),
            "acc_trde_prica": str(random.randint(10000000, 100000000)),
            "ind_invsr": str(random.randint(-1000000, 1000000)),  # 개인
            "frgnr_invsr": str(random.randint(-1000000, 1000000)),  # 외국인
            "orgn": str(random.randint(-1000000, 1000000)),  # 기관
            "trst": "0",  # 수탁
            "pens": "0",  # 연기금
            "fin": "0",  # 금융투자
            "ins": "0",  # 보험
            "etc_fin": "0",  # 기타금융
        })

    return {
        "return_code": "0",
        "return_msg": "정상처리되었습니다",
        "stk_invsr_orgn_chart": chart_data,
        "cont-yn": "N",
        "next-key": "",
    }


def generate_stock_list(market: str = "0") -> Dict[str, Any]:
    """Mock 종목 목록 생성"""
    # 테스트용 종목 데이터
    mock_stocks = [
        {"code": "005930", "name": "삼성전자", "upName": "반도체", "marketCode": "0", "marketName": "KOSPI", "state": "01", "listCount": "1000000", "regDay": "19750611", "lastPrice": "50000"},
        {"code": "000660", "name": "SK하이닉스", "upName": "반도체", "marketCode": "0", "marketName": "KOSPI", "state": "01", "listCount": "500000", "regDay": "19880115", "lastPrice": "100000"},
        {"code": "035420", "name": "NAVER", "upName": "IT서비스", "marketCode": "0", "marketName": "KOSPI", "state": "01", "listCount": "300000", "regDay": "19950715", "lastPrice": "200000"},
        {"code": "051910", "name": "LG화학", "upName": "화학", "marketCode": "0", "marketName": "KOSPI", "state": "01", "listCount": "200000", "regDay": "19791025", "lastPrice": "300000"},
        {"code": "006400", "name": "삼성SDI", "upName": "전기배터리", "marketCode": "0", "marketName": "KOSPI", "state": "01", "listCount": "150000", "regDay": "19771001", "lastPrice": "400000"},
    ]

    # KOSDAQ 종목 추가
    if market == "10":
        mock_stocks.extend([
            {"code": "066570", "name": "엘아이지", "upName": "화학", "marketCode": "10", "marketName": "KOSDAQ", "state": "01", "listCount": "100000", "regDay": "20010101", "lastPrice": "100000"},
            {"code": "086520", "name": "에코프로비엠", "upName": "전기배터리", "marketCode": "10", "marketName": "KOSDAQ", "state": "01", "listCount": "80000", "regDay": "20100101", "lastPrice": "200000"},
        ])

    return {
        "return_code": "0",
        "return_msg": "정상처리되었습니다",
        "list": mock_stocks,
        "cont-yn": "N",
        "next-key": "",
    }


def generate_daily_chart(ticker: str, base_date: str, days: int = 60) -> Dict[str, Any]:
    """Mock 일봉 차트 데이터 생성 (ka10081)"""
    import random
    from datetime import datetime, timedelta

    chart_data = []
    base_price = 50000

    for i in range(days):
        date = (datetime.strptime(base_date, "%Y%m%d") - timedelta(days=days - i)).strftime("%Y%m%d")

        # 주말 제외
        weekday = datetime.strptime(date, "%Y%m%d").weekday()
        if weekday >= 5:  # 토=5, 일=6
            continue

        price_change = random.randint(-2000, 2000)
        open_price = base_price + random.randint(-500, 500)
        high_price = max(open_price, base_price) + random.randint(0, 500)
        low_price = min(open_price, base_price) - random.randint(0, 500)
        close_price = base_price + price_change

        chart_data.append({
            "dt": date,
            "open_pric": str(open_price),
            "high_pric": str(high_price),
            "low_pric": str(low_price),
            "cur_prc": str(close_price),
            "pred_pre": str(price_change),
            "pred_pre_sig": "+" if price_change >= 0 else "-",
            "trde_qty": str(random.randint(100000, 1000000)),
            "trde_prica": str(random.randint(10000000, 100000000)),
            "trde_tern_rt": f"{random.uniform(0.1, 5.0):.2f}",
        })

        base_price = close_price

    return {
        "return_code": "0",
        "return_msg": "정상처리되었습니다",
        "stk_dt_pole_chart_qry": chart_data,
    }


def generate_index_price(index_code: str) -> Dict[str, Any]:
    """Mock 지수 데이터 생성"""
    import random

    # 지수 기반 가격
    index_prices = {
        "KS11": 2500,  # KOSPI
        "KQ11": 800,   # KOSDAQ
    }

    base_price = index_prices.get(index_code, 1000)
    change = random.uniform(-20, 20)

    return {
        "return_code": "0",
        "return_msg": "정상처리되었습니다",
        "stk_cd": index_code,
        "stk_nm": "KOSPI" if index_code == "KS11" else "KOSDAQ",
        "cur_prc": f"{base_price + change:.2f}",
        "pred_pre": f"{change:+.2f}",
        "flu_rt": f"{(change / base_price * 100):+.2f}",
        "trde_qty": str(random.randint(100000000, 1000000000)),
    }


def generate_index_chart(index_code: str, days: int = 5) -> Dict[str, Any]:
    """Mock 지수 일봉 차트 데이터 생성"""
    import random
    from datetime import datetime, timedelta

    index_prices = {
        "KS11": 2500,
        "KQ11": 800,
    }

    base_price = index_prices.get(index_code, 1000)
    chart_data = []

    for i in range(days):
        date = (datetime.now() - timedelta(days=days - i)).strftime("%Y%m%d")

        # 주말 제외
        weekday = datetime.strptime(date, "%Y%m%d").weekday()
        if weekday >= 5:
            continue

        price_change = random.uniform(-30, 30)
        open_price = base_price + random.uniform(-10, 10)
        high_price = max(open_price, base_price) + random.uniform(0, 20)
        low_price = min(open_price, base_price) - random.uniform(0, 20)
        close_price = base_price + price_change

        chart_data.append({
            "dt": date,
            "opn_prc": f"{open_price:.2f}",
            "hgh_prc": f"{high_price:.2f}",
            "lw_prc": f"{low_price:.2f}",
            "cls_prc": f"{close_price:.2f}",
            "trde_qty": str(random.randint(100000000, 1000000000)),
        })

        base_price = close_price

    return {
        "return_code": "0",
        "return_msg": "정상처리되었습니다",
        "dtal_1": chart_data,
    }


# FastAPI 앱 생성
app = FastAPI(
    title="Mock Kiwoom REST API",
    description="키움 증권 REST API Mock 서버",
    version="1.0.0",
)


@app.get("/")
async def root():
    """헬스 체크"""
    return {
        "service": "Mock Kiwoom REST API",
        "status": "running",
        "timestamp": datetime.now().isoformat(),
    }


@app.post("/oauth2/token")
async def issue_token(request: TokenRequest):
    """OAuth2 토큰 발급 (키움 API 시뮬레이션)"""
    if request.grant_type == "client_credentials":
        # 토큰 발급
        return generate_token()
    elif request.grant_type == "refresh_token":
        # 토큰 갱신
        return generate_token()
    else:
        raise HTTPException(status_code=400, detail="Unsupported grant_type")


@app.post("/api/dostk/ka10001")
async def get_current_price(
    request: CurrentPriceRequest,
    authorization: str = Header(None),
    api_id: str = Header(None),
):
    """현재가 조회 (ka10001)"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Unauthorized")

    ticker = request.params.get("t0414InBlock", {}).get("shcode", "")
    if not ticker:
        raise HTTPException(status_code=400, detail="Invalid ticker")

    return generate_current_price(ticker)


@app.post("/api/dostk/chart")
async def get_chart(
    request: ChartRequest,
    authorization: str = Header(None),
    api_id: str = Header(None),
):
    """종목별투자자기관별차트 조회 (ka10060)"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Unauthorized")

    return generate_chart_data(request.stk_cd, request.dt)


@app.post("/api/dostk/stkinfo")
async def get_stock_info(
    request: StockListRequest,
    authorization: str = Header(None),
    api_id: str = Header(None),
):
    """종목정보 리스트 조회 (ka10099)"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Unauthorized")

    return generate_stock_list(request.mrkt_tp)


@app.post("/api/dostk/ka10081")
async def get_daily_chart(
    request: DailyChartRequest,
    authorization: str = Header(None),
    api_id: str = Header(None),
):
    """주식 일봉 차트 조회 (ka10081)"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Unauthorized")

    # 지수 차트 요청 확인
    if request.isu_cd_tp == "02":  # 지수
        return generate_index_chart(request.stk_cd)
    else:  # 주식
        return generate_daily_chart(request.stk_cd, request.base_dt)


@app.post("/api/dostk/stkinfo")
async def get_index_price(
    request: IndexPriceRequest,
    authorization: str = Header(None),
    api_id: str = Header(None),
):
    """지수 현재가 조회"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Unauthorized")

    return generate_index_price(request.stk_cd)


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """전역 예외 핸들러"""
    logger.error(f"Unexpected error: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "return_code": "-1",
            "return_msg": f"서버 에러: {str(exc)}",
        },
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5116)
