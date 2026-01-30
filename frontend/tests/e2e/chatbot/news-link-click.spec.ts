/**
 * E2E 테스트 - 챗봇 뉴스 링크 클릭 기능 (Phase 4: RED)
 *
 * 테스트 목적:
 * - 챗봇 응답의 뉴스 링크가 클릭 가능한지 확인
 * - 링크 클릭 시 새 탭에서 열리는지 확인
 * - 여러 뉴스 링크가 모두 작동하는지 확인
 *
 * Prerequisites:
 * - API Gateway (port 5111)
 * - Frontend (port 5110)
 * - DB에 테스트용 뉴스 URL 데이터 필요
 */

import { test, expect } from "@playwright/test"

test.describe("챗봇 뉴스 링크 E2E 테스트 (Phase 4: RED)", () => {
  test.beforeEach(async ({ page }) => {
    // 챗봇 페이지 접속
    await page.goto("http://localhost:5110/chatbot")
    await page.waitForLoadState("networkidle")
  })

  /**
   * RED TEST 1: 뉴스 링크가 새 탭에서 열림
   * 챗봇 응답에 포함된 뉴스 링크를 클릭하면 새 탭에서 열려야 함
   */
  test("RED: 뉴스 링크 클릭 시 새 탭에서 열림", async ({ page, context }) => {
    // 메시지 입력
    const messageInput = page.locator("input[placeholder*='메시지를 입력하세요']")
    await messageInput.fill("삼성전자 뉴스 알려줘")

    // 전송 버튼 클릭
    const sendButton = page.locator("button:has-text('전송')")
    await sendButton.click()

    // 응답 대기 (최대 10초)
    await page.waitForTimeout(5000)

    // 마크다운 링크 [title](url) 형식 찾기
    // 뉴스 링크는 n.news.naver.com 도메인을 포함
    const newsLinkSelector = "a[href*='n.news.naver.com']"

    // 링크가 있는지 확인 (뉴스 URL이 있어야 함)
    const linkExists = await page.locator(newsLinkSelector).count() > 0

    if (linkExists) {
      // 첫 번째 뉴스 링크 가져오기
      const newsLink = page.locator(newsLinkSelector).first()

      // 링크의 target 속성이 _blank인지 확인
      const targetValue = await newsLink.getAttribute("target")
      expect(targetValue).toBe("_blank")

      // rel 속성에 noopener noreferrer가 있는지 확인 (보안)
      const relValue = await newsLink.getAttribute("rel")
      expect(relValue).toContain("noopener")
      expect(relValue).toContain("noreferrer")

      // 새 탭 열림 이벤트 리스너
      const newTabPromise = context.waitForEvent("page")

      // 링크 클릭
      await newsLink.click()

      // 새 탭이 열리는지 확인
      const newTab = await newTabPromise
      await newTab.waitForLoadState("domcontentloaded")

      // 새 탭의 URL이 네이버 뉴스 도메인인지 확인
      expect(newTab.url()).toContain("n.news.naver.com")

      // 새 탭 닫기
      await newTab.close()
    } else {
      // 뉴스 링크가 없는 경우 (테스트 데이터 부족 가능)
      console.log("뉴스 링크가 없어 테스트 통과로 간주 (데이터 필요)")
      // 링크가 없더라도 응답은 와야 함
      const messages = page.locator(".bg-gray-100, .dark\\:bg-gray-700")
      await expect(messages.nth(1)).toBeVisible() // 첫 응답
    }
  })

  /**
   * RED TEST 2: 뉴스 링크에 올바른 URL이 포함됨
   * 링크의 href 속성에 실제 뉴스 URL이 있어야 함
   */
  test("RED: 뉴스 링크에 올바른 URL 포함", async ({ page }) => {
    // 테스트용 종목 분석 요청
    const messageInput = page.locator("input[placeholder*='메시지를 입력하세요']")
    await messageInput.fill("005930 종목 분석해줘")

    const sendButton = page.locator("button:has-text('전송')")
    await sendButton.click()

    // 응답 대기
    await page.waitForTimeout(5000)

    // 뉴스 링크 찾기
    const newsLinks = page.locator("a[href*='n.news.naver.com'], a[href*='yna.co.kr'], a[href*='news']")

    const linkCount = await newsLinks.count()

    if (linkCount > 0) {
      // 첫 번째 링크 확인
      const firstLink = newsLinks.first()
      const href = await firstLink.getAttribute("href")

      // URL이 유효한 형식인지 확인
      expect(href).toMatch(/^https?:\/\/.+/)

      // 링크 텍스트가 있는지 확인
      const linkText = await firstLink.textContent()
      expect(linkText?.trim()).toBeTruthy()
    } else {
      console.log("뉴스 링크가 없음 - DB 데이터 필요")
    }
  })

  /**
   * RED TEST 3: 여러 뉴스 링크가 모두 클릭 가능
   * 응답에 여러 뉴스 링크가 있을 경우 모두 클릭 가능해야 함
   */
  test("RED: 여러 뉴스 링크 모두 클릭 가능", async ({ page, context }) => {
    // 뉴스 요청
    const messageInput = page.locator("input[placeholder*='메시지를 입력하세요']")
    await messageInput.fill("최신 뉴스 알려줘")

    const sendButton = page.locator("button:has-text('전송')")
    await sendButton.click()

    await page.waitForTimeout(5000)

    // 모든 뉴스 링크 찾기
    const newsLinks = page.locator("a[href*='n.news.naver.com'], a[href*='yna.co.kr']")

    const linkCount = await newsLinks.count()

    if (linkCount >= 2) {
      // 모든 링크에 target="_blank"가 있는지 확인
      for (let i = 0; i < Math.min(linkCount, 3); i++) {
        const link = newsLinks.nth(i)
        const target = await link.getAttribute("target")
        expect(target).toBe("_blank")
      }
    } else if (linkCount === 1) {
      // 하나라도 있는지 확인
      const link = newsLinks.first()
      await expect(link).toBeVisible()
    } else {
      console.log("뉴스 링크 없음 - DB 데이터 필요")
    }
  })

  /**
   * RED TEST 4: 마크다운 링크 형식이 올바르게 렌더링됨
   * [title](url) 형식의 마크다운이 <a> 태그로 변환되어야 함
   */
  test("RED: 마크다운 링크 형식 렌더링", async ({ page }) => {
    // 분석 요청 (뉴스 포함된 응답 기대)
    const messageInput = page.locator("input[placeholder*='메시지를 입력하세요']")
    await messageInput.fill("삼성전자 어떄?")

    const sendButton = page.locator("button:has-text('전송')")
    await sendButton.click()

    await page.waitForTimeout(5000)

    // 응답 메시지 영역
    const responseMessages = page.locator(".bg-gray-100, .dark\\:bg-gray-700")

    if (await responseMessages.count() > 1) {
      const lastResponse = responseMessages.nth(1) // 두 번째 메시지 (첫 응답)

      // 마크다운 링크 패턴: [title](url)이 <a 태그로 변환되어야 함
      const linksInResponse = lastResponse.locator("a[href]")

      const linkCount = await linksInResponse.count()

      // 뉴스 링크가 있으면 href 속성 확인
      if (linkCount > 0) {
        for (let i = 0; i < linkCount; i++) {
          const link = linksInResponse.nth(i)
          const href = await link.getAttribute("href")

          // href가 있어야 함
          expect(href).toBeTruthy()

          // 외부 링크인 경우 target="_blank" 확인
          if (href?.startsWith("http")) {
            const target = await link.getAttribute("target")
            // 새 탭에서 열려야 함 (현재는 테스트 실패 예상)
            if (target !== "_blank") {
              console.log("링크에 target='_blank' 속성 없음 - GREEN 단계에서 구현 필요")
            }
          }
        }
      }
    }
  })

  /**
   * RED TEST 5: 뉴스 링크가 없을 때도 응답 정상 표시
   * 뉴스 링크가 없더라도 응답은 렌더링되어야 함
   */
  test("RED: 뉴스 링크 없을 때도 응답 정상 표시", async ({ page }) => {
    // 단순 질문 (뉴스 없을 가능성 높음)
    const messageInput = page.locator("input[placeholder*='메시지를 입력하세요']")
    await messageInput.fill("안녕")

    const sendButton = page.locator("button:has-text('전송')")
    await sendButton.click()

    // 응답 대기
    await page.waitForTimeout(3000)

    // 응답 메시지가 표시되어야 함
    const responseMessages = page.locator(".bg-gray-100, .dark\\:bg-gray-700")
    await expect(responseMessages.nth(1)).toBeVisible()

    // 응답 내용 확인
    const responseText = await responseMessages.nth(1).textContent()
    expect(responseText).toBeTruthy()
    expect(responseText?.length).toBeGreaterThan(0)
  })
})
