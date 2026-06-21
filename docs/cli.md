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
chanpy analyze --code sh.600000 --start 2024-01-01 --end 2025-12-31
chanpy analyze --data-src baostock --code sz.000001 --kl-type K_DAY --output-dir images
```

`--data-src cache` 时会按级别分别输出图片，例如：

- `output/sz.002536_K_WEEK.png`
- `output/sz.002536_K_DAY.png`
- `output/sz.002536_K_30M.png`
- `output/sz.002536_K_5M.png`

---

## cache update：刷新缓存数据

```bash
chanpy cache update [OPTIONS]
```

### 参数

| 参数 | 说明 | 默认值 |
| --- | --- | --- |
| `--mode` | 刷新模式：`live` 或 `eod` | 必填 |
| `--codes` | 逗号分隔的股票代码 | 必填 |
| `--cache-path` | SQLite 缓存文件路径 | `.chanpy/cache.sqlite3` |

- `live` 模式：从新浪刷新分钟级别数据（`K_1M`、`K_5M`、`K_15M`、`K_30M`、`K_60M`）。
- `eod` 模式：从 Baostock 刷新 `K_WEEK`、`K_DAY`、`K_60M`、`K_30M`、`K_15M`、`K_5M`，跳过 `K_1M`。

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
