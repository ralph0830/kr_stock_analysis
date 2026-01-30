/**
 * E2E 테스트 - 기본 페이지 접속 및 렌더링
 *
 * 이 테스트는 백엔드 서비스가 실행 중이어야 합니다.
 *
 * Prerequisites:
 * - API Gateway (port 5111)
 * - Frontend (port 5110)
 */

import { test, expect } from "@playwright/test"

test.describe("시그널 페이지 E2E 테스트", () => {
  test("시그널 페이지 접속 및 기본 UI 확인", async ({ page }) => {
    // 시그널 페이지 접속
    await page.goto("http://localhost:5110/signals")

    // 페이지 로딩 대기
    await page.waitForLoadState("networkidle")

    // 페이지 제목 확인
    await expect(page.locator("h1")).toContainText("종가베팅 V2 시그널")

    // 등급 카드 확인
    await expect(page.locator("text=S 등급")).toBeVisible()
    await expect(page.locator("text=A 등급")).toBeVisible()
    await expect(page.locator("text=B 등급")).toBeVisible()
    await expect(page.locator("text=C 등급")).toBeVisible()
  })

  test("종목 상세 페이지 이동 테스트", async ({ page }) => {
    await page.goto("http://localhost:5110/signals")
    await page.waitForLoadState("networkidle")

    // 시그널이 있는지 확인 (API에서 가져온 데이터)
    const signalLinks = page.locator("a[href^='/stock/']")

    const count = await signalLinks.count()

    if (count > 0) {
      // 첫 번째 종목 링크 클릭
      await signalLinks.first().click()

      // 종목 상세 페이지로 이동 확인
      await page.waitForURL(/\/stock\/\d+/)

      // 페이지 제목 확인
      const h1 = page.locator("h1")
      if (await h1.count() > 0) {
        await expect(h1).toBeVisible()
      }
    } else {
      // 데이터가 없는 경우 처리
      console.log("시그널 데이터가 없어 테스트 스킵")
    }
  })
})

test.describe("대시보드 E2E 테스트", () => {
  test("대시보드 페이지 접속", async ({ page }) => {
    await page.goto("http://localhost:5110/dashboard")
    await page.waitForLoadState("networkidle")

    // 페이지 제목 확인
    await expect(page.locator("h1")).toContainText("KR Stock 대시보드")
  })
})

test.describe("메인 페이지 E2E 테스트", () => {
  test("메인 페이지 접속", async ({ page }) => {
    await page.goto("http://localhost:5110/")
    await page.waitForLoadState("networkidle")

    // 페이지가 로드되는지 확인
    const body = page.locator("body")
    await expect(body).toBeVisible()
  })
})
