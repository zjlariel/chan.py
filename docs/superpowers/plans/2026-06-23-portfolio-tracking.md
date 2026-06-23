# 单表持仓与观察股跟踪 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 SQLite 中跟踪观察股和持仓股，并用一个命令输出面向买点或卖点的缠论提示。

**Architecture:** `PortfolioStore` 只负责 `tracked_stocks` 表；`portfolio` CLI 负责管理记录和编排已有 `CChan` 分析；信号格式化模块只消费分析对象，绝不修改缠论计算。

**Tech Stack:** Python 3.11、SQLite、Typer、pytest。

---

### Task 1: 持仓表存储

**Files:**
- Create: `App/portfolio_store.py`
- Create: `tests/test_portfolio_store.py`

- [ ] 写入失败测试，覆盖建表、观察股写入、买入后更新数量和成本。
- [ ] 运行 `pytest tests/test_portfolio_store.py -v`，确认模块缺失。
- [ ] 实现表创建、upsert、列表读取与状态派生。
- [ ] 运行同一测试，确认通过。

### Task 2: 规则化分析摘要

**Files:**
- Create: `App/portfolio_analysis.py`
- Create: `tests/test_portfolio_analysis.py`

- [ ] 写入失败测试，覆盖持仓卖点提示与观察股买点提示。
- [ ] 运行 `pytest tests/test_portfolio_analysis.py -v`，确认模块缺失。
- [ ] 实现基于最新排序买卖点和成本价的纯格式化函数。
- [ ] 运行同一测试，确认通过。

### Task 3: CLI 命令

**Files:**
- Modify: `cli.py`
- Modify: `tests/test_unified_cli.py`
- Modify: `docs/cli.md`

- [ ] 写入失败测试，覆盖初始化、统一设置和按持仓/观察分类的分析输出。
- [ ] 运行目标 CLI 测试，确认新命令不存在。
- [ ] 注册 `portfolio` 子命令并调用存储与分析模块。
- [ ] 更新中文命令文档。
- [ ] 运行完整相关测试。
