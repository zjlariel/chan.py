# ETF 基金跟踪表设计

## 目标

新增一张独立的 SQLite 表跟踪场内 ETF 基金，避免把 ETF 与当前 A 股股票池混在同一张 `tracked_stocks` 表中。ETF 表只负责保存持仓和观察信息，热门行业 ETF 排序只作为候选报告输出，不自动入库。

## 数据模型

新增 `tracked_etfs` 表：

- `symbol`：6 位场内基金代码，主键，支持 `15`、`51`、`56`、`58` 开头。
- `name`：基金名称。
- `quantity`：持有份额，`0` 表示观察。
- `available_quantity`：可用份额。
- `cost_price`：成本价，观察 ETF 为空。
- `category`：行业或主题分类，例如半导体、机器人、创新药、港股科技。
- `tracking_index`：跟踪指数或参考指数。
- `note`：备注。
- `active`：软删除标记。
- `created_at`、`updated_at`：北京时间时间戳。

状态规则与股票池一致：`quantity > 0` 为持仓，`quantity == 0` 为观察。

## 命令

新增 `etf` 子命令：

- `etf init`：创建 `tracked_etfs` 表。
- `etf set`：新增或更新观察/持仓 ETF。持仓必须提供大于 0 的成本价；观察会清空成本价。
- `etf list`：列出启用 ETF，持仓在前，观察在后。
- `etf delete`：软删除 ETF，不物理删除历史记录。

本轮不把 ETF 接入缠论分析和 `cache update --all`。现有行情接口对 ETF 的代码和数据支持需要单独验证，避免把数据源能力变化和跟踪表管理混在一起。

## 热门行业 ETF 排序

热门行业 ETF 采用综合热度口径：近期强势主题、成交活跃度、市场关注度。排序报告用于人工挑选候选，不自动写入 `tracked_etfs` 表。

## 测试

- `EtfStore` 覆盖建表、持仓/观察转换、成本价校验、软删除。
- CLI 覆盖 `etf init`、`etf set`、`etf list`、`etf delete`。
- 不修改缠论算法相关文件。
