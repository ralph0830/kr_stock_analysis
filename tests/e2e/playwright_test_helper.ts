/**
 * Playwright E2E Test Helper
 *
 * API 상태 확인 및 페이지 렌더링 검증
 */

export interface E2ETestResult {
  testName: string;
  passed: boolean;
  message: string;
  details?: Record<string, any>;
}

export interface APIHealthCheck {
  signals: boolean;
  marketGate: boolean;
  health: boolean;
  websocket: boolean;
}

/**
 * 페이지에서 API 상태 확인
 */
export async function checkAPIHealthStatus(page: any): Promise<APIHealthCheck> {
  const result = await page.evaluate(async () => {
    const checks = {
      signals: false,
      marketGate: false,
      health: false,
      websocket: false,
    };

    try {
      // Health Check
      const healthRes = await fetch('http://localhost:5111/health');
      checks.health = healthRes.ok;
    } catch (e) {
      // Health check failed
    }

    try {
      // Signals API
      const signalsRes = await fetch('http://localhost:5111/api/kr/signals');
      checks.signals = signalsRes.ok;
    } catch (e) {
      // Signals API failed
    }

    try {
      // Market Gate API
      const marketGateRes = await fetch('http://localhost:5111/api/kr/market-gate');
      checks.marketGate = marketGateRes.ok;
    } catch (e) {
      // Market Gate API failed
    }

    // WebSocket 상태는 전역 변수 확인
    checks.websocket = typeof window !== 'undefined' &&
                      (window as any).__websocketConnected === true;

    return checks;
  });

  return result;
}

/**
 * Market Gate 상태 확인
 */
export async function checkMarketGateDisplay(page: any): Promise<E2ETestResult> {
  try {
    const marketGateInfo = await page.evaluate(() => {
      // Market Gate 섹션 확인
      const marketGateSection = document.querySelector('section');
      if (!marketGateSection) {
        return { found: false, error: 'Market Gate section not found' };
      }

      const textContent = marketGateSection.textContent || '';

      // 에러 메시지 확인
      if (textContent.includes('Market Gate 정보를 불러올 수 없습니다')) {
        return {
          found: true,
          hasError: true,
          error: 'Market Gate 정보를 불러올 수 없습니다',
        };
      }

      // 로딩 중 확인
      if (textContent.includes('로딩 중')) {
        return {
          found: true,
          isLoading: true,
          error: 'Still loading',
        };
      }

      // 데이터 확인
      const statusMatch = textContent.match(/(GREEN|YELLOW|RED)/);
      const levelMatch = textContent.match(/레벨\s*(\d+)/);

      return {
        found: true,
        hasData: true,
        status: statusMatch ? statusMatch[1] : null,
        level: levelMatch ? parseInt(levelMatch[1]) : null,
        fullText: textContent.substring(0, 200),
      };
    });

    if (!marketGateInfo.found) {
      return {
        testName: 'Market Gate Display',
        passed: false,
        message: 'Market Gate 섹션을 찾을 수 없습니다',
      };
    }

    if (marketGateInfo.hasError) {
      return {
        testName: 'Market Gate Display',
        passed: false,
        message: `Market Gate 에러: ${marketGateInfo.error}`,
        details: marketGateInfo,
      };
    }

    if (marketGateInfo.isLoading) {
      return {
        testName: 'Market Gate Display',
        passed: false,
        message: 'Market Gate가 여전히 로딩 중입니다',
        details: marketGateInfo,
      };
    }

    if (marketGateInfo.hasData) {
      return {
        testName: 'Market Gate Display',
        passed: true,
        message: `Market Gate 정상 표시: ${marketGateInfo.status} 레벨 ${marketGateInfo.level}`,
        details: marketGateInfo,
      };
    }

    return {
      testName: 'Market Gate Display',
      passed: false,
      message: 'Market Gate 상태를 확인할 수 없습니다',
      details: marketGateInfo,
    };
  } catch (error) {
    return {
      testName: 'Market Gate Display',
      passed: false,
      message: `테스트 실패: ${error}`,
    };
  }
}

/**
 * VCP Signals 상태 확인
 */
export async function checkVCPSignalsDisplay(page: any): Promise<E2ETestResult> {
  try {
    const signalsInfo = await page.evaluate(() => {
      const bodyText = document.body.textContent || '';

      // 활성 VCP 시그널 섹션 확인
      const hasSignalSection = bodyText.includes('활성 VCP 시그널') ||
                               bodyText.includes('전체 VCP 시그널');

      if (!hasSignalSection) {
        return { found: false };
      }

      // 종목코드 패턴 확인 (6자리 숫자)
      const tickerPattern = /\b\d{6}\b/g;
      const tickers = bodyText.match(tickerPattern) || [];

      // 종목명 확인
      const commonStocks = ['삼성전자', 'NAVER', 'SK하이닉스', '현대차', 'LG화학', '셀트리온'];
      const foundStocks = commonStocks.filter(stock => bodyText.includes(stock));

      return {
        found: true,
        tickerCount: tickers.length,
        uniqueTickers: [...new Set(tickers)].length,
        foundStocks,
        sampleText: bodyText.substring(bodyText.indexOf('VCP'), bodyText.indexOf('VCP') + 200),
      };
    });

    if (!signalsInfo.found) {
      return {
        testName: 'VCP Signals Display',
        passed: false,
        message: 'VCP Signals 섹션을 찾을 수 없습니다',
      };
    }

    return {
      testName: 'VCP Signals Display',
      passed: signalsInfo.uniqueTickers > 0,
      message: `VCP Signals ${signalsInfo.uniqueTickers}개 종목 표시됨`,
      details: signalsInfo,
    };
  } catch (error) {
    return {
      testName: 'VCP Signals Display',
      passed: false,
      message: `테스트 실패: ${error}`,
    };
  }
}

/**
 * WebSocket 연결 상태 확인
 */
export async function checkWebSocketConnection(page: any): Promise<E2ETestResult> {
  try {
    const wsInfo = await page.evaluate(() => {
      const bodyText = document.body.textContent || '';

      // WebSocket 상태 메시지 확인
      const connected = bodyText.includes('실시간 연결됨');
      const hasClientId = bodyText.match(/ID:\s*([a-f0-9\-]+)/i);

      return {
        connected,
        clientId: hasClientId ? hasClientId[1] : null,
      };
    });

    return {
      testName: 'WebSocket Connection',
      passed: wsInfo.connected,
      message: wsInfo.connected
        ? `WebSocket 연결됨 (ID: ${wsInfo.clientId})`
        : 'WebSocket 연결되지 않음',
      details: wsInfo,
    };
  } catch (error) {
    return {
      testName: 'WebSocket Connection',
      passed: false,
      message: `테스트 실패: ${error}`,
    };
  }
}

/**
 * Console 에러 확인
 */
export async function checkConsoleErrors(page: any): Promise<E2ETestResult> {
  try {
    // browser_context.on('console')로 미리 수집해야 함
    // 여기서는 페이지 내에서 에러 핸들러를 확인
    const errorInfo = await page.evaluate(() => {
      return {
        hasErrorMarkers: document.body.textContent?.includes('Error') || false,
      };
    });

    return {
      testName: 'Console Errors',
      passed: !errorInfo.hasErrorMarkers,
      message: errorInfo.hasErrorMarkers
        ? '화면에 에러 메시지가 있습니다'
        : '명백한 에러 메시지 없음',
      details: errorInfo,
    };
  } catch (error) {
    return {
      testName: 'Console Errors',
      passed: false,
      message: `테스트 실패: ${error}`,
    };
  }
}

/**
 * 전체 E2E 테스트 실행
 */
export async function runFullE2ETest(page: any, url: string): Promise<E2ETestResult[]> {
  const results: E2ETestResult[] = [];

  // 페이지 이동
  await page.goto(url, { waitUntil: 'networkidle' });

  // API 상태 확인
  const apiHealth = await checkAPIHealthStatus(page);
  results.push({
    testName: 'API Health Check',
    passed: apiHealth.health && apiHealth.marketGate && apiHealth.signals,
    message: `API 상태 - Health: ${apiHealth.health}, MarketGate: ${apiHealth.marketGate}, Signals: ${apiHealth.signals}`,
    details: apiHealth,
  });

  // 각 컴포넌트 확인
  results.push(await checkMarketGateDisplay(page));
  results.push(await checkVCPSignalsDisplay(page));
  results.push(await checkWebSocketConnection(page));
  results.push(await checkConsoleErrors(page));

  return results;
}

/**
 * 테스트 결과 보고서 생성
 */
export function generateTestReport(results: E2ETestResult[]): string {
  const lines: string[] = [];
  lines.push('='.repeat(60));
  lines.push('E2E Test Report');
  lines.push('='.repeat(60));
  lines.push('');

  let passCount = 0;
  let failCount = 0;

  for (const result of results) {
    const icon = result.passed ? '✅' : '❌';
    lines.push(`${icon} ${result.testName}`);
    lines.push(`   ${result.message}`);

    if (result.details) {
      lines.push(`   Details: ${JSON.stringify(result.details, null, 2).split('\n').join('\n   ')}`);
    }
    lines.push('');

    if (result.passed) passCount++;
    else failCount++;
  }

  lines.push('-'.repeat(60));
  lines.push(`Results: ${passCount} passed, ${failCount} failed, ${results.length} total`);
  lines.push('='.repeat(60));

  return lines.join('\n');
}

/**
 * Playwright 테스트에서 사용할 수 있는 헬퍼 함수
 */
export const e2eHelper = {
  checkAPIHealthStatus,
  checkMarketGateDisplay,
  checkVCPSignalsDisplay,
  checkWebSocketConnection,
  checkConsoleErrors,
  runFullE2ETest,
  generateTestReport,
};
