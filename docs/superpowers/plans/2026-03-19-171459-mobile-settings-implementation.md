# Mobile Settings Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a reading-first mobile settings experience while preserving the existing desktop split layout.

**Architecture:** Keep the current desktop settings routes and content structure, but switch the shell on narrow screens to a single-column mobile layout with a settings hub, mobile page metadata, and summary-first detail views. Use a small pure TypeScript helper module for route decisions and hub summaries so the mobile behavior can be covered by `node:test`.

**Tech Stack:** React 19, React Router, Tailwind CSS v4, Zustand, `node:test`, Vite

---

## File Map

- Create: `BillNote_frontend/src/lib/settingsLayout.ts`
- Create: `BillNote_frontend/src/pages/SettingPage/SettingsHub.tsx`
- Create: `BillNote_frontend/src/pages/SettingPage/SettingsIndex.tsx`
- Modify: `BillNote_frontend/src/App.tsx`
- Modify: `BillNote_frontend/src/layouts/SettingLayout.tsx`
- Modify: `BillNote_frontend/src/pages/SettingPage/Model.tsx`
- Modify: `BillNote_frontend/src/pages/SettingPage/Downloader.tsx`
- Modify: `BillNote_frontend/src/pages/SettingPage/about.tsx`
- Test: `BillNote_frontend/tests/settingsLayout.test.ts`

## Chunk 1: Mobile route and summary helpers

### Task 1: Add failing tests for settings mobile decisions

**Files:**
- Create: `BillNote_frontend/tests/settingsLayout.test.ts`
- Test: `BillNote_frontend/src/lib/settingsLayout.ts`

- [ ] **Step 1: Write the failing test**

```ts
test('desktop settings index redirects to model while mobile stays on hub', () => {
  assert.equal(getSettingsIndexTarget(1280), '/settings/model')
  assert.equal(getSettingsIndexTarget(390), null)
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `node --test BillNote_frontend/tests/settingsLayout.test.ts`
Expected: FAIL because `settingsLayout.ts` does not exist yet

- [ ] **Step 3: Write minimal implementation**

```ts
export function getSettingsIndexTarget(width: number): string | null
export function getSettingsPageMeta(pathname: string): { title: string; description: string; backToHub: boolean }
export function buildSettingsHubCards(input: SummaryInput): SettingsHubCard[]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `node --test BillNote_frontend/tests/settingsLayout.test.ts`
Expected: PASS

## Chunk 2: Mobile settings shell and hub

### Task 2: Route `/settings` to a mobile hub instead of unconditional redirect

**Files:**
- Create: `BillNote_frontend/src/pages/SettingPage/SettingsIndex.tsx`
- Modify: `BillNote_frontend/src/App.tsx`
- Modify: `BillNote_frontend/src/layouts/SettingLayout.tsx`

- [ ] **Step 1: Write the failing test**

```ts
test('settings page metadata marks root as hub and details as back-navigable', () => {
  assert.equal(getSettingsPageMeta('/settings').backToHub, false)
  assert.equal(getSettingsPageMeta('/settings/model').backToHub, true)
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `node --test BillNote_frontend/tests/settingsLayout.test.ts`
Expected: FAIL because metadata helper is still incomplete

- [ ] **Step 3: Write minimal implementation**

```tsx
<Route index element={<SettingsIndex />} />
```

```tsx
return isMobile ? <MobileSettingShell><Outlet /></MobileSettingShell> : <DesktopSettingShell ... />
```

- [ ] **Step 4: Run test to verify it passes**

Run: `node --test BillNote_frontend/tests/settingsLayout.test.ts`
Expected: PASS

### Task 3: Add a mobile settings hub with summary cards

**Files:**
- Create: `BillNote_frontend/src/pages/SettingPage/SettingsHub.tsx`
- Modify: `BillNote_frontend/src/layouts/SettingLayout.tsx`

- [ ] **Step 1: Write the failing test**

```ts
test('settings hub cards expose readable summaries and stable destinations', () => {
  const cards = buildSettingsHubCards({
    providerCount: 2,
    enabledProviderCount: 1,
    enabledModelCount: 3,
    downloadPlatformCount: 4,
  })
  assert.equal(cards[0].path, '/settings/model')
  assert.match(cards[0].summary, /3/)
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `node --test BillNote_frontend/tests/settingsLayout.test.ts`
Expected: FAIL because the summary builder is missing or incomplete

- [ ] **Step 3: Write minimal implementation**

```tsx
<SettingsHub cards={buildSettingsHubCards(...)} />
```

- [ ] **Step 4: Run test to verify it passes**

Run: `node --test BillNote_frontend/tests/settingsLayout.test.ts`
Expected: PASS

## Chunk 3: Mobile detail readability

### Task 4: Make model and download pages summary-first on mobile

**Files:**
- Modify: `BillNote_frontend/src/pages/SettingPage/Model.tsx`
- Modify: `BillNote_frontend/src/pages/SettingPage/Downloader.tsx`

- [ ] **Step 1: Reuse the passing helper tests as guardrails**

Run: `node --test BillNote_frontend/tests/settingsLayout.test.ts`
Expected: PASS before UI changes

- [ ] **Step 2: Write minimal implementation**

```tsx
return isMobile ? <SingleColumnSummaryThenContent /> : <ExistingTwoColumnLayout />
```

- [ ] **Step 3: Run test/build verification**

Run: `node --test BillNote_frontend/tests/settingsLayout.test.ts`
Expected: PASS

### Task 5: Improve about-page mobile readability

**Files:**
- Modify: `BillNote_frontend/src/pages/SettingPage/about.tsx`

- [ ] **Step 1: Reuse the passing helper tests as guardrails**

Run: `node --test BillNote_frontend/tests/settingsLayout.test.ts`
Expected: PASS before content layout changes

- [ ] **Step 2: Write minimal implementation**

```tsx
<div className="px-4 py-8 sm:px-6 sm:py-12">
```

- [ ] **Step 3: Run test/build verification**

Run: `node --test BillNote_frontend/tests/settingsLayout.test.ts`
Expected: PASS

## Final Verification

- [ ] Run: `node --test BillNote_frontend/tests/settingsLayout.test.ts`
- [ ] Run: `node --test BillNote_frontend/tests/homeLayout.test.ts`
- [ ] Run: `node --test BillNote_frontend/tests/taskProgress.test.ts`
- [ ] Run: `cd BillNote_frontend && npm run build`
