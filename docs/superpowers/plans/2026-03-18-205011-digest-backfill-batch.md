# Digest Backfill Batch Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `bilibili-up-digest` reuse existing canonical notes by default and batch missing note generation through `bilinote-cli --jobs` with structured manifests and progress logs.

**Architecture:** Split digest video handling into plan/execute stages so existing notes can be reused without invoking the generation stack. Extend `bilinote-cli` with manifest/progress outputs and partial-failure semantics, then consume that batch contract from the digest-side `bilinote_client` wrapper while preserving canonicalization inside the digest pipeline.

**Tech Stack:** Python standard library (`argparse`, `json`, `subprocess`, `tempfile`, `unittest`, `unittest.mock`), Typer CLI, existing BiliNote backend services

---

## Chunk 1: Extend `bilinote-cli` Batch Contract

### Task 1: Add failing CLI contract tests for manifest, progress, and partial failures

**Files:**
- Modify: `/Users/fanghaotian/Desktop/src/BiliNote/backend/tests/test_cli_note.py`
- Modify: `/Users/fanghaotian/Desktop/src/BiliNote/backend/app/cli/note.py`

- [ ] **Step 1: Write failing tests for batch output metadata**

Add tests covering:
- `--help` mentions `--manifest-json`, `--progress-jsonl`, and `--continue-on-error`
- batch mode writes a manifest file describing successes
- batch mode emits progress events when `--progress-jsonl` is provided
- batch mode with one failure and `--continue-on-error` still processes other items and writes manifest entries for both success and failure

- [ ] **Step 2: Run the CLI tests to verify the new tests fail**

Run:

```bash
python -m unittest /Users/fanghaotian/Desktop/src/BiliNote/backend/tests/test_cli_note.py -v
```

Expected: FAIL because the current CLI does not support the new flags or manifest/progress files.

- [ ] **Step 3: Implement the minimal CLI contract changes**

Update `/Users/fanghaotian/Desktop/src/BiliNote/backend/app/cli/note.py` to:
- accept `--manifest-json`
- accept `--progress-jsonl`
- accept `--continue-on-error`
- collect per-item success/failure metadata in batch mode
- write the manifest file on completion
- append progress events during execution
- preserve existing stdout path printing behavior for successful outputs

- [ ] **Step 4: Re-run the CLI tests to verify they pass**

Run:

```bash
python -m unittest /Users/fanghaotian/Desktop/src/BiliNote/backend/tests/test_cli_note.py -v
```

Expected: PASS for the new and existing CLI contract tests.

## Chunk 2: Add Digest-Side Batch Wrapper

### Task 2: Add failing tests for digest batch wrapper behavior

**Files:**
- Modify: `/Users/fanghaotian/.codex/skills/bilibili-up-digest/tests/test_pipeline.py`
- Modify: `/Users/fanghaotian/.codex/skills/bilibili-up-digest/scripts/bilibili_up_digest/bilinote_client.py`

- [ ] **Step 1: Write failing tests for the new batch wrapper**

Add tests covering:
- the wrapper constructs a single CLI command with multiple URLs and `--jobs`
- the wrapper reads `manifest.json` and returns successes plus failures
- the wrapper can return partial successes even when the subprocess exits nonzero if manifest data exists
- the wrapper records stdout/stderr log paths in its result

- [ ] **Step 2: Run the digest tests to verify they fail**

Run:

```bash
python -m unittest /Users/fanghaotian/.codex/skills/bilibili-up-digest/tests/test_pipeline.py -v
```

Expected: FAIL because the current client only exposes single-URL generation.

- [ ] **Step 3: Implement the minimal batch wrapper**

Update `/Users/fanghaotian/.codex/skills/bilibili-up-digest/scripts/bilibili_up_digest/bilinote_client.py` to:
- keep the single-URL helper for compatibility
- add batch result dataclasses
- create a run directory with manifest, progress, stdout, stderr, and output files
- invoke `uv run bilinote-cli <urls...> --jobs N --manifest-json ... --progress-jsonl ... --continue-on-error --output ...`
- load markdown from the output paths listed in manifest

- [ ] **Step 4: Re-run the digest tests to verify they pass**

Run:

```bash
python -m unittest /Users/fanghaotian/.codex/skills/bilibili-up-digest/tests/test_pipeline.py -v
```

Expected: PASS for the new batch wrapper tests.

## Chunk 3: Change Digest Planning And Execution Semantics

### Task 3: Add failing pipeline tests for reuse-by-default and true failure reporting

**Files:**
- Modify: `/Users/fanghaotian/.codex/skills/bilibili-up-digest/tests/test_pipeline.py`
- Modify: `/Users/fanghaotian/.codex/skills/bilibili-up-digest/scripts/bilibili_up_digest/pipeline.py`
- Modify: `/Users/fanghaotian/.codex/skills/bilibili-up-digest/scripts/build_daily_digest.py`

- [ ] **Step 1: Write failing pipeline tests**

Add tests covering:
- if a canonical note already exists for a discovered BVID, rerun reuses it without calling the markdown generator by default
- when `refresh_existing=True`, existing notes are regenerated
- daily failures section only contains true failures, not reused/skipped items
- a mixed run with existing and missing videos only invokes generation for missing videos

- [ ] **Step 2: Run the pipeline tests to verify they fail**

Run:

```bash
python -m unittest /Users/fanghaotian/.codex/skills/bilibili-up-digest/tests/test_pipeline.py -v
```

Expected: FAIL because the current pipeline refreshes all existing notes and merges warnings into the failure list.

- [ ] **Step 3: Implement the minimal pipeline restructuring**

Update `/Users/fanghaotian/.codex/skills/bilibili-up-digest/scripts/bilibili_up_digest/pipeline.py` and `/Users/fanghaotian/.codex/skills/bilibili-up-digest/scripts/build_daily_digest.py` to:
- add a `refresh_existing` control path
- separate plan entries into `reuse`, `generate`, `refresh`
- batch-generate only the non-reused items
- canonicalize batch results into target paths
- collect only actual failures into the daily render call
- keep `existing_records` fallback logic intact for backfill safety

- [ ] **Step 4: Re-run the pipeline tests to verify they pass**

Run:

```bash
python -m unittest /Users/fanghaotian/.codex/skills/bilibili-up-digest/tests/test_pipeline.py -v
```

Expected: PASS for the new reuse/failure semantics tests.

## Chunk 4: Wire CLI Flags And End-to-End Validation

### Task 4: Expose configuration and run focused end-to-end verification

**Files:**
- Modify: `/Users/fanghaotian/.codex/skills/bilibili-up-digest/SKILL.md`
- Modify: `/Users/fanghaotian/.codex/skills/bilibili-up-digest/scripts/build_daily_digest.py`
- Modify: `/Users/fanghaotian/.codex/skills/bilibili-up-digest/scripts/bilibili_up_digest/pipeline.py`

- [ ] **Step 1: Add any missing user-facing flags and docs**

Document:
- `--refresh-existing`
- `--bilinote-jobs`
- `--bilinote-batch-size`

- [ ] **Step 2: Run the focused automated test suites**

Run:

```bash
python -m unittest /Users/fanghaotian/Desktop/src/BiliNote/backend/tests/test_cli_note.py -v
python -m unittest /Users/fanghaotian/.codex/skills/bilibili-up-digest/tests/test_pipeline.py -v
```

Expected: PASS.

- [ ] **Step 3: Run a real backfill command against `2026-03-16`**

Run:

```bash
zsh -lc 'source /Users/fanghaotian/.config/shell/proxy.sh; proxy_on >/dev/null; uv run --with pyyaml --with bilibili-api-python --with curl_cffi python /Users/fanghaotian/.codex/skills/bilibili-up-digest/scripts/build_daily_digest.py --vault-root /Users/fanghaotian/Desktop/obsidian/bilibili --config /Users/fanghaotian/Desktop/obsidian/bilibili/配置/关注UP.yaml --date 2026-03-16'
```

Expected:
- existing notes are reused by default
- only missing items are sent to batch CLI
- digest writes a daily page
- failure section only contains real failures, if any

- [ ] **Step 4: Inspect outputs for correctness**

Verify:
- the daily page exists
- manifest/progress/log files exist for any batch generation
- generated counts match the daily page frontmatter
- rerunning the same command does not trigger full refresh of existing notes
