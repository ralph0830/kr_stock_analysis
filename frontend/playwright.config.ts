import { defineConfig, devices } from "@playwright/test";

/**
 * Playwright E2E 테스트 설정
 *
 * 환경 변수:
 * - CI: CI 환경에서는 프로덕션 URL 사용
 * - BASE_URL: 테스트 대상 URL (기본: http://localhost:5110)
 *
 * 백엔드 서비스가 실행 중이어야 합니다:
 * - API Gateway: http://localhost:5111
 * - VCP Scanner: http://localhost:5112
 * - Signal Engine: http://localhost:5113
 * - Frontend: http://localhost:5110
 */
export default defineConfig({
  testDir: "./tests/e2e",
  fullyParallel: false,
  forbidOnly: false,
  retries: 0,
  workers: 1,

  // 환경 변수에 따른 baseURL 설정
  use: {
    // CI 환경이거나 BASE_URL이 지정된 경우 해당 URL 사용, 그렇지 않으면 로컬 개발 서버
    baseURL: process.env.BASE_URL || (process.env.CI ? "https://stock.ralphpark.com" : "http://localhost:5110"),

    // Collect trace when retrying the failed test
    trace: "on-first-retry",

    // Screenshot on failure
    screenshot: "only-on-failure",

    // Video on failure
    video: "retain-on-failure",
  },

  // 로컬 개발 시 자동으로 dev 서버 시작 (CI 환경 제외)
  webServer: process.env.CI ? undefined : {
    command: "npm run dev",
    url: "http://localhost:5110",
    timeout: 120 * 1000,
    reuseExistingServer: true, // 이미 실행 중인 서버 재사용
  },

  projects: [
    {
      name: "chromium",
      use: {
        ...devices["Desktop Chrome"],
      },
    },
  ],
});
