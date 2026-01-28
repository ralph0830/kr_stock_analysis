import { defineConfig, devices } from "@playwright/test";

/**
 * Playwright E2E 테스트 설정
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

  use: {
    // Base URL for all tests
    baseURL: "http://localhost:5110",

    // Collect trace when retrying the failed test
    trace: "on-first-retry",

    // Screenshot on failure
    screenshot: "only-on-failure",

    // Video on failure
    video: "retain-on-failure",
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
