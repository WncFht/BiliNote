# BiliNote Backend uv Migration Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Migrate the backend from `pip + requirements.txt` to `uv + pyproject.toml + uv.lock`, and update local development and Docker workflows accordingly.

**Architecture:** Keep the repository layout intact, but turn [backend](/Users/fanghaotian/Desktop/src/BiliNote/.worktrees/uv-migration/backend) into the canonical Python project. The backend will become a non-packaged `uv` application with pinned runtime dependencies, an optional GPU dependency group, and Docker images that install from the lockfile for reproducible builds in domestic-network-friendly environments.

**Tech Stack:** `uv`, `pyproject.toml`, `uv.lock`, FastAPI, Docker, Docker Compose, `pnpm`

---

## Chunk 1: uv Project Bootstrap

### Task 1: Create the backend uv project metadata

**Files:**
- Create: `/Users/fanghaotian/Desktop/src/BiliNote/.worktrees/uv-migration/backend/pyproject.toml`
- Create: `/Users/fanghaotian/Desktop/src/BiliNote/.worktrees/uv-migration/backend/uv.lock`
- Modify: `/Users/fanghaotian/Desktop/src/BiliNote/.worktrees/uv-migration/.gitignore`

- [ ] **Step 1: Generate the bare uv project in `backend/`**

Run: `uv init --bare --app --no-package --no-readme --no-pin-python --vcs none backend`
Expected: `backend/pyproject.toml` exists with a minimal app configuration.

- [ ] **Step 2: Import the current pinned requirements as raw dependencies**

Run: `cd backend && uv add --requirements requirements.txt --raw --frozen`
Expected: `project.dependencies` contains the runtime dependencies from `requirements.txt`.

- [ ] **Step 3: Add the GPU-only dependency as an optional extra**

Run: `cd backend && uv add --optional gpu --raw "transformers[torch]>=4.23"`
Expected: `project.optional-dependencies.gpu` exists and includes the transformer extra previously installed only in the GPU Dockerfile.

- [ ] **Step 4: Normalize metadata and uv settings**

Edit `backend/pyproject.toml` to:
- set a clear project name and description
- set `requires-python` to match the Docker base image (`>=3.11`)
- mark the project as non-packaged if uv didn’t already
- add domestic mirror defaults in `tool.uv` config where appropriate

- [ ] **Step 5: Update ignore rules**

Ensure `.worktrees/` is ignored in the repository root `.gitignore`.

## Chunk 2: Local Developer Workflow

### Task 2: Replace pip-first instructions with uv-first commands

**Files:**
- Modify: `/Users/fanghaotian/Desktop/src/BiliNote/.worktrees/uv-migration/README.md`
- Modify: `/Users/fanghaotian/Desktop/src/BiliNote/.worktrees/uv-migration/.env.example`
- Modify: `/Users/fanghaotian/Desktop/src/BiliNote/.worktrees/uv-migration/backend/.env.example`

- [ ] **Step 1: Document the new backend bootstrap commands**

Update local setup docs to use:
- `cd backend && uv sync`
- `cd backend && uv run python main.py`

- [ ] **Step 2: Document mirror-friendly setup**

Add a short section for domestic users describing:
- optional `UV_DEFAULT_INDEX`
- optional proxy usage
- continued `HF_ENDPOINT=https://hf-mirror.com`

- [ ] **Step 3: Clarify required vs optional secrets**

Update env example documentation so users can quickly see:
- required model provider keys for summarization
- optional keys for alternate transcribers/providers
- optional Bilibili cookie path for subtitle extraction

## Chunk 3: Docker Migration

### Task 3: Convert Docker images from pip to uv

**Files:**
- Modify: `/Users/fanghaotian/Desktop/src/BiliNote/.worktrees/uv-migration/backend/Dockerfile`
- Modify: `/Users/fanghaotian/Desktop/src/BiliNote/.worktrees/uv-migration/backend/Dockerfile.gpu`

- [ ] **Step 1: Install uv in both images**

Use the existing domestic apt/pypi-friendly posture while ensuring `uv` is available in the image.

- [ ] **Step 2: Optimize layer caching for lockfile-based installs**

Copy `backend/pyproject.toml` and `backend/uv.lock` before the full backend source tree, then run:
- CPU: `uv sync --frozen --no-dev`
- GPU: `uv sync --frozen --no-dev --extra gpu`

- [ ] **Step 3: Preserve runtime behavior**

Keep existing environment defaults, `ffmpeg`, and `HF_ENDPOINT`, and ensure the container still starts with `python main.py` or an equivalent `uv run` command.

## Chunk 4: Verification

### Task 4: Verify the new uv workflow works end to end

**Files:**
- No new files required

- [ ] **Step 1: Sync the backend environment**

Run: `cd backend && uv sync`
Expected: `.venv` is created and dependencies install successfully.

- [ ] **Step 2: Run a lightweight backend smoke check**

Run: `cd backend && uv run python -m compileall .`
Expected: Python sources compile without syntax errors.

- [ ] **Step 3: Validate Dockerfiles**

Run:
- `docker build -f backend/Dockerfile .`
- `docker build -f backend/Dockerfile.gpu .`
Expected: both images build successfully, or any platform-specific blocker is captured explicitly.

- [ ] **Step 4: Check the final diff**

Run: `git status --short`
Expected: only the intended uv, Docker, and documentation files are modified.
