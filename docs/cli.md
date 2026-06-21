# 命令行工具

本仓库提供统一的 Typer 命令行入口 `cli.py`，同时保留原有的独立入口作为兼容实现。

- `python cli.py`：统一的 Typer 命令行入口，包含分析与缓存两大子命令。
- `python main.py`：基于 `argparse` 的分析绘图入口（兼容入口）。
- `python -m App.cache_cli`：基于 `argparse` 的缓存管理入口（兼容入口）。

---

## 一、统一入口 `cli.py`

### 安装与使用

项目依赖中包含 `typer`，执行以下命令即可使用：

```bash
uv sync
python cli.py --help
```

如果通过 `pip install -e .` 或 `uv pip install -e .` 安装，还会生成可执行命令：

```bash
chanpy --help
```

> 入口命令在 `pyproject.toml` 中注册：
> ```toml
> [project.scripts]
> chanpy = "cli:app"
> ```

### 顶层命令

```text
python cli.py [OPTIONS] COMMAND [ARGS]...
```

| 全局选项 | 说明 |
| --- | --- |
| `--install-completion` | 为当前 shell 安装命令补全 |
| `--show-completion` | 显示补全脚本 |
| `--help` | 显示帮助信息 |

### 子命令

- `analyze`：缠论 K 线分析与绘图
- `cache`：离线缓存管理（包含 `update`、`status`）

---

## 二、分析绘图命令 `analyze`

### 功能

默认先查询本地 SQLite 缓存；未命中的周线、日线、30 分钟和 5 分钟数据会按各自默认回溯窗口由 Baostock 补齐并写入缓存，随后运行缠论计算并保存 PNG 图片。显式指定其他数据源时，保留直接读取该数据源的行为。

### 命令

```bash
python cli.py analyze [OPTIONS]
```

### 参数

| 参数 | 说明 | 默认值 |
| --- | --- | --- |
| `--data-src` | 数据源：`cache`、`baostock`、`akshare`、`ccxt`、`csv`、`sina` | `cache` |
| `--code` | 股票或交易标的代码 | `sz.000001` |
| `--start` | 起始日期，格式 `YYYY-MM-DD` | 按级别自动回溯 |
| `--end` | 结束日期，格式 `YYYY-MM-DD` | 获取至最新数据 |
| `--kl-type` | 逗号分隔的 K 线级别 | `K_WEEK,K_DAY,K_30M,K_5M` |
| `--output-dir` | 图片输出目录 | `output` |

未提供 `--start` 时，CLI 按当前自然日为每个选中级别计算默认起始日期：

| 级别 | 回溯天数 |
| --- | ---: |
| `K_WEEK` | 2400 天 |
| `K_DAY` | 1200 天 |
| `K_30M` | 180 天 |
| `K_5M` | 20 天 |

其它级别在未显式提供 `--start` 时传入 `None`。

### 示例

```bash
python cli.py analyze \
  --code sh.600000 \
  --start 2024-01-01 \
  --end 2025-12-31 \
  --kl-type K_WEEK,K_DAY,K_30M,K_5M \
  --output-dir output
```

缓存模式会按级别分别执行分析，生成：

- `output/sh.600000_K_WEEK.png`
- `output/sh.600000_K_DAY.png`
- `output/sh.600000_K_30M.png`
- `output/sh.600000_K_5M.png`

---

## 三、缓存管理命令 `cache`

### 功能

为 `DATA_SRC.CACHE` 维护本地 SQLite 缓存。盘中可由新浪补齐分钟线缺口，盘后可由 Baostock 刷新日线及以上/非 1 分钟周期数据；外部调度器（如 cron、Task Scheduler、CI）可定期调用此 CLI，无需重复实现缓存逻辑。

默认缓存文件：`.chanpy/cache.sqlite3`

### 命令

```bash
python cli.py cache <subcommand> [OPTIONS]
```

### `cache update`：刷新缓存

| 参数 | 说明 | 默认值 |
| --- | --- | --- |
| `--mode` | 刷新模式：`live`（盘中）或 `eod`（盘后） | 必填 |
| `--codes` | 逗号分隔的股票代码 | 必填 |
| `--cache-path` | SQLite 缓存文件路径 | `.chanpy/cache.sqlite3` |

- `live` 模式：使用新浪刷新分钟级别（`K_1M`、`K_5M`、`K_15M`、`K_30M`、`K_60M`）。
- `eod` 模式：使用 Baostock 刷新 `K_WEEK`、`K_DAY`、`K_60M`、`K_30M`、`K_15M`、`K_5M`，跳过 `K_1M`。

### `cache status`：查看缓存状态

| 参数 | 说明 | 默认值 |
| --- | --- | --- |
| `--cache-path` | SQLite 缓存文件路径 | `.chanpy/cache.sqlite3` |

### 示例

盘中补 1/5/15/30/60 分钟线：

```bash
python cli.py cache update --mode live --codes 600000,000001
```

盘后刷新日线及以上、非 1 分钟周期：

```bash
python cli.py cache update --mode eod --codes 600000
```

查看缓存汇总：

```bash
python cli.py cache status
```

---

## 四、兼容入口

### `python main.py`

基于 `argparse` 的分析绘图入口，参数与 `cli.py analyze` 保持一致。实现位于 `cli_args.py`。

```bash
python main.py \
  --data-src baostock \
  --code sz.000001 \
  --start 2025-01-01 \
  --end 2026-01-01 \
  --kl-type K_WEEK,K_DAY,K_30M,K_5M \
  --output-dir output
```

### `python -m App.cache_cli`

基于 `argparse` 的缓存管理入口，参数与 `cli.py cache` 保持一致。实现位于 `App/cache_cli.py`。

```bash
python -m App.cache_cli update --mode live --codes 600000,000001
python -m App.cache_cli status
```

---

## 五、数据源速查

| 数据源 | 入口 | 说明 |
| --- | --- | --- |
| `baostock` | `cli.py analyze --data-src baostock` | 日线及以上、分钟线（无 1 分钟） |
| `sina` | `cli.py analyze --data-src sina` | 1/5/15/30/60 分钟线 |
| `cache` | `cli.py analyze --data-src cache` | 优先读取本地缓存，缺数据时按盘中/盘后策略自动刷新 |

---

## 六、环境要求

- Python >= 3.11
- 依赖：`typer`、`matplotlib`、`pandas` 等（见 `pyproject.toml`）
- 使用 `uv` 管理依赖：`uv sync`
- 运行测试：`uv run pytest`
