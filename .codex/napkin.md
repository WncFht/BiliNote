# Napkin Runbook

## Curation Rules
- Re-prioritize on every read.
- Keep recurring, high-value notes only.
- Max 10 items per category.
- Each item includes date + "Do instead".

## Execution & Validation (Highest Priority)
1. **[2026-03-19] Runtime failures need the exact log segment**
   Do instead: inspect the newest stack trace in `backend.local.log`, `frontend.local.log`, and `backend/logs/app.log` before inferring root cause.
2. **[2026-03-19] Frontend unit tests can run with plain `node --test`**
   Do instead: run targeted frontend `.ts` tests like `node --test BillNote_frontend/tests/taskProgress.test.ts` before reaching for extra runners such as `tsx`.
3. **[2026-03-19] Backend test files exist but `uv run pytest` is not guaranteed to work**
   Do instead: verify `pytest` is declared in `backend/pyproject.toml` before treating `backend/tests` as a runnable project-level test suite.

## Shell & Command Reliability
1. **[2026-03-19] Public-network shell commands should use the local proxy helper**
   Do instead: run networked commands with `zsh -lc 'proxy_on >/dev/null; <command>'` unless the target is localhost.

## Domain Behavior Guardrails
1. **[2026-03-19] Web history now hydrates from backend task history**
   Do instead: when different devices show different note histories, inspect `/api/task_history` and frontend `mergeHydratedTasks` before blaming local Zustand persistence alone.
2. **[2026-03-19] Task deletion must key by `task_id`**
   Do instead: send `task_id` from the frontend delete flow and remove cached `note_results` artifacts by `task_id`; `video_id/platform` is only a legacy fallback.
3. **[2026-03-19] Phone and Tailscale checks should run against `vite preview`**
   Do instead: use `./scripts/dev.sh restart-preview` when validating mobile load speed so the device hits production bundles instead of the HMR dev server.
4. **[2026-03-19] Preview mode needs its own API proxy config**
   Do instead: keep `vite.config.ts` `preview.proxy` aligned with `server.proxy`, or `/api` and `/static` routes will fail after switching away from `pnpm dev`.
5. **[2026-03-19] Mobile home performance depends on deferred preview assets**
   Do instead: keep `MarkdownViewer`, markmap, code-highlighting, image zoom, and history on lazy chunks so phone users do not download preview tooling before opening those panels.
6. **[2026-03-19] Settings performance should avoid whole-package AI icon imports**
   Do instead: render provider badges from lightweight local mappings in `providerLogo.ts` instead of importing all of `@lobehub/icons` for the settings model list.
7. **[2026-03-19] Stable manualChunks should exclude settings packages with circular deps**
   Do instead: split markdown, markmap, lottie, react core, and app shell with `build/manualChunks.ts`, but let settings packages ride on route-level lazy loading unless the chunk graph is proven cycle-free.
8. **[2026-03-19] Local runtime uses split logs**
   Do instead: treat `backend.local.log` and `frontend.local.log` as process stdout/stderr, and `backend/logs/app.log` as structured backend app logging.
9. **[2026-03-19] Web note generation must keep image-input mode disabled until payload handling is redesigned**
   Do instead: normalize web requests to `screenshot=False`, `video_understanding=False`, `grid_size=[]`, and strip `screenshot` from requested formats; keep screenshot mode explicit-only in CLI.

## User Directives
1. **[2026-03-19] Subagents must pin model and reasoning**
   Do instead: when spawning agents in this repo, explicitly pass `model: "gpt-5.4"` and `reasoning_effort: "xhigh"`.
