# 单表持仓与观察股跟踪设计

## 目标

在现有 SQLite 缓存库中维护一张统一的股票跟踪表。数量为零的记录是观察股；数量大于零的记录是持仓股。使用一个命令完成持仓卖点和观察股买点的缠论分析。

## 数据模型

新增 `tracked_stocks` 表：`symbol`（裸码，主键）、`name`、`quantity`、`available_quantity`、`cost_price`（观察股为空）、`group_name`、`note`、`active`、`created_at`、`updated_at`。不重复保存行情、K 线或缠论结构。

## 命令

- `portfolio init`：创建表并写入已确认的五只股票。
- `portfolio set`：新增或修改观察/持仓记录；数量为零时清空成本价。
- `portfolio list`：打印统一列表及状态。
- `portfolio analyze`：持仓在前、观察股在后，使用周、日、30 分钟和 5 分钟已有缠论计算。`--refresh` 时先按 auto 刷新缓存。

## 规则化输出

持仓股聚焦最新卖点、成本价相对位置和风险提示；观察股聚焦最新买点与关注优先级。输出均列出数据时间及信号依据，属于规则化技术分析提示，不自动执行交易。
