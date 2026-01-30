/**
 * Chatbot Widget Component
 * AI 기반 주식 챗봇 위젯
 */

"use client";

import { useState, useRef, useEffect } from "react";
import apiClient from "@/lib/api-client";
import { type IChatMessage, type IChatResponse } from "@/types";
import { useTypingAnimation } from "@/hooks/useTypingAnimation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

// Props 인터페이스
interface IChatbotWidgetProps {
  initialMessage?: string;
  onStockClick?: (ticker: string) => void;
}

export function ChatbotWidget({ initialMessage, onStockClick }: IChatbotWidgetProps) {
  // 상태 관리
  const [messages, setMessages] = useState<IChatMessage[]>([
    {
      role: "assistant",
      content: "안녕하세요! 한국 주식 AI 챗봇입니다. 주식 관련 질문을 해주세요.\n\n예시:\n- 삼성전자 현재가 알려줘\n- VCP 시그널 있는 종목 추천해줘\n- 오늘 시장 상태 어때?",
      timestamp: new Date().toISOString(),
    },
  ]);
  const [inputValue, setInputValue] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [sessionId] = useState(() => `session-${Date.now()}`);
  const typingDots = useTypingAnimation({ interval: 300 });

  // 스크롤 참조
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // 자동 스크롤
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // 초기 메시지 처리
  useEffect(() => {
    if (initialMessage) {
      handleSendMessage(initialMessage);
    }
  }, []);

  // 메시지 전송 핸들러
  const handleSendMessage = async (message: string) => {
    if (!message.trim() || isLoading) return;

    // 사용자 메시지 추가
    const userMessage: IChatMessage = {
      role: "user",
      content: message,
      timestamp: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, userMessage]);
    setInputValue("");
    setIsLoading(true);

    try {
      // API 호출
      const response: IChatResponse = await apiClient.chat({
        message,
        session_id: sessionId,
      });

      // 어시스턴트 메시지 추가
      const assistantMessage: IChatMessage = {
        role: "assistant",
        content: response.reply,
        timestamp: response.timestamp,
      };
      setMessages((prev) => [...prev, assistantMessage]);

      // 제안이 있으면 표시
      if (response.suggestions && response.suggestions.length > 0) {
        // 제안 버튼을 표시하기 위한 상태 업데이트는 별도로 처리
      }
    } catch (error) {
      console.error("챗봇 응답 오류:", error);
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: "죄송합니다. 응답을 가져오는 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.",
          timestamp: new Date().toISOString(),
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  // 티커 클릭 핸들러
  const handleTickerClick = (ticker: string) => {
    if (onStockClick) {
      onStockClick(ticker);
    }
  };

  // 메시지에서 티커 추출 및 링크 변환
  const renderMessage = (message: IChatMessage) => {
    // 티커 패턴 (6자리 숫자)
    const tickerPattern = /(\d{6})/g;

    if (message.role === "user") {
      return <p className="text-sm whitespace-pre-wrap">{message.content}</p>;
    }

    // 어시스턴트 메시지에서 티커를 링크로 변환
    const parts = message.content.split(tickerPattern);
    const renderedParts: React.ReactNode[] = [];

    parts.forEach((part, index) => {
      if (tickerPattern.test(part)) {
        renderedParts.push(
          <button
            key={index}
            onClick={() => handleTickerClick(part)}
            className="text-blue-600 hover:text-blue-800 underline font-mono"
          >
            {part}
          </button>
        );
      } else {
        renderedParts.push(
          <span key={index} className="whitespace-pre-wrap">
            {part}
          </span>
        );
      }
    });

    return <div className="text-sm">{renderedParts}</div>;
  };

  // 제안 메시지 표시
  const suggestionMessages: string[] = [
    "삼성전자 현재가 알려줘",
    "VCP 시그널 종목 추천해줘",
    "오늘 시장 상태 어때?",
    "005930 종목 분석해줘",
  ];

  return (
    <Card className="flex flex-col h-[600px]">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg flex items-center gap-2">
            <span className="text-2xl">🤖</span>
            AI 주식 챗봇
          </CardTitle>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => {
              setMessages([
                {
                  role: "assistant",
                  content: "안녕하세요! 한국 주식 AI 챗봇입니다. 주식 관련 질문을 해주세요.",
                  timestamp: new Date().toISOString(),
                },
              ]);
            }}
          >
            새 대화
          </Button>
        </div>
      </CardHeader>

      <CardContent className="flex-1 flex flex-col gap-4 overflow-hidden">
        {/* 메시지 영역 */}
        <div className="flex-1 overflow-y-auto space-y-4 pr-2">
          {messages.map((message, index) => (
            <div
              key={index}
              className={`flex ${message.role === "user" ? "justify-end" : "justify-start"}`}
            >
              <div
                className={`max-w-[80%] rounded-lg px-4 py-2 ${
                  message.role === "user"
                    ? "bg-blue-600 text-white"
                    : "bg-gray-100 text-gray-900"
                }`}
              >
                {renderMessage(message)}
                <span className="text-xs opacity-60 mt-1 block">
                  {new Date(message.timestamp).toLocaleTimeString("ko-KR", {
                    hour: "2-digit",
                    minute: "2-digit",
                  })}
                </span>
              </div>
            </div>
          ))}
          {isLoading && (
            <div className="flex justify-start">
              <div className="bg-gray-100 dark:bg-gray-700 rounded-lg px-4 py-2">
                <span className="text-gray-600 dark:text-gray-300">
                  {typingDots}
                </span>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* 제안 버튼 영역 */}
        {messages.length <= 1 && (
          <div className="flex flex-wrap gap-2">
            {suggestionMessages.map((suggestion) => (
              <Badge
                key={suggestion}
                variant="outline"
                className="cursor-pointer hover:bg-gray-100"
                onClick={() => handleSendMessage(suggestion)}
              >
                {suggestion}
              </Badge>
            ))}
          </div>
        )}

        {/* 입력 영역 */}
        <div className="flex gap-2">
          <Input
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                handleSendMessage(inputValue);
              }
            }}
            placeholder="메시지를 입력하세요..."
            disabled={isLoading}
            className="flex-1"
          />
          <Button
            onClick={() => handleSendMessage(inputValue)}
            disabled={isLoading || !inputValue.trim()}
          >
            전송
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

export default ChatbotWidget;
