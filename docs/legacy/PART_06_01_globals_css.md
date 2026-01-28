# PART 06-1: Dashboard Design System (globals.css)

> **파일**: `frontend/src/app/globals.css`
> **용도**: Apple Dark Mode 기반 대시보드 스타일시트
> **프레임워크**: Tailwind CSS

---

## 개요

Korean Market AI Stock Analysis 시스템의 디자인 시스템입니다.

Apple Dark Mode 팔레트를 기반으로 하며, Glassmorphism 효과와 커스텀 스크롤바를 포함합니다.

---

## CSS 변수 정의

```css
@import "tailwindcss";

:root {
  /* Apple Dark Mode Palette */
  --bg-page: #000000;
  --bg-surface: #1c1c1e;
  --bg-surface-hover: #2c2c2e;
  --bg-glass: rgba(28, 28, 30, 0.75);
  --border-color: rgba(255, 255, 255, 0.1);

  /* Text Colors */
  --text-primary: #f5f5f7;
  --text-secondary: #86868b;
  --text-tertiary: #6e6e73;

  /* Accents */
  --accent: #2997ff;
  --status-success: #30d158;
  --status-error: #ff453a;
  --status-warning: #ff9f0a;
}
```

### 색상 매핑

| 변수 | 값 | 용도 |
|-----|-----|------|
| `--bg-page` | `#000000` | 페이지 배경 |
| `--bg-surface` | `#1c1c1e` | 카드/패널 배경 |
| `--bg-surface-hover` | `#2c2c2e` | 호버 상태 |
| `--bg-glass` | `rgba(28, 28, 30, 0.75)` | 글래스모피즘 |
| `--border-color` | `rgba(255, 255, 255, 0.1)` | 테두리 |
| `--text-primary` | `#f5f5f7` | 주요 텍스트 |
| `--text-secondary` | `#86868b` | 보조 텍스트 |
| `--accent` | `#2997ff` | 강조색 (파란색) |
| `--status-success` | `#30d158` | 성공 (녹색) |
| `--status-error` | `#ff453a` | 에러 (빨간색) |
| `--status-warning` | `#ff9f0a` | 경고 (주황색) |

---

## 기본 스타일

```css
body {
  background-color: var(--bg-page);
  color: var(--text-primary);
  font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "Segoe UI", "Inter", sans-serif;
  font-size: 14px;
  line-height: 1.6;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}
```

---

## Glassmorphism

### `.apple-glass` - 사이드바/네비게이션

```css
.apple-glass {
  background-color: rgba(28, 28, 30, 0.65);
  backdrop-filter: blur(20px) saturate(180%);
  -webkit-backdrop-filter: blur(20px) saturate(180%);
  border-right: 1px solid rgba(255, 255, 255, 0.08);
}
```

### `.glass-card` - 카드 컴포넌트

```css
.glass-card {
  background-color: var(--bg-surface);
  border: 1px solid rgba(255, 255, 255, 0.05);
  border-radius: 18px;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
  transition: transform 0.2s ease, background-color 0.2s ease;
}

.glass-card:hover {
  background-color: var(--bg-surface-hover);
  transform: scale(1.005);
}
```

---

## 스크롤바

```css
::-webkit-scrollbar {
  width: 8px;
  height: 8px;
}

::-webkit-scrollbar-track {
  background: transparent;
}

::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.2);
  border-radius: 4px;
  border: 2px solid var(--bg-page);
}

::-webkit-scrollbar-thumb:hover {
  background: rgba(255, 255, 255, 0.3);
}
```

---

## 애니메이션

### `fadeIn` - 페이드인

```css
@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(10px);
  }

  to {
    opacity: 1;
    transform: translateY(0);
  }
}
```

### `pulse-glow` - 펄스 글로우

```css
@keyframes pulse-glow {
  0% {
    box-shadow: 0 0 10px rgba(16, 185, 129, 0.1);
  }

  50% {
    box-shadow: 0 0 25px rgba(16, 185, 129, 0.3);
  }

  100% {
    box-shadow: 0 0 10px rgba(16, 185, 129, 0.1);
  }
}
```

### 유틸리티 클래스

```css
.animate-fade-in {
  animation: fadeIn 0.3s ease both;
}
```

---

## 유틸리티 클래스

```css
.text-xxs {
  font-size: 10px !important;
  letter-spacing: 0.02em;
}
```

---

## Tailwind 커스텀 색상

Tailwind 설정에서 사용할 수 있는 커스텀 색상:

```javascript
// tailwind.config.js
module.exports = {
  theme: {
    extend: {
      colors: {
        // 배경
        'bg-page': '#000000',
        'bg-surface': '#1c1c1e',
        'bg-surface-hover': '#2c2c2e',

        // 텍스트
        'text-primary': '#f5f5f7',
        'text-secondary': '#86868b',

        // 상태
        'status-success': '#30d158',
        'status-error': '#ff453a',
        'status-warning': '#ff9f0a',
      }
    }
  }
}
```

---

## 사용 예시

```tsx
{/* Glass Card */}
<div className="glass-card p-6">
  <h3 className="text-lg font-bold text-white">카드 제목</h3>
  <p className="text-sm text-text-secondary">카드 내용</p>
</div>

{/* Apple Glass (사이드바) */}
<nav className="apple-glass w-64 h-screen">
  ...
</nav>

{/* Status Colors */}
<span className="text-status-success">성공</span>
<span className="text-status-error">에러</span>
<span className="text-status-warning">경고</span>

{/* Animations */}
<div className="animate-fade-in">페이드인 요소</div>
```

---

## 브라우저 호환성

| 기능 | Chrome | Safari | Firefox |
|-----|--------|--------|---------|
| CSS Variables | ✅ 49+ | ✅ 9.1+ | ✅ 31+ |
| backdrop-filter | ✅ 76+ | ✅ 9+ | ✅ 103+ |
| -webkit-backdrop-filter | - | ✅ 9+ | - |

---

## Apple SF Pro 폰트

```css
/* macOS/iOS 기본 시스템 폰트 */
font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "Segoe UI", "Inter", sans-serif;
```

**대체 폰트 순서:**
1. `-apple-system`: macOS 시스템 폰트
2. `BlinkMacSystemFont`: Chrome macOS
3. `SF Pro Text`: Apple 공식 폰트
4. `Segoe UI`: Windows
5. `Inter`: 웹 폴백
