# ETF 基金跟踪表 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 新增独立 ETF 跟踪表和 CLI 管理命令，并输出当前热门行业 ETF 候选排序供用户挑选。

**Architecture:** 新建 `App/etf_store.py` 负责 `tracked_etfs` 表的建表、upsert、列表和软删除。`cli.py` 新增 `etf` Typer 子命令，只调用 `EtfStore`，不接入现有缠论分析和缓存刷新。

**Tech Stack:** Python 3.11、SQLite、Typer、pytest。

---

### Task 1: ETF 存储

**Files:**
- Create: `App/etf_store.py`
- Create: `tests/test_etf_store.py`

- [ ] 写入失败测试：初始化表、写入观察 ETF、转持仓、清仓后成本清空、软删除。
- [ ] 运行 `pytest tests/test_etf_store.py -q --basetemp .pytest-tmp -p no:cacheprovider`，确认因为 `App.etf_store` 不存在而失败。
- [ ] 实现 `EtfStore.initialize()`、`set_position()`、`list_positions()`、`delete_position()`。
- [ ] 运行同一测试，确认通过。

### Task 2: ETF CLI

**Files:**
- Modify: `cli.py`
- Modify: `tests/test_unified_cli.py`

- [ ] 写入失败测试：`etf init`、`etf set`、`etf list`、`etf delete` 能管理同一张 `tracked_etfs` 表。
- [ ] 运行目标测试，确认 `etf` 子命令不存在而失败。
- [ ] 在 `cli.py` 注册 `etf_app`，新增 `init`、`set`、`list`、`delete` 命令。
- [ ] 运行目标测试，确认通过。

### Task 3: 文档与热门候选

**Files:**
- Modify: `docs/cli.md`
- Create: `output/hot_industry_etfs_2026-06-30.md`

- [ ] 更新 CLI 文档，说明 `tracked_etfs` 表和 `etf` 子命令。
- [ ] 联网核对当前行业 ETF 主题和代表基金，按综合热度输出候选排序。
- [ ] 运行 ETF 相关测试和必要 CLI 测试。
- [ ] 删除本次创建的 `.pytest-tmp*` 临时目录。
