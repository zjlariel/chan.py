# 新浪 A 股实时分钟数据设计

## 目标

通过新浪财经的分钟 K 线接口，为现有数据源框架提供沪深 A 股的实时 1、5、15、30、60 分钟数据。

## 接口与集成

- 新增 `DATA_SRC.SINA` 和 `DataAPI/SinaAPI.py` 中的 `CSina`。
- `Chan.CChan.GetStockAPI` 将 `DATA_SRC.SINA` 映射到 `CSina`，调用方沿用 `data_src=DATA_SRC.SINA`。
- 适配器继承 `CCommonStockApi`，输出 `CKLine_Unit`，字段为时间、开高低收与成交量。

## 代码与周期

- 接受 `sz.000001`、`sz000001` 和裸六码股票代码。
- 裸码以 6 开头映射到 `sh`，以 0 或 3 开头映射到 `sz`；其他代码拒绝。
- 支持 `K_1M`、`K_5M`、`K_15M`、`K_30M` 和 `K_60M`，并映射到新浪的相应 `scale` 参数。
- 只支持沪深 A 股，不支持港股、美股或非分钟周期。

## 数据处理与失败模式

- 新浪分钟数据以未复权价格输出；`autype` 不对数据作变换。
- 对 `begin_date` 与 `end_date` 做客户端时间过滤。
- 网络异常、HTTP 失败、无效 JSON、缺失 K 线字段和空响应都会产生包含代码与周期上下文的异常。

## 测试

单元测试会 mock HTTP 响应，覆盖代码规范化、周期映射、解析和日期过滤，以及 `DATA_SRC.SINA` 的分发注册；不依赖交易时段或公网可用性。
