# 命令行工具

项目通过 `pyproject.toml` 注册入口：

```toml
[project.scripts]
chanpy = "cli:app"
```

安装后可直接使用 `chanpy`，未安装时也可用 `python cli.py` 或 `uv run chanpy` 运行。

---

## analyze：缠论 K 线分析与绘图

```bash
chanpy analyze [OPTIONS]
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
| `--json` | 导出笔、线段、中枢与买卖点等计算结果 | 关闭 |
| `--figure` | 生成 PNG 图片输出 | 关闭 |

未提供 `--start` 时，默认回溯天数如下：

| 级别 | 回溯天数 |
| --- | ---: |
| `K_WEEK` | 2400 |
| `K_DAY` | 1200 |
| `K_30M` | 180 |
| `K_5M` | 20 |

### 示例

```bash
chanpy analyze --code sz.002536
chanpy analyze --code sz.002536 --json
chanpy analyze --code sz.002536 --json --figure
chanpy analyze --code sh.600000 --start 2024-01-01 --end 2025-12-31
chanpy analyze --data-src baostock --code sz.000001 --kl-type K_DAY --output-dir images
```

默认执行会在终端打印各级别的简洁摘要，包括数据范围、笔、线段、中枢数量、最后一个中枢区间和最新买卖点。默认不会写入图片或 JSON 文件；分别使用 `--figure`、`--json` 按需生成。

`--data-src cache` 时会按级别分别输出图片，例如：

- `output/sz.002536_K_WEEK.png`
- `output/sz.002536_K_DAY.png`
- `output/sz.002536_K_30M.png`
- `output/sz.002536_K_5M.png`

`--json` 会生成 `output/sz.002536_analysis.json`。它包含每个级别的时间范围、笔、线段、线段线段、中枢和买卖点；K 线 OHLCV 数据不重复导出，可直接从 SQLite 缓存查询。

---

## cache update：刷新缓存数据

```bash
chanpy cache update [OPTIONS]
```

### 参数

| 参数 | 说明 | 默认值 |
| --- | --- | --- |
| `--mode` | 刷新模式：`auto`、`live` 或 `eod` | `auto` |
| `--codes` | 逗号分隔的股票代码 | 必填 |
| `--full` | 从完整保留窗口重新拉取，而非增量更新 | 关闭 |
| `--cache-path` | SQLite 缓存文件路径 | `.chanpy/cache.sqlite3` |

- `live` 模式：从新浪刷新分钟级别数据（`K_1M`、`K_5M`、`K_15M`、`K_30M`、`K_60M`）。
- `eod` 模式：从 Baostock 刷新 `K_WEEK`、`K_DAY`、`K_60M`、`K_30M`、`K_15M`、`K_5M`，跳过 `K_1M`。
- `auto` 模式：分钟周期中，昨天及更早的数据使用 Baostock，当天数据始终使用新浪；日线与周线仅刷新到昨天。
- 默认更新只回拉每个周期最后缓存时间前 3 天的重叠区间；首次缺少完整覆盖记录时才拉取完整窗口。成功后会裁剪窗口外的旧数据。

### 示例

```bash
chanpy cache update --mode live --codes 600000,000001
chanpy cache update --mode eod --codes sz.002536 --cache-path .chanpy/cache.sqlite3
```

---

## cache status：查看缓存状态

```bash
chanpy cache status [OPTIONS]
```

### 参数

| 参数 | 说明 | 默认值 |
| --- | --- | --- |
| `--cache-path` | SQLite 缓存文件路径 | `.chanpy/cache.sqlite3` |

### 示例

```bash
chanpy cache status
chanpy cache status --cache-path .chanpy/cache.sqlite3
```
