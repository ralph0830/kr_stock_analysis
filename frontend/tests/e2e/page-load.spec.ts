/**
 * E2E Page Load Tests
 * TDD Red Phase: 모든 페이지가 정상 로드되는지 확인
 */
import { test, expect } from '@playwright/test';

// 기본 설정
const BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5110';

test.describe('Frontend Page Load Tests (TDD)', () => {
  test.beforeEach(async ({ page }) => {
    // 각 테스트 전에 페이지 로드
    await page.goto(BASE_URL, { timeout: 10000 });
  });

  test('홈 페이지 (/) 로드', async ({ page }) => {
    await page.goto(BASE_URL);

    // 페이지 타이틀 확인
    await expect(page).toHaveTitle(/Ralph Stock|Stock Analysis/);

    // 주요 요소 확인
    const heading = page.locator('h1, h2, h3').first();
    await expect(heading).toBeVisible();
  });

  test('대시보드 (/dashboard) 로드', async ({ page }) => {
    await page.goto(`${BASE_URL}/dashboard`);

    // 페이지 타이틀 또는 주요 콘텐츠 확인
    await expect(page.locator('h1, h2').first()).toBeVisible({ timeout: 5000 });
  });

  test('KR 대시보드 (/dashboard/kr) 로드', async ({ page }) => {
    await page.goto(`${BASE_URL}/dashboard/kr`);

    // 한국 주식 시장 관련 UI 확인
    await expect(page.locator('h1, h2').first()).toBeVisible({ timeout: 5000 });
  });

  test('VCP 페이지 (/dashboard/kr/vcp) 로드', async ({ page }) => {
    await page.goto(`${BASE_URL}/dashboard/kr/vcp`);

    // VCP 관련 UI 확인
    await expect(page.locator('h1, h2').first()).toBeVisible({ timeout: 5000 });
  });

  test('종가베팅 페이지 (/dashboard/kr/closing-bet) 로드', async ({ page }) => {
    await page.goto(`${BASE_URL}/dashboard/kr/closing-bet`);

    // 종가베팅 관련 UI 확인
    await expect(page.locator('h1, h2').first()).toBeVisible({ timeout: 5000 });
  });

  test('시그널 페이지 (/signals) 로드', async ({ page }) => {
    await page.goto(`${BASE_URL}/signals`);

    // 시그널 관련 UI 확인
    await expect(page.locator('h1, h2').first()).toBeVisible({ timeout: 5000 });
  });

  test('차트 페이지 (/chart) 로드', async ({ page }) => {
    await page.goto(`${BASE_URL}/chart`);

    // 차트 관련 UI 확인
    await expect(page.locator('h1, h2').first()).toBeVisible({ timeout: 5000 });
  });

  test('챗봇 페이지 (/chatbot) 로드', async ({ page }) => {
    await page.goto(`${BASE_URL}/chatbot`);

    // 챗봇 UI 확인 (입력창 등)
    const input = page.locator('input, textarea').first();
    await expect(input).toBeVisible({ timeout: 5000 });
  });

  test('종목 상세 페이지 (/stock/[ticker]) 로드', async ({ page }) => {
    // 삼성전자 (005930)로 테스트
    await page.goto(`${BASE_URL}/stock/005930`);

    // 종목 상세 UI 확인 (ticker 표시 또는 "시그널 목록" 링크)
    const link = page.locator('a:has-text("시그널 목록")');
    await expect(link).toBeVisible({ timeout: 5000 });
  });

  test('콘솔 에러 없음', async ({ page }) => {
    // 모든 주요 페이지 순회하며 콘솔 에러 확인
    const pages = [
      '/',
      '/dashboard',
      '/dashboard/kr',
      '/dashboard/kr/vcp',
      '/dashboard/kr/closing-bet',
      '/signals',
      '/chart',
      '/chatbot',
      '/stock/005930',
    ];

    for (const path of pages) {
      const response = await page.goto(`${BASE_URL}${path}`);
      expect(response?.status()).toBeLessThan(500);

      // JavaScript 에러 확인
      const errors: string[] = [];
      page.on('console', msg => {
        if (msg.type() === 'error') {
          errors.push(msg.text());
        }
      });
    }
  });
});
