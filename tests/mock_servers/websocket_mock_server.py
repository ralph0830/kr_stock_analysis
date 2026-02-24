"""
Mock WebSocket Server
====================

실시간 데이터 전송용 Mock WebSocket 서버

주요 기능:
- 실시간 가격 데이터 시뮬레이션
- VCP 시그널 전송
- 종가베팅 시그널 전송
- SmartMoney 흐름 데이터 전송
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Set
import random
from fastapi import WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


class MockWebSocketServer:
    """
    Mock WebSocket 서버

    실시간 데이터 스트리밍 시뮬레이션
    """

    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
        self._broadcast_task = None
        self._running = False

    async def connect(self, websocket: WebSocket):
        """WebSocket 연결 수락"""
        await websocket.accept()
        self.active_connections.add(websocket)
        logger.info(f"WebSocket 연결됨. 현재 연결 수: {len(self.active_connections)}")

        # 연결 환영 메시지
        await self.send_personal_message({
            "type": "connected",
            "message": "WebSocket 연결 성공",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }, websocket)

    def disconnect(self, websocket: WebSocket):
        """WebSocket 연결 종료"""
        self.active_connections.discard(websocket)
        logger.info(f"WebSocket 연결 종료. 현재 연결 수: {len(self.active_connections)}")

    async def send_personal_message(self, message: Dict[str, Any], websocket: WebSocket):
        """특정 클라이언트에게 메시지 전송"""
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error(f"메시지 전송 실패: {e}")
            self.disconnect(websocket)

    async def broadcast(self, message: Dict[str, Any]):
        """모든 연결된 클라이언트에게 메시지 브로드캐스트"""
        if not self.active_connections:
            return

        disconnected = set()
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"브로드캐스트 실패: {e}")
                disconnected.add(connection)

        # 실패한 연결 제거
        for connection in disconnected:
            self.disconnect(connection)

    async def start_broadcasting(self, interval: float = 2.0):
        """
        실시간 데이터 브로드캐스트 시작

        Args:
            interval: 전송 간격 (초)
        """
        if self._running:
            logger.warning("이미 브로드캐스팅 중입니다")
            return

        self._running = True
        logger.info(f"실시간 데이터 브로드캐스트 시작 (간격: {interval}초)")

        while self._running:
            try:
                # 실시간 가격 데이터 브로드캐스트
                await self._broadcast_realtime_prices()

                # VCP 시그널 브로드캐스트 (10% 확률)
                if random.random() < 0.1:
                    await self._broadcast_vcp_signal()

                # 종가베팅 시그널 브로드캐스트 (10% 확률)
                if random.random() < 0.1:
                    await self._broadcast_closing_bet_signal()

                await asyncio.sleep(interval)

            except Exception as e:
                logger.error(f"브로드캐스트 에러: {e}")
                await asyncio.sleep(interval)

    def stop_broadcasting(self):
        """실시간 데이터 브로드캐스트 중지"""
        self._running = False
        logger.info("실시간 데이터 브로드캐스트 중지")

    async def _broadcast_realtime_prices(self):
        """실시간 가격 데이터 브로드캐스트"""
        # 테스트용 종목 리스트
        test_tickers = ["005930", "000660", "035420", "051910", "006400"]

        for ticker in test_tickers:
            price_data = {
                "type": "realtime_price",
                "data": self._generate_realtime_price(ticker),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            await self.broadcast(price_data)

    async def _broadcast_vcp_signal(self):
        """VCP 시그널 브로드캐스트"""
        signal_data = {
            "type": "vcp_signal",
            "data": self._generate_vcp_signal(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        await self.broadcast(signal_data)

    async def _broadcast_closing_bet_signal(self):
        """종가베팅 시그널 브로드캐스트"""
        signal_data = {
            "type": "closing_bet_signal",
            "data": self._generate_closing_bet_signal(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        await self.broadcast(signal_data)

    def _generate_realtime_price(self, ticker: str) -> Dict[str, Any]:
        """실시간 가격 데이터 생성"""
        base_prices = {
            "005930": 50000,  # 삼성전자
            "000660": 100000,  # SK하이닉스
            "035420": 200000,  # NAVER
            "051910": 300000,  # LG화학
            "006400": 400000,  # 삼성SDI
        }

        base_price = base_prices.get(ticker, 50000)
        price_change = random.randint(-500, 500)
        current_price = base_price + price_change

        return {
            "ticker": ticker,
            "name": self._get_stock_name(ticker),
            "price": current_price,
            "change": price_change,
            "change_rate": round((price_change / base_price) * 100, 2),
            "volume": random.randint(100000, 1000000),
            "bid_price": current_price - 100,
            "ask_price": current_price + 100,
        }

    def _generate_vcp_signal(self) -> Dict[str, Any]:
        """VCP 시그널 데이터 생성"""
        tickers = ["005930", "000660", "035420", "051910", "006400"]
        ticker = random.choice(tickers)

        return {
            "ticker": ticker,
            "name": self._get_stock_name(ticker),
            "pattern_type": random.choice(["VCP", "Tight", "Cup"]),
            "score": round(random.uniform(70, 95), 2),
            "current_price": random.randint(50000, 400000),
            "pivot_price": random.randint(50000, 400000),
            "volume_ratio": round(random.uniform(0.5, 2.0), 2),
            "rsi": round(random.uniform(30, 70), 2),
            "signal_strength": random.choice(["Strong", "Moderate", "Weak"]),
            "detected_at": datetime.now(timezone.utc).isoformat(),
        }

    def _generate_closing_bet_signal(self) -> Dict[str, Any]:
        """종가베팅 시그널 데이터 생성"""
        tickers = ["005930", "000660", "035420", "051910", "006400"]
        ticker = random.choice(tickers)

        return {
            "ticker": ticker,
            "name": self._get_stock_name(ticker),
            "score": random.randint(0, 12),
            "scores": {
                "price_position": random.randint(0, 2),
                "volume_surge": random.randint(0, 2),
                "smart_money_flow": random.randint(0, 2),
                "market_trend": random.randint(0, 2),
                "rsi_signal": random.randint(0, 2),
                "macd_signal": random.randint(0, 2),
                "bollinger_position": random.randint(0, 2),
                "support_resistance": random.randint(0, 2),
                "time_signal": random.randint(0, 2),
                "momentum": random.randint(0, 2),
            },
            "current_price": random.randint(50000, 400000),
            "target_price": random.randint(50000, 400000),
            "stop_loss": random.randint(40000, 300000),
            "signal_type": random.choice(["BUY", "HOLD", "SELL"]),
            "detected_at": datetime.now(timezone.utc).isoformat(),
        }

    def _get_stock_name(self, ticker: str) -> str:
        """종목코드로 종목명 반환"""
        names = {
            "005930": "삼성전자",
            "000660": "SK하이닉스",
            "035420": "NAVER",
            "051910": "LG화학",
            "006400": "삼성SDI",
        }
        return names.get(ticker, f"종목_{ticker}")


# FastAPI 앱에 WebSocket 라우트 추가를 위한 핸들러
async def websocket_endpoint(websocket: WebSocket, server: MockWebSocketServer):
    """WebSocket 엔드포인트 핸들러"""
    await server.connect(websocket)

    try:
        while True:
            # 클라이언트로부터 메시지 수신
            data = await websocket.receive_text()
            message = json.loads(data)

            logger.info(f"수신한 메시지: {message}")

            # 메시지 타입에 따른 응답
            if message.get("type") == "subscribe":
                # 구독 요청
                ticker = message.get("ticker")
                await server.send_personal_message({
                    "type": "subscribed",
                    "ticker": ticker,
                    "message": f"{ticker} 실시간 데이터 구독 시작",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }, websocket)

            elif message.get("type") == "unsubscribe":
                # 구독 취소
                ticker = message.get("ticker")
                await server.send_personal_message({
                    "type": "unsubscribed",
                    "ticker": ticker,
                    "message": f"{ticker} 실시간 데이터 구독 취소",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }, websocket)

            elif message.get("type") == "ping":
                # 핑퐥
                await server.send_personal_message({
                    "type": "pong",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }, websocket)

    except WebSocketDisconnect:
        server.disconnect(websocket)
        logger.info("WebSocket 연결 해제됨")
    except Exception as e:
        logger.error(f"WebSocket 에러: {e}")
        server.disconnect(websocket)


# 전역 서버 인스턴스
mock_ws_server = MockWebSocketServer()
