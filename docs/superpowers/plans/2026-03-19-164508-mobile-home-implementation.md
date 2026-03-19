# Mobile Home Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a mobile-specific home layout for BiliNote so phones get first-class `新建 / 任务 / 预览` navigation while desktop keeps the existing three-column workspace.

**Architecture:** Keep the existing feature units (`NoteForm`, `History`, `MarkdownViewer`) and switch the shell around them based on viewport width. The desktop branch continues using the current resizable panels; the mobile branch introduces a fixed top bar, bottom navigation, and single-panel content region.

**Tech Stack:** React 19, React Router, Tailwind CSS v4, `node:test`, Vite

---

## File Map

- Modify: `BillNote_frontend/src/layouts/HomeLayout.tsx`
- Modify: `BillNote_frontend/src/pages/HomePage/components/NoteForm.tsx`
- Modify: `BillNote_frontend/src/pages/HomePage/components/History.tsx`
- Modify: `BillNote_frontend/src/pages/HomePage/components/MarkdownViewer.tsx`
- Create: `BillNote_frontend/src/lib/homeLayout.ts`
- Test: `BillNote_frontend/tests/homeLayout.test.ts`

## Chunk 1: Mobile shell switching

### Task 1: Define and test mobile navigation behavior

**Files:**
- Create: `BillNote_frontend/src/lib/homeLayout.ts`
- Test: `BillNote_frontend/tests/homeLayout.test.ts`

- [ ] **Step 1: Write the failing test**

```ts
test('mobile layout starts on create and routes task actions to preview', () => {
  assert.equal(getNextMobileTab({ type: 'init' }), 'create')
  assert.equal(getNextMobileTab({ type: 'submit' }), 'preview')
  assert.equal(getNextMobileTab({ type: 'select-task' }), 'preview')
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `node --test BillNote_frontend/tests/homeLayout.test.ts`
Expected: FAIL because the helper does not exist yet

- [ ] **Step 3: Write minimal implementation**

```ts
export type MobileHomeTab = 'create' | 'tasks' | 'preview'
export function getNextMobileTab(action: { type: 'init' | 'submit' | 'select-task' }): MobileHomeTab
```

- [ ] **Step 4: Run test to verify it passes**

Run: `node --test BillNote_frontend/tests/homeLayout.test.ts`
Expected: PASS

### Task 2: Add the responsive `HomeLayout` branch

**Files:**
- Modify: `BillNote_frontend/src/layouts/HomeLayout.tsx`

- [ ] **Step 1: Write the failing test**

```ts
test('mobile shell renders bottom tabs and desktop shell does not', () => {
  const mobile = renderHomeLayout({ isMobile: true })
  const desktop = renderHomeLayout({ isMobile: false })
  assert.match(mobile, /新建/)
  assert.match(mobile, /任务/)
  assert.match(mobile, /预览/)
  assert.doesNotMatch(desktop, /新建/)
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `node --test BillNote_frontend/tests/homeLayout.test.ts`
Expected: FAIL because `HomeLayout` does not expose a mobile branch yet

- [ ] **Step 3: Write minimal implementation**

```tsx
const isMobile = useIsMobile()
return isMobile ? <MobileHomeShell ... /> : <DesktopHomeShell ... />
```

- [ ] **Step 4: Run test to verify it passes**

Run: `node --test BillNote_frontend/tests/homeLayout.test.ts`
Expected: PASS

## Chunk 2: Mobile content fit-and-finish

### Task 3: Remove obvious mobile overflow from the form

**Files:**
- Modify: `BillNote_frontend/src/pages/HomePage/components/NoteForm.tsx`
- Test: `BillNote_frontend/tests/homeLayout.test.ts`

- [ ] **Step 1: Write the failing test**

```ts
test('mobile form layout exposes stacked action controls', () => {
  const html = renderHomeLayout({ isMobile: true, tab: 'create' })
  assert.match(html, /生成笔记/)
  assert.match(html, /data-mobile-form/)
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `node --test BillNote_frontend/tests/homeLayout.test.ts`
Expected: FAIL because the mobile form markers and layout classes are missing

- [ ] **Step 3: Write minimal implementation**

```tsx
<div data-mobile-form className="space-y-4 md:space-y-4">
```

- [ ] **Step 4: Run test to verify it passes**

Run: `node --test BillNote_frontend/tests/homeLayout.test.ts`
Expected: PASS

### Task 4: Make history and preview fit inside the mobile shell

**Files:**
- Modify: `BillNote_frontend/src/pages/HomePage/components/History.tsx`
- Modify: `BillNote_frontend/src/pages/HomePage/components/MarkdownViewer.tsx`

- [ ] **Step 1: Write the failing test**

```ts
test('mobile preview and history avoid nested h-screen assumptions', () => {
  const html = renderHomeLayout({ isMobile: true, tab: 'preview' })
  assert.doesNotMatch(html, /h-screen w-full/)
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `node --test BillNote_frontend/tests/homeLayout.test.ts`
Expected: FAIL because current child components still assume full-screen ownership

- [ ] **Step 3: Write minimal implementation**

```tsx
<div className="flex min-h-0 w-full flex-1 flex-col overflow-hidden">
```

- [ ] **Step 4: Run test to verify it passes**

Run: `node --test BillNote_frontend/tests/homeLayout.test.ts`
Expected: PASS

## Final Verification

- [ ] Run: `node --test BillNote_frontend/tests/homeLayout.test.ts`
- [ ] Run: `node --test BillNote_frontend/tests/taskProgress.test.ts`
- [ ] Run: `cd BillNote_frontend && npm run build`
