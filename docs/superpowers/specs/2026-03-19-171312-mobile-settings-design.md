# Mobile Settings Design

## Goal

Improve the mobile experience of the settings area by making it primarily readable and browseable on phones, while preserving the existing desktop split-layout behavior.

## Constraints

- The user rarely edits settings on mobile.
- Mobile settings should prioritize reading, scanning, and light navigation over dense inline forms.
- Desktop settings behavior should stay structurally unchanged in this round.

## Chosen Approach

Use a mobile-only reading-first settings shell.

- `< md`: replace the desktop sidebar-first layout with a settings hub and detail pages
- `>= md`: keep the current sidebar + content layout

## Mobile Information Architecture

### Settings Hub

The mobile `/settings` landing page becomes a hub instead of an automatic redirect to `/settings/model`.

It shows three top-level cards:

- `模型设置`
  - current model summary
  - enabled model count
  - entry into model detail
- `下载配置`
  - downloader summary
  - entry into download detail
- `关于`
  - version/project summary
  - entry into about detail

### Detail Pages

- `模型设置详情`
  - summary-first presentation
  - model/provider overview before editing
  - edit actions lead into existing form-heavy subviews
- `下载配置详情`
  - summary-first presentation
  - lightweight explanation and status before editing
- `关于`
  - optimized for narrow-screen reading
  - better spacing and hierarchy for text and screenshots

## Interaction Rules

- Mobile settings keep a top bar with a clear "back to home" entry
- Mobile detail pages expose an in-app return path to the settings hub
- Direct links such as `/settings/model` still work on mobile
- Mobile `/settings` should no longer auto-redirect into `model`
- Reading content comes before heavy edit controls on mobile

## Implementation Direction

- Introduce responsive branching in `SettingLayout`
- Add a dedicated mobile settings hub component instead of reusing the desktop sidebar presentation
- Keep current route structure where possible so existing links keep working
- Adapt menu data into card-style navigation for mobile
- Improve the about page typography and spacing for narrow screens
- Defer large form refactors by wrapping existing model/download flows in mobile-friendly containers first

## Error Handling

- If provider/model state is still loading, mobile hub cards should show lightweight loading text rather than blank areas
- If summaries cannot be derived, cards should fall back to neutral placeholder text and still allow navigation
- Existing detail routes should remain reachable even if the hub summary data is incomplete

## Verification Plan

- Add mobile layout logic tests for the settings shell
- Run targeted frontend tests
- Run frontend build
- Manually inspect `/settings`, `/settings/model`, `/settings/download`, and `/settings/about` at a narrow viewport
