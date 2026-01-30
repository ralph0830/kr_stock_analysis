"""
Chatbot Prompts
RAG 프롬프트 템플릿
"""

from typing import List, Dict, Any, Optional


# ============================================================================
# System Prompts
# ============================================================================

CHATBOT_SYSTEM_PROMPT = """
당신은 "Ralph Stock"이라는 한국 주식 분석 시스템의 AI 어시스턴트입니다.

## 역할
- 한국 주식 시장에 대한 전문적인 분석과 조언 제공
- VCP (Volatility Contraction Pattern) 패턴 분석
- 종가베팅 V2 시그널 해석
- SmartMoney 수급 분석

## 제공 정보
- 종목 기본 정보 (티커, 이름, 시장, 섹터)
- VCP/종가베팅 시그널 (점수, 등급)
- Market Gate 상태 (GREEN/YELLOW/RED)
- AI 감성 분석 결과
- **뉴스 링크 (news_urls)**: 참고한 뉴스 기사의 URL

## 응답 원칙
1. 객관적 사실 기반 전달
2. 투자 위험 고지 필수 ("이 정보는 참고용이며 투자 손실에 책임지지 않습니다")
3. 이해하기 쉬운 용어 사용
4. 근거 기반 추천

## 뉴스 링크 필수 포함 (중요!)
- 뉴스 분석 시 **반드시 뉴스 기사 링크**를 포함해야 합니다
- 제공된 news_urls 리스트에서 각 뉴스의 제목과 URL을 마크다운 링크 형식으로 표시
- 형식: `[{제목}]({URL})`
- 링크가 없더라도 "관련 뉴스" 섹션에 뉴스 요약은 포함해야 함

## 제한 사항
- 재무 상담, 세무 조언 불가
- 미래 가격 보장 불가
- 투자 결정 대행 불가
"""

RECOMMENDATION_SYSTEM_PROMPT = """
## 종목 추천 가이드라인

### VCP 패턴
- 볼린저밴드 수축 후 돌파 예상
- 진입: 수축 기간 저점 부근
- 목표가: 직전 고가 + 10~20%

### 종가베팅 V2
- 12점 scoring 기반
- S등급(10점+): 15% 비중
- A등급(8점+): 12% 비중
- B등급(6점+): 10% 비중
- C등급(<6점): 관망

### SmartMoney
- 외국인 40%, 기관 30% 가중
- 순매수 전환 시 매수 강도 ↑

### 리스크 관리
- 분산 투자: 5~10종목
- 손절가: -5% 기준
- 익절가: +10~15% 분할 매도
"""

MARKET_ANALYSIS_SYSTEM_PROMPT = """
## Market Gate 해석

### GREEN (레벨 60~100)
- 전체 매수 권장
- 섹터별 순매수 종목 집중
- 신규 진입 적기

### YELLOW (레벨 40~60)
- 관망 + 일부 매수
- 우량 종목만 선별
- 신규 진입 자제

### RED (레벨 0~40)
- 현금 비중 확대
- 손실 종목 정리
- 신규 진입 보류
"""


# ============================================================================
# RAG Prompt Builder
# ============================================================================

def build_rag_prompt(
    user_message: str,
    context: Dict[str, Any],
    conversation_history: Optional[List[Dict]] = None
) -> str:
    """
    RAG 기반 프롬프트 생성

    Args:
        user_message: 사용자 메시지
        context: 검색된 컨텍스트
        conversation_history: 대화 기록 (선택)

    Returns:
        LLM에 전달할 프롬프트
    """
    parts = [CHATBOT_SYSTEM_PROMPT]

    # 대화 기록 추가 (최근 3개)
    if conversation_history and len(conversation_history) > 0:
        parts.append("\n## 대화 기록")
        recent_history = conversation_history[-6:]  # 최근 3턴 (6개 메시지)
        for msg in reversed(recent_history):  # 오래된 순서로
            role = "사용자" if msg["role"] == "user" else "어시스턴트"
            parts.append(f"{role}: {msg['content']}")

    # 컨텍스트 추가
    if context.get("stocks"):
        parts.append("\n## 관련 종목")
        for stock in context["stocks"][:3]:
            # 실시간 가격 정보가 있으면 포함
            price_info = ""
            if stock.get("realtime_price"):
                rp = stock["realtime_price"]
                price = rp.get('price')
                change = rp.get('change', 0)
                change_rate = rp.get('change_rate', 0)
                change_str = f"+{change:,}" if change > 0 else f"{change:,}"
                rate_str = f"+{change_rate:.2f}%" if change_rate > 0 else f"{change_rate:.2f}%"
                price_info = f" | 현재가: {price:,}원 ({change_str}, {rate_str})"
            elif stock.get("ticker"):
                price_info = f" | 티커: {stock['ticker']}"

            parts.append(f"- {stock['name']}({stock['ticker']}): {stock['market']} {stock.get('sector', '')}{price_info}")

    if context.get("signals"):
        parts.append("\n## 시그널 정보")
        for signal in context["signals"][:5]:
            parts.append(
                f"- {signal['ticker']} {signal['signal_type']} "
                f"({signal['grade']}등급, {signal['score']}점)"
            )

    if context.get("market_status"):
        status = context["market_status"]
        parts.append("\n## Market Gate 상태")
        parts.append(f"- 현재: {status['status']} (레벨 {status['level']})")
        parts.append(f"- KOSPI: {status['kospi_status']}")
        parts.append(f"- KOSDAQ: {status['kosdaq_status']}")

    if context.get("news"):
        parts.append("\n## 최신 뉴스/분석")
        for news in context["news"][:3]:
            summary = news.get('summary', '분석 내용')[:100]
            parts.append(f"- {summary}...")

            # 뉴스 링크 추가
            news_urls = news.get('news_urls', [])
            if news_urls:
                parts.append("  📰 참고 뉴스:")
                for url_info in news_urls[:3]:  # 최대 3개 링크
                    title = url_info.get('title', '뉴스')
                    url = url_info.get('url', '')
                    if url:
                        parts.append(f"    - [{title}]({url})")
                    else:
                        parts.append(f"    - {title}")

    # 사용자 질문
    parts.append(f"\n## 사용자 질문\n{user_message}")

    return "\n".join(parts)


def build_recommendation_prompt(
    stocks: List[Dict[str, Any]],
    signals: List[Dict[str, Any]]
) -> str:
    """
    종목 추천용 프롬프트 생성

    Args:
        stocks: 종목 리스트
        signals: 시그널 리스트

    Returns:
        추천 프롬프트
    """
    parts = [RECOMMENDATION_SYSTEM_PROMPT]

    parts.append("\n## 추천 종목")

    for i, stock in enumerate(stocks[:5], 1):
        # 해당 종목 시그널 찾기
        stock_signals = [s for s in signals if s["ticker"] == stock["ticker"]]
        signal_info = ""
        if stock_signals:
            sig = stock_signals[0]
            signal_info = f" ({sig['signal_type']} {sig['grade']}등급 {sig['score']}점)"

        parts.append(f"{i}. {stock['name']}({stock['ticker']}){signal_info}")

    return "\n".join(parts)


def build_market_analysis_prompt(market_status: Dict[str, Any]) -> str:
    """
    시장 분석용 프롬프트 생성

    Args:
        market_status: Market Gate 상태

    Returns:
        시장 분석 프롬프트
    """
    parts = [MARKET_ANALYSIS_SYSTEM_PROMPT]

    parts.append("\n## 현재 Market Gate 상태")
    parts.append(f"- 상태: {market_status['status']}")
    parts.append(f"- 레벨: {market_status['level']}")
    parts.append(f"- KOSPI: {market_status['kospi_status']}")
    parts.append(f"- KOSDAQ: {market_status['kosdaq_status']}")

    if market_status.get("updated_at"):
        parts.append(f"- 기준일: {market_status['updated_at']}")

    return "\n".join(parts)


# ============================================================================
# Response Formatting
# ============================================================================

def format_suggestions(context_type: str) -> List[str]:
    """
    컨텍스트 타입별 추천 질문 생성

    Args:
        context_type: 질문 유형

    Returns:
        추천 질문 리스트
    """
    suggestions_map = {
        "market": [
            "KOSPI 현황",
            "급등 종목",
            "외국인 수급",
        ],
        "recommendation": [
            "VCP 시그널 종목",
            "종가베팅 S등급",
            "추천 종목 더보기",
        ],
        "stock": [
            "재무제표",
            "최신 뉴스",
            "기술적 분석",
        ],
    }

    return suggestions_map.get(context_type, [
        "오늘의 추천종목",
        "Market Gate 상태",
        "VCP 시그널 확인",
    ])
