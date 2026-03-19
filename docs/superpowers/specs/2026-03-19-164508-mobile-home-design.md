# Mobile Home Design

## Goal

Improve the mobile experience for the BiliNote home flow without disturbing the existing desktop three-column layout. The first delivery only covers the home flow: note creation, task history, and result preview.

## Constraints

- Mobile can use a different information architecture from desktop.
- Desktop should remain functionally unchanged in this round.
- Settings stay reachable on mobile, but the settings pages are not redesigned in this round.

## Chosen Approach

Use a mobile-only top-and-bottom app shell for the home page.

- `< md`: mobile mode with three first-class destinations: `新建`, `任务`, `预览`
- `>= md`: keep the current desktop `HomeLayout` three-column structure

This fits the user's mixed mobile usage better than a form-first or wizard flow because creation, history switching, and reading results are all common tasks.

## Mobile Information Architecture

### `新建`

- Default landing view on mobile
- Hosts the note generation form
- Converts fixed two-column form groups into single-column or wrap-safe layouts

### `任务`

- Hosts search and task history
- Touch targets should be larger than the current desktop-oriented list density
- Selecting a task sets it as current and switches to `预览`

### `预览`

- Hosts markdown preview, transcript, and mindmap related viewing
- Empty state should give direct actions back to `新建` and `任务`
- Creating a task should switch here automatically after submission

## Interaction Rules

- Mobile keeps a pinned top bar with logo/title and settings entry
- Mobile keeps a fixed bottom navigation with the three primary destinations
- The bottom navigation remains visible while moving between creation, task switching, and reading
- Task creation and task selection both route the user into `预览`

## Implementation Direction

- Introduce a responsive branch in `HomeLayout` instead of forcing `ResizablePanelGroup` onto narrow screens
- Keep `NoteForm`, `History`, and `MarkdownViewer` as the feature units, but render them inside a mobile shell when the viewport is narrow
- Refine `NoteForm` mobile spacing:
  - stack or wrap fixed-width controls
  - convert action buttons to vertical stacking when needed
  - remove obvious horizontal overflow risks
- Refine `History` mobile density:
  - increase touch area
  - allow the list to fill the page height cleanly
- Refine `MarkdownViewer` mobile framing:
  - avoid nested `h-screen` assumptions inside the mobile shell
  - preserve current status/empty/error/success states

## Verification Plan

- Add a regression test for mobile home layout rendering and navigation
- Run the frontend test command that covers the new mobile behavior
- Run the production build
- Manually inspect the home flow at a narrow viewport
