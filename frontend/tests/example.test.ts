/**
 * Vitest 설정 확인용 샘플 테스트
 */

import { describe, it, expect } from 'vitest'

describe('Vitest 환경 설정 테스트', () => {
  it('테스트 환경이 정상적으로 동작해야 한다', () => {
    expect(1 + 1).toBe(2)
  })

  it('문자열 비교가 정상적으로 동작해야 한다', () => {
    const str = 'Hello, Vitest!'
    expect(str).toBe('Hello, Vitest!')
    expect(str).toContain('Vitest')
  })

  it('객체 비교가 정상적으로 동작해야 한다', () => {
    const obj = { name: '테스트', value: 100 }
    expect(obj).toEqual({ name: '테스트', value: 100 })
    expect(obj).toHaveProperty('name')
  })
})
