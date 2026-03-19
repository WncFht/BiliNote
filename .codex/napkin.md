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
1. **[2026-03-19] Web generation history is device-local**
   Do instead: when different devices show different note histories, inspect the frontend Zustand `task-storage` persistence first; do not assume the backend serves a shared history list.
2. **[2026-03-19] Local runtime uses split logs**
   Do instead: treat `backend.local.log` and `frontend.local.log` as process stdout/stderr, and `backend/logs/app.log` as structured backend app logging.
3. **[2026-03-19] Web note generation must keep image-input mode disabled until payload handling is redesigned**
   Do instead: normalize web requests to `screenshot=False`, `video_understanding=False`, `grid_size=[]`, and strip `screenshot` from requested formats; keep screenshot mode explicit-only in CLI.

## User Directives
1. **[2026-03-19] Subagents must pin model and reasoning**
   Do instead: when spawning agents in this repo, explicitly pass `model: "gpt-5.4"` and `reasoning_effort: "xhigh"`.
