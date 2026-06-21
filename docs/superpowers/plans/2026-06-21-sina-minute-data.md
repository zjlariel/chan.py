# 新浪分钟数据 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a Sina-backed real-time A-share minute-bar data source.

**Architecture:** `CSina` will translate existing symbols and `KL_TYPE` values into Sina request parameters, validate the response, filter by the existing date bounds, and yield normal `CKLine_Unit` values. The existing data-source enum and factory will expose the adapter without changing callers.

**Tech Stack:** Python 3.11, requests, pytest, unittest.mock.

---

### Task 1: Define test coverage for the adapter

**Files:**
- Create: `tests/test_sina_api.py`

- [ ] **Step 1: Write tests for code normalization and supported periods**

Test `600000`, `sz.000001`, and unsupported codes; assert all five minute `KL_TYPE` values map to Sina scales and a daily period raises an error.

- [ ] **Step 2: Run the test to verify it fails**

Run: `uv run pytest tests/test_sina_api.py -v`

Expected: FAIL because `DataAPI.SinaAPI` does not exist.

- [ ] **Step 3: Implement the minimal `CSina` adapter**

Create `DataAPI/SinaAPI.py` with HTTP request, normalization, response validation, `CKLine_Unit` conversion, and range filtering.

- [ ] **Step 4: Run the focused tests**

Run: `uv run pytest tests/test_sina_api.py -v`

Expected: PASS.

### Task 2: Register and verify the new data source

**Files:**
- Modify: `Common/CEnum.py`
- Modify: `Chan.py`
- Modify: `tests/test_sina_api.py`

- [ ] **Step 1: Write a failing dispatch test**

Assert `DATA_SRC.SINA` is accepted by `CChan.GetStockAPI` and resolves to `CSina`.

- [ ] **Step 2: Run the dispatch test to verify it fails**

Run: `uv run pytest tests/test_sina_api.py -v`

Expected: FAIL because `DATA_SRC.SINA` is not registered.

- [ ] **Step 3: Add enum and factory registration**

Add `SINA` to `DATA_SRC`; import and return `CSina` in `GetStockAPI`.

- [ ] **Step 4: Run focused and full verification**

Run: `uv run pytest -v; uv lock --check; uv sync --check`

Expected: all tests pass and uv reports an up-to-date lockfile and synchronized environment.
