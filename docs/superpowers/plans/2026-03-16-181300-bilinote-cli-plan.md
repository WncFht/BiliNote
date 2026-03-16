# BiliNote CLI Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a `bilinote-cli` command that generates Markdown notes from a Bilibili URL without starting frontend/backend services, then package that flow into a Codex skill.

**Architecture:** Reuse backend bootstrap and `NoteGenerator.generate()` directly from a new CLI module. Keep defaults aligned with the user's current local setup and expose only `--style` and screenshot toggles in v1.

**Tech Stack:** Python 3.11+, Typer, uv, unittest, Codex skill metadata

---

## Chunk 1: CLI Contract

### Task 1: Add failing CLI tests

**Files:**
- Create: `backend/tests/test_cli_note.py`
- Create: `backend/app/cli/__init__.py`
- Create: `backend/app/cli/note.py`

- [ ] **Step 1: Write the failing tests**
- [ ] **Step 2: Run `uv run python -m unittest tests.test_cli_note` and verify it fails because the CLI module or entrypoint is missing**
- [ ] **Step 3: Implement the minimum CLI surface**
- [ ] **Step 4: Run `uv run python -m unittest tests.test_cli_note` and verify it passes**

## Chunk 2: CLI Integration

### Task 2: Wire CLI into backend bootstrap and defaults

**Files:**
- Modify: `backend/pyproject.toml`
- Modify: `backend/app/cli/note.py`
- Modify: `README.md`

- [ ] **Step 1: Write failing tests for default provider/model/style/screenshot mapping**
- [ ] **Step 2: Run the targeted tests and verify they fail for the expected assertion**
- [ ] **Step 3: Implement bootstrap + NoteGenerator integration**
- [ ] **Step 4: Re-run the tests and verify they pass**

## Chunk 3: Skill Packaging

### Task 3: Add a Codex skill that wraps the CLI

**Files:**
- Create: `/Users/fanghaotian/.codex/skills/bilinote-video-note/SKILL.md`

- [ ] **Step 1: Create the skill after the CLI command is stable**
- [ ] **Step 2: Run one real CLI command through the skill instructions**
- [ ] **Step 3: Verify the command produces a Markdown note**

## Chunk 4: Real Validation

### Task 4: Prove the full flow works on a Bilibili link

**Files:**
- Modify: `backend/tests/test_cli_note.py`
- Modify: `README.md`

- [ ] **Step 1: Run `uv run python -m unittest tests.test_cli_note tests.test_mlx_whisper_transcriber`**
- [ ] **Step 2: Run `uv run bilinote-cli "<bilibili_url>"` against a real Bilibili URL**
- [ ] **Step 3: Confirm the generated Markdown path and key output files exist**
- [ ] **Step 4: Commit the finished work**
