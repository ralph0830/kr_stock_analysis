# PART 06-2: KR Stock Chatbot Core

> **파일**: `chatbot/core.py`
> **용도**: VCP 기반 한국 주식 분석 챗봇 메인 클래스
> **의존**: memory, history, prompts, data_loader, Gemini API

---

## 개요

`KRStockChatbot`는 한국 주식 시장 분석을 위한 AI 챗봇입니다.

**주요 기능:**
- 장기 메모리: 사용자 프로필, 투자 성향 저장
- 대화 히스토리: 최근 10개 대화 컨텍스트 유지
- 시장 데이터 연동: 수급 점수, 섹터 점수, Market Gate
- Gemini AI 연동: 자연어 질의응답

---

## 클래스 구조

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KR Stock Chatbot Core - 메인 챗봇 클래스
Gemini AI 연동 및 대화 처리 로직
"""

import os
import logging
from typing import Optional, Callable, Dict, Any
from pathlib import Path
from datetime import datetime

# Load .env file
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent.parent.parent / ".env"
    load_dotenv(env_path)
except ImportError:
    pass

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

from memory import MemoryManager
from history import HistoryManager
from prompts import build_system_prompt, get_welcome_message, SYSTEM_PERSONA
from data_loader import fetch_all_data, search_stock, get_top_vcp_stocks

logger = logging.getLogger(__name__)

# 설정
GEMINI_MODEL = "gemini-3-flash-preview"
MAX_RETRIES = 3
```

---

## KRStockChatbot 클래스

```python
class KRStockChatbot:
    """
    VCP 기반 한국 주식 분석 챗봇

    Features:
    - 장기 메모리: 사용자 프로필, 투자 성향 저장
    - 대화 히스토리: 최근 10개 대화 컨텍스트 유지
    - 시장 데이터 연동: 수급 점수, 섹터 점수, Market Gate
    """

    def __init__(
        self,
        user_id: str,
        data_fetcher: Optional[Callable] = None,
        api_key: str = None
    ):
        """
        Args:
            user_id: 사용자 식별자
            data_fetcher: 시장 데이터 가져오는 함수 (외부 주입)
            api_key: Gemini API 키 (없으면 환경변수에서 로드)
        """
        self.user_id = user_id
        self.memory = MemoryManager(user_id)
        self.history = HistoryManager(user_id)
        self.data_fetcher = data_fetcher or fetch_all_data

        # Gemini 초기화
        self.api_key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY", "")
        self.model = None

        if GEMINI_AVAILABLE and self.api_key:
            try:
                genai.configure(api_key=self.api_key)
                self.model = genai.GenerativeModel(GEMINI_MODEL)
                logger.info(f"Gemini initialized for user: {user_id}")
            except Exception as e:
                logger.error(f"Gemini initialization failed: {e}")
        else:
            logger.warning("Gemini not available - using fallback responses")

        # 데이터 캐시 (30초 TTL)
        self._data_cache = None
        self._cache_timestamp = None
        self._cache_ttl = 30
```

---

## 주요 메서드

### 1. `_get_cached_data()` - 캐시된 시장 데이터

```python
def _get_cached_data(self) -> Dict[str, Any]:
    """캐시된 시장 데이터 반환 (30초 TTL)"""
    now = datetime.now()
    if (self._data_cache is None or
        self._cache_timestamp is None or
        (now - self._cache_timestamp).seconds > self._cache_ttl):

        try:
            self._data_cache = self.data_fetcher()
            self._cache_timestamp = now
        except Exception as e:
            logger.error(f"Data fetch error: {e}")
            self._data_cache = {"market": {}, "vcp_stocks": [], "sector_scores": {}}

    return self._data_cache
```

---

### 2. `chat()` - 메인 대화 함수

```python
def chat(self, user_message: str) -> str:
    """
    메인 대화 함수

    Args:
        user_message: 사용자 입력

    Returns:
        봇 응답
    """
    # 1. 명령어 체크
    if user_message.startswith("/"):
        return self._handle_command(user_message)

    # 2. 시장 데이터 가져오기
    data = self._get_cached_data()
    market_data = data.get("market", {})
    vcp_data = data.get("vcp_stocks", [])
    sector_scores = data.get("sector_scores", {})

    # 3. 특정 종목 질문인지 확인
    stock_context = self._detect_stock_query(user_message)

    # 4. 시스템 프롬프트 구성
    system_prompt = build_system_prompt(
        memory_text=self.memory.format_for_prompt(),
        market_data=market_data,
        vcp_data=vcp_data,
        sector_scores=sector_scores
    )

    # 종목별 컨텍스트 추가
    if stock_context:
        system_prompt += f"\n\n## 질문 대상 종목 상세\n{stock_context}"

    # 5. 대화 히스토리 가져오기
    chat_history = self.history.get_recent()

    # 6. Gemini 호출 (또는 폴백)
    if self.model:
        bot_response = self._call_gemini(system_prompt, user_message, chat_history)
    else:
        bot_response = self._fallback_response(user_message, vcp_data)

    # 7. 히스토리 저장
    self.history.add("user", user_message)
    self.history.add("model", bot_response)

    return bot_response
```

---

### 3. `_call_gemini()` - Gemini API 호출

```python
def _call_gemini(self, system_prompt: str, user_message: str, chat_history: list) -> str:
    """Gemini API 호출"""
    try:
        chat_session = self.model.start_chat(history=chat_history)

        # 시스템 프롬프트 + 사용자 메시지
        full_prompt = f"""[시스템 지시사항]
{system_prompt}

[사용자 질문]
{user_message}"""

        response = chat_session.send_message(full_prompt)
        return response.text

    except Exception as e:
        logger.error(f"Gemini API error: {e}")
        return f"⚠️ AI 응답 생성 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요."
```

---

### 4. `_fallback_response()` - 폴백 응답

```python
def _fallback_response(self, user_message: str, vcp_data: list) -> str:
    """Gemini 사용 불가 시 폴백 응답"""
    lower_msg = user_message.lower()

    # 추천 요청
    if any(kw in lower_msg for kw in ['뭐 살', '추천', '종목', 'top']):
        if vcp_data:
            response = "📊 **오늘의 수급 상위 종목**\n\n"
            for i, stock in enumerate(vcp_data[:5], 1):
                name = stock.get('name', 'N/A')
                score = stock.get('supply_demand_score', 0)
                double = " 🔥쌍끌이" if stock.get('is_double_buy') else ""
                response += f"{i}. **{name}**: {score}점{double}\n"
            return response
        return "현재 데이터를 불러올 수 없습니다."

    # 특정 종목 질문
    for stock in vcp_data:
        if stock.get('name', '') in user_message:
            return self._format_stock_info(stock)

    return "질문을 이해하지 못했습니다. \"오늘 뭐 살까?\" 또는 \"삼성전자 어때?\"와 같이 질문해주세요."
```

---

### 5. `_detect_stock_query()` - 종목 질문 감지

```python
def _detect_stock_query(self, message: str) -> Optional[str]:
    """종목 관련 질문 감지 및 상세 정보 반환"""
    data = self._get_cached_data()
    vcp_stocks = data.get("vcp_stocks", [])

    for stock in vcp_stocks:
        name = stock.get('name', '')
        ticker = stock.get('ticker', '')

        if name in message or ticker in message:
            return self._format_stock_info(stock)

    return None
```

---

### 6. `_format_stock_info()` - 종목 정보 포맷팅

```python
def _format_stock_info(self, stock: Dict) -> str:
    """종목 정보 포맷팅"""
    name = stock.get('name', 'N/A')
    ticker = stock.get('ticker', '')
    score = stock.get('supply_demand_score', 0)
    stage = stock.get('supply_demand_stage', '')
    double = "✅ 쌍끌이" if stock.get('is_double_buy') else ""

    foreign_5d = stock.get('foreign_5d', 0)
    inst_5d = stock.get('inst_5d', 0)

    return f"""
📊 **{name} ({ticker})**

- 수급 점수: {score}점 ({stage})
- 외국인 5일: {foreign_5d:+,}원
- 기관 5일: {inst_5d:+,}원
- {double}
    """.strip()
```

---

### 7. `_handle_command()` - 명령어 처리

```python
def _handle_command(self, command: str) -> str:
    """슬래시 명령어 처리"""
    if command == "/reset":
        self.history.clear()
        return "🔄 대화 기록이 초기화되었습니다."

    elif command == "/memory":
        return f"📝 저장된 메모:\n{self.memory.format_for_prompt()}"

    elif command == "/help":
        return """
🤖 **사용 가능한 명령어**

- `/reset`: 대화 기록 초기화
- `/memory`: 저장된 사용자 메모 확인
- `/help`: 도움말

**질문 예시:**
- "오늘 뭐 살까?"
- "삼성전자 어때?"
- "쌍끌이 종목 추천해줘"
        """.strip()

    else:
        return f"❌ 알 수 없는 명령어입니다: {command}"
```

---

## 의존 모듈

| 모듈 | 용도 |
|-----|------|
| `memory.MemoryManager` | 장기 메모리 관리 |
| `history.HistoryManager` | 대화 히스토리 관리 |
| `prompts.build_system_prompt` | 시스템 프롬프트 생성 |
| `data_loader.fetch_all_data` | 시장 데이터 수집 |
| `data_loader.search_stock` | 종목 검색 |
| `data_loader.get_top_vcp_stocks` | VCP 상위 종목 |

---

## 환경 변수

```bash
# .env
GEMINI_API_KEY=your_gemini_api_key_here
# 또는
GOOGLE_API_KEY=your_gemini_api_key_here
```

---

## 사용 예시

```python
# 챗봇 초기화
chatbot = KRStockChatbot(user_id="user123")

# 대화
response = chatbot.chat("오늘 뭐 살까?")
print(response)

# 종목 질문
response = chatbot.chat("삼성전자 어때?")
print(response)

# 명령어
response = chatbot.chat("/help")
print(response)
```

---

## Gemini 모델 설정

| 설정 | 값 | 설명 |
|-----|-----|------|
| `GEMINI_MODEL` | `"gemini-3-flash-preview"` | 사용할 모델명 |
| `MAX_RETRIES` | `3` | 최대 재시도 횟수 |

---

## 데이터 캐싱

- **TTL**: 30초
- **목적**: API 호출 최소화
- **캐시 내용**:
  - `market`: Market Gate 데이터
  - `vcp_stocks`: VCP 시그널 종목 목록
  - `sector_scores`: 섹터별 점수

---

## 로깅

```python
logger.info(f"Gemini initialized for user: {user_id}")
logger.error(f"Gemini initialization failed: {e}")
logger.error(f"Data fetch error: {e}")
logger.error(f"Gemini API error: {e}")
```
