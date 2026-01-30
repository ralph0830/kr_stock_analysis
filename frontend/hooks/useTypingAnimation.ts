/**
 * Typing Animation Hook
 * 점 반복 애니메이션 (. .. ... .... .....)
 *
 * 사이클: . → .. → ... → .... → ..... → .... → ... → .. → . → (반복)
 */

import { useState, useEffect, useRef } from "react";

interface IUseTypingAnimationOptions {
  /** 애니메이션 속도 (ms) */
  interval?: number;
  /** 최대 점 개수 */
  maxDots?: number;
}

/**
 * 타이핑 애니메이션 훅
 *
 * @example
 * const dots = useTypingAnimation(); // ".", "..", "..." 순환
 * return <span>{dots}</span>;
 */
export function useTypingAnimation(options: IUseTypingAnimationOptions = {}): string {
  const { interval = 400, maxDots = 5 } = options;

  const [dots, setDots] = useState(".");
  const [isIncreasing, setIsIncreasing] = useState(true);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    intervalRef.current = setInterval(() => {
      setDots((prev) => {
        const currentLength = prev.length;

        // 증가 모드
        if (isIncreasing) {
          if (currentLength >= maxDots) {
            setIsIncreasing(false);
            return ".".repeat(maxDots - 1);
          }
          return ".".repeat(currentLength + 1);
        }
        // 감소 모드
        else {
          if (currentLength <= 1) {
            setIsIncreasing(true);
            return "..";
          }
          return ".".repeat(currentLength - 1);
        }
      });
    }, interval);

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, [interval, maxDots, isIncreasing]);

  return dots;
}

export default useTypingAnimation;
