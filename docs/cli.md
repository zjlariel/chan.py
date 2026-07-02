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
| `--codes` | 逗号分隔的股票或 ETF 代码 | 关闭 |
| `--all` | 更新 `tracked_stocks` 表中全部启用股票 | 关闭 |
| `--all-etfs` | 更新 `tracked_etfs` 表中全部启用 ETF | 关闭 |
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
chanpy cache update --all
chanpy cache update --all-etfs --mode eod
```

`--all` 会读取 SQLite 中 `tracked_stocks` 表的全部启用股票，并按指定模式更新。`--all-etfs` 会读取 `tracked_etfs` 表的全部启用 ETF。`--codes`、`--all`、`--all-etfs` 三者必须且只能指定一个。

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

---

## portfolio：持仓与观察股跟踪

持仓与观察股都存储在缓存 SQLite 的 `tracked_stocks` 表中：数量为 `0` 表示观察股，数量大于 `0` 表示持仓股。

```bash
chanpy portfolio init
chanpy portfolio list
chanpy portfolio set --code 000001 --name 平安银行 --quantity 0
chanpy portfolio set --code 002536 --name 飞龙股份 --quantity 400 --available 400 --cost-price 41.343
chanpy portfolio delete --code 002460
chanpy portfolio analyze
chanpy portfolio analyze --refresh
chanpy portfolio analyze --code 002050 --refresh
chanpy portfolio analyze --output-dir output
```

`portfolio delete --code <代码>` 会把股票从当前股票池中移除；这是软删除，只会将 `tracked_stocks.active` 标记为 `0`，不会物理删除历史记录、成本价、备注等信息。删除后该股票不会出现在 `portfolio list`、`portfolio analyze` 和 `cache update --all` 的启用股票范围内。后续可再次使用 `portfolio set` 重新加入。

`portfolio analyze` 使用周线作为趋势背景、日线作为决策级别、30 分钟作为确认级别；不使用 5 分钟信号。分析结果默认保存为两份文件：`output/portfolio_model_YYYY-MM-DD.json` 给大模型做结构化分析，`output/portfolio_summary_YYYY-MM-DD.txt` 给人快速扫盘；可用 `--output-dir` 指定输出目录。持仓股同时显示卖点风险和加仓候选，观察股显示买点与关注优先级。它是规则化技术分析提示，不会自动执行交易。

使用 `portfolio analyze --code <代码>` 分析未写入跟踪表的股票时，会以“临时观察股”身份分析，不会自动保存到数据库。

---

## etf：ETF 基金跟踪

ETF 基金单独存储在缓存 SQLite 的 `tracked_etfs` 表中，不与 A 股股票池 `tracked_stocks` 混用。数量为 `0` 表示观察 ETF，数量大于 `0` 表示持仓 ETF。

```bash
chanpy etf init
chanpy etf list
chanpy etf set --code 513130 --name 恒生科技ETF --quantity 0 --category 港股科技 --tracking-index 恒生科技指数
chanpy etf set --code 159995 --name 芯片ETF --quantity 10000 --available 10000 --cost-price 1.250 --category 半导体
chanpy etf delete --code 513130
chanpy etf analyze
chanpy etf analyze --refresh
chanpy etf analyze --code 159530 --output-dir output
```

`etf delete --code <代码>` 是软删除，只会将 `tracked_etfs.active` 标记为 `0`，不会物理删除历史记录、成本价、分类和备注。

ETF 命令负责跟踪表管理和批量缠论跟踪；ETF 的 K 线刷新通过 `cache update` 完成，ETF 池的批量分析通过 `etf analyze` 完成。场内 ETF 支持裸码或带交易所前缀，`15` 开头默认深市，`51`、`56`、`58` 开头默认沪市；ETF 默认使用不复权口径。

ETF 的日线和周线 EOD 缓存优先使用东方财富历史行情，以获得更完整的长期数据；ETF 分钟线仍按缓存刷新模式使用 Baostock 或新浪。

```bash
chanpy cache update --codes 513130 --mode eod
chanpy cache update --codes 159530 --mode eod
chanpy cache update --all-etfs --mode eod
```

`etf analyze` 使用周线作为趋势背景、日线作为决策级别、30 分钟作为确认级别；不使用 5 分钟信号。它会读取 `tracked_etfs` 表里的全部启用 ETF，默认保存两份文件：`output/etf_model_YYYY-MM-DD.json` 给大模型做结构化分析，`output/etf_summary_YYYY-MM-DD.txt` 给人快速扫盘。`--refresh` 会先按 `auto` 模式刷新每只 ETF 的分析级别缓存；`--code <代码>` 可以只分析某一只已跟踪 ETF。

```bash
chanpy etf analyze
chanpy etf analyze --refresh
chanpy etf analyze --code 159530 --output-dir output
```

如果要每天跟踪整个 ETF 池，推荐流程是先刷新全部启用 ETF，再一键生成 ETF 池的缠论跟踪报告：

```bash
chanpy cache update --all-etfs --mode eod --cache-path .chanpy/cache.sqlite3
chanpy etf analyze --cache-path .chanpy/cache.sqlite3 --output-dir output
```

需要给单只 ETF 额外出图或导出底层缠论 JSON 时，再使用通用 `analyze` 命令：

```bash
chanpy analyze --data-src cache --code 513130
chanpy analyze --data-src cache --code 159530 --kl-type K_WEEK,K_DAY,K_30M
chanpy analyze --data-src cache --code 518880 --json --figure --output-dir output
```
