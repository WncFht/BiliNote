# Shared History Sync Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make web note history visible across devices by hydrating frontend task state from backend task/result files instead of relying only on browser-local persistence.

**Architecture:** Add a backend history listing endpoint that joins task IDs from the database with status/result artifacts from `note_results`, then map that payload into frontend `Task` records through a small pure TypeScript merge helper. Keep local pending-task state and form snapshots, but treat backend history as the source of truth for shared task status/result data.

**Tech Stack:** FastAPI, SQLAlchemy, React 19, Zustand, TypeScript, `unittest`, `node:test`

---

## File Map

- Create: `backend/tests/test_note_history.py`
- Create: `BillNote_frontend/src/lib/historySync.ts`
- Create: `BillNote_frontend/tests/historySync.test.ts`
- Modify: `backend/app/db/video_task_dao.py`
- Modify: `backend/app/routers/note.py`
- Modify: `BillNote_frontend/src/services/note.ts`
- Modify: `BillNote_frontend/src/store/taskStore/index.ts`
- Modify: `BillNote_frontend/src/App.tsx`

## Chunk 1: Backend shared-history serialization

### Task 1: Add failing backend tests for history entry serialization

**Files:**
- Create: `backend/tests/test_note_history.py`
- Test: `backend/app/routers/note.py`
- Test: `backend/app/db/video_task_dao.py`

- [ ] **Step 1: Write the failing tests**

```python
def test_serialize_task_history_entry_reads_result_file():
    ...

def test_get_task_history_returns_latest_tasks():
    ...
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && .venv/bin/python -m unittest tests.test_note_history`
Expected: FAIL because history serialization/listing helpers do not exist yet

- [ ] **Step 3: Write minimal implementation**

```python
def list_video_tasks(limit: int = 50): ...
def serialize_task_history_entry(task_row) -> dict: ...
@router.get("/task_history")
def get_task_history(limit: int = 50): ...
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && .venv/bin/python -m unittest tests.test_note_history`
Expected: PASS

## Chunk 2: Frontend hydration and merge behavior

### Task 2: Add failing frontend tests for history mapping and merge semantics

**Files:**
- Create: `BillNote_frontend/src/lib/historySync.ts`
- Create: `BillNote_frontend/tests/historySync.test.ts`
- Test: `BillNote_frontend/src/store/taskStore/index.ts`

- [ ] **Step 1: Write the failing tests**

```ts
test('mapHistoryItemToTask converts backend payload to frontend task shape', () => {
  ...
})

test('mergeHydratedTasks preserves local formData while accepting remote result data', () => {
  ...
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `node --test BillNote_frontend/tests/historySync.test.ts`
Expected: FAIL because the helper module does not exist yet

- [ ] **Step 3: Write minimal implementation**

```ts
export function mapHistoryItemToTask(item: ServerHistoryItem): Task
export function mergeHydratedTasks(existing: Task[], incoming: Task[]): Task[]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `node --test BillNote_frontend/tests/historySync.test.ts`
Expected: PASS

### Task 3: Wire frontend hydration into app startup

**Files:**
- Modify: `BillNote_frontend/src/services/note.ts`
- Modify: `BillNote_frontend/src/store/taskStore/index.ts`
- Modify: `BillNote_frontend/src/App.tsx`

- [ ] **Step 1: Re-run helper test before component/store changes**

Run: `node --test BillNote_frontend/tests/historySync.test.ts`
Expected: PASS

- [ ] **Step 2: Implement minimal hydration flow**

```ts
export const getTaskHistory = async () => request.get('/task_history')
```

```ts
loadTaskHistory: async () => {
  const history = await getTaskHistory()
  set(state => ({ tasks: mergeHydratedTasks(state.tasks, history.map(mapHistoryItemToTask)) }))
}
```

```ts
useEffect(() => {
  if (initialized) void loadTaskHistory()
}, [initialized, loadTaskHistory])
```

- [ ] **Step 3: Run tests/build verification**

Run: `node --test BillNote_frontend/tests/historySync.test.ts BillNote_frontend/tests/providerErrors.test.ts BillNote_frontend/tests/noteSubmission.test.ts`
Expected: PASS

## Chunk 3: Verification

- [ ] Run: `cd backend && .venv/bin/python -m unittest tests.test_note_router tests.test_note_router_security tests.test_note_history`
- [ ] Run: `zsh -lc 'source /Users/fanghaotian/.config/shell/proxy.sh && proxy_on >/dev/null && uv run --project backend pytest backend/tests/test_note_router.py backend/tests/test_note_router_security.py backend/tests/test_note_history.py -q'`
- [ ] Run: `node --test BillNote_frontend/tests/homeLayout.test.ts BillNote_frontend/tests/settingsLayout.test.ts BillNote_frontend/tests/taskProgress.test.ts BillNote_frontend/tests/providerErrors.test.ts BillNote_frontend/tests/noteSubmission.test.ts BillNote_frontend/tests/historySync.test.ts`
- [ ] Run: `cd BillNote_frontend && npm run build`
- [ ] Run: `cd BillNote_frontend && npm run lint`
