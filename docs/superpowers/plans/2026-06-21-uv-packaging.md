# uv Packaging Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the repository installable and reproducibly managed with uv.

**Architecture:** A root `pyproject.toml` will declare the `chanpy` distribution, its runtime dependencies, and Hatchling’s explicit inclusion of the existing flat source tree. `uv.lock` will resolve those dependencies; `uv sync` will recreate the unusable virtual environment and install the project editable.

**Tech Stack:** Python 3.11+, uv, Hatchling, pytest.

---

### Task 1: Establish the uv project metadata

**Files:**
- Create: `pyproject.toml`
- Reference: `Script/requirements.txt`

- [ ] **Step 1: Record the existing dependency contract**

Run: `Get-Content -Raw Script/requirements.txt`

Expected: six runtime requirements: baostock, ipython, matplotlib, numpy, pandas, and requests.

- [ ] **Step 2: Create the minimal package configuration**

Create `pyproject.toml` with this content:

```toml
[build-system]
requires = ["hatchling>=1.27"]
build-backend = "hatchling.build"

[project]
name = "chanpy"
version = "0.1.0"
description = "Chan theory analysis library"
readme = "README.md"
requires-python = ">=3.11"
license = { file = "LICENSE" }
dependencies = [
  "baostock>=0.8.8",
  "ipython>=8.5.0",
  "matplotlib>=3.5.3",
  "numpy>=1.23.3",
  "pandas>=1.4.2",
  "requests>=2.22.0",
]

[dependency-groups]
dev = ["pytest>=8.0"]

[tool.hatch.build.targets.wheel]
include = [
  "/App",
  "/Bi",
  "/BuySellPoint",
  "/ChanModel",
  "/Combiner",
  "/Common",
  "/DataAPI",
  "/KLine",
  "/Math",
  "/Plot",
  "/Seg",
  "/ZS",
  "/Chan.py",
  "/ChanConfig.py",
]
```

- [ ] **Step 3: Validate TOML metadata before resolving dependencies**

Run: `uv lock --check`

Expected: exit code 1 because `uv.lock` does not exist yet, but no TOML or build-configuration parsing error.

- [ ] **Step 4: Commit the metadata**

```powershell
git add pyproject.toml
git commit -m "build: add uv project metadata"
```

### Task 2: Resolve and install the project

**Files:**
- Create: `uv.lock`
- Modify: `.venv/` (generated, untracked)

- [ ] **Step 1: Generate the lockfile**

Run: `uv lock`

Expected: exit code 0 and a new `uv.lock` that resolves Python 3.11-compatible runtime and development dependencies.

- [ ] **Step 2: Synchronize the managed environment**

Run: `uv sync --all-groups`

Expected: exit code 0; uv recreates or repairs `.venv` and installs `chanpy` editable plus the `dev` group.

- [ ] **Step 3: Verify the interpreter and dependency graph**

Run: `uv run python --version; uv run python -m pip check`

Expected: Python 3.11 or later and `No broken requirements found.`

- [ ] **Step 4: Verify the installed project imports**

Run: `uv run python -c "from Chan import CChan; from ChanConfig import CChanConfig; print(CChan.__name__, CChanConfig.__name__)"`

Expected: `CChan CChanConfig`.

- [ ] **Step 5: Verify the test runner is available**

Run: `uv run pytest`

Expected: exit code 5 with `no tests ran` is acceptable because the repository currently contains no test files; any collection/import error is a failure to investigate.

- [ ] **Step 6: Commit the reproducible dependency state**

```powershell
git add uv.lock
git commit -m "build: lock uv dependencies"
```
