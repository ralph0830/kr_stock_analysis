# PART 04-2: LLMAnalyzer (뉴스 분석)

> **파일**: `engine/llm_analyzer.py`
> **용도**: Gemini API 기반 뉴스 감성 분석
> **의존**: google.generativeai, python-dotenv

---

## 개요

`LLMAnalyzer`는 Gemini AI를 사용하여 종목 뉴스를 분석하고 호재 점수(0~3)를 산출합니다.

---

## 클래스 구조

```python
"""
LLM 기반 뉴스 분석기 (Gemini)
"""

import os
import google.generativeai as genai
from typing import List, Dict
import asyncio
from datetime import datetime
from dotenv import load_dotenv

# 환경변수 로드 (.env)
load_dotenv()

class LLMAnalyzer:
    """Gemini를 이용한 뉴스 분석 및 점수 산출"""

    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            print("Warning: GOOGLE_API_KEY not found. LLM analysis will be skipped.")
            self.model = None
        else:
            genai.configure(api_key=self.api_key)
            # 모델명 환경변수에서 로드 (기본값: gemini-2.0-flash-exp)
            model_name = os.getenv("GEMINI_MODEL", "gemini-2.0-flash-exp")
            self.model = genai.GenerativeModel(model_name)
```

---

## 주요 메서드

### `analyze_news_sentiment()` - 뉴스 감성 분석

```python
async def analyze_news_sentiment(self, stock_name: str, news_items: List[Dict]) -> Dict:
    """
    뉴스 목록을 분석하여 호재 점수(0~3)와 요약 반환
    """
```

**파라미터:**
- `stock_name`: 종목명 (예: "삼성전자")
- `news_items`: 뉴스 목록
  ```python
  [
      {"title": "제목", "summary": "요약"},
      ...
  ]
  ```

**반환:**
```python
{
    "score": 2,      # 0~3점 (호재 강도)
    "reason": "종합적인 요약 이유"
}
```

---

## 점수 기준

| 점수 | 기준 | 예시 |
|-----|------|------|
| **3점** | 확실한 호재 | 대규모 수주, 상한가 재료, 어닝 서프라이즈, 경영권 분쟁 |
| **2점** | 긍정적 호재 | 실적 개선, 기대감, 테마 상승 |
| **1점** | 단순/중립적 | 일반적인 뉴스 |
| **0점** | 악재 또는 무호재 | 부정적 이슈, 별다른 호재 없음 |

---

## 프롬프트 구조

```python
prompt = f"""
    당신은 주식 투자 전문가입니다. 다음은 '{stock_name}' 종목에 대한 최신 뉴스들입니다.
    이 뉴스들을 **종합적으로 분석**하여 현재 시점에서의 호재 강도를 0~3점으로 평가하세요.

    [뉴스 목록]
    {news_text}

    [점수 기준]
    3점: 확실한 호재 (대규모 수주, 상한가 재료, 어닝 서프라이즈, 경영권 분쟁 등)
    2점: 긍정적 호재 (실적 개선, 기대감, 테마 상승)
    1점: 단순/중립적 소식
    0점: 악재 또는 별다른 호재 없음

    [출력 형식]
    뉴스 3개를 따로 평가하지 말고, **종목 전체에 대한 하나의 평가**를 내리세요.
    반드시 아래 포맷의 **단일 JSON 객체**로만 답하세요. (Markdown code block 없이)

    Format: {{"score": 2, "reason": "종합적인 요약 이유"}}
    """
```

---

## API 호출

```python
try:
    # 비동기 실행
    response = await asyncio.to_thread(
        self.model.generate_content,
        prompt,
        generation_config={"response_mime_type": "application/json"}
    )

    import json
    import re

    text = response.text.strip()

    # JSON 추출 (Markdown 코드블록 제거 및 정규식)
    if "```" in text:
        text = re.sub(r"```json|```", "", text).strip()

    # 중괄호로 시작하고 끝나는지 확인, 아니면 정규식으로 추출
    if not (text.startswith("{") and text.endswith("}")):
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            text = match.group()

    try:
        result = json.loads(text)
        return result
    except json.JSONDecodeError:
        print(f"[LLM Error] JSON Decode Failed. Raw text: {text[:100]}...")
        return {"score": 0, "reason": "JSON Parsing Failed"}

except Exception as e:
    print(f"[LLM Error] API Call Failed: {e}")
    return {"score": 0, "reason": f"Error: {str(e)}"}
```

---

## 환경 변수

```bash
# .env
GOOGLE_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-2.0-flash-exp  # 선택사항
```

---

## 사용 예시

```python
# SignalGenerator에서 사용
llm_result = None
if news_list and self.llm_analyzer.model:
    await asyncio.sleep(2)  # Rate Limit 방지

    print(f"    [LLM] Analyzing {stock.name} news...")
    news_dicts = [{"title": n.title, "summary": n.summary} for n in news_list]
    llm_result = await self.llm_analyzer.analyze_news_sentiment(stock.name, news_dicts)
    if llm_result:
       print(f"      -> Score: {llm_result.get('score')}, Reason: {llm_result.get('reason')}")
```

---

## 에러 핸들링

| 상황 | 처리 |
|-----|------|
| API Key 없음 | `model = None`, 분석 스킵 |
| API 호출 실패 | `{"score": 0, "reason": "Error: ..."}` |
| JSON 파싱 실패 | `{"score": 0, "reason": "JSON Parsing Failed"}` |
| 뉴스 없음 | `{"score": 0, "reason": "No LLM or No News"}` |

---

## 지원 모델

| 모델 | 설명 | 환경변수 값 |
|-----|------|-----------|
| Gemini 2.0 Flash Exp | 실험적 빠른 모델 | `gemini-2.0-flash-exp` (기본값) |
| Gemini 1.5 Flash | 안정적인 모델 | `gemini-1.5-flash` |
| Gemini 1.5 Pro | 고성능 모델 | `gemini-1.5-pro` |
