# 离线数据缓存 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a SQLite-backed, source-aware offline K-line cache and one-shot update CLI.

**Architecture:** `CacheStore` owns durable rows and coverage metadata. `CCache` uses it for normal `CChan` reads and asks a source selector for missing data. `App.cache_cli` invokes the same updater so external schedulers do not duplicate cache logic.

**Tech Stack:** Python 3.11, sqlite3, argparse, pytest, unittest.mock.

---

### Task 1: Add the tested SQLite cache store

**Files:**
- Create: `DataAPI/CacheStore.py`
- Create: `tests/test_cache_store.py`

- [x] Write tests for row upsert, ordered range reads, and coverage records.
- [x] Run them and verify failure because the store is absent.
- [x] Implement the smallest SQLite schema and store API.
- [x] Re-run tests and verify pass.

### Task 2: Add source-aware cached reads

**Files:**
- Create: `DataAPI/CacheAPI.py`
- Modify: `Common/CEnum.py`
- Modify: `Chan.py`
- Create: `tests/test_cache_api.py`

- [x] Write failing tests for cached return, live Sina selection, end-of-day Baostock selection, and K_1M end-of-day skip.
- [x] Implement `CCache` and register `DATA_SRC.CACHE`.
- [x] Run focused tests and verify pass.

### Task 3: Add one-shot external-scheduler commands

**Files:**
- Create: `App/cache_cli.py`
- Create: `tests/test_cache_cli.py`
- Modify: `.gitignore`

- [x] Write failing CLI tests for `update` and `status` argument handling.
- [x] Implement the CLI and ignore `.chanpy/`.
- [x] Run full suite plus `uv lock --check` and `uv sync --check`.
