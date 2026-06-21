# 命令行参数实现计划

> **供代理执行：** 必须使用 `superpowers:executing-plans` 或 `superpowers:subagent-driven-development` 逐项执行；步骤使用复选框跟踪。

**目标：** 为示例入口增加可测试的中文命令行参数，按级别计算默认起始日期，保存图片到可配置目录。

**架构：** 新建纯 Python CLI 模块，用 `argparse` 将字符串转换为枚举、日期和参数数据类。`main.py` 只负责装配并运行；`CChan` 向后兼容地支持 `KL_TYPE` 到起始日期的映射，并在构造数据源时按级别取值。

**技术栈：** Python 标准库（`argparse`、`datetime`、`pathlib`）、pytest。

---

### 任务 1：CLI 参数解析模块

**文件：**
- 新建：`CLI.py`
- 新建：`tests/test_cli.py`

- [ ] **步骤 1：编写失败测试**

```python
from datetime import date

from CLI import parse_args
from Common.CEnum import DATA_SRC, KL_TYPE


def test_默认参数包含四个级别与分级别起始日期():
    options = parse_args([], today=date(2026, 6, 21))

    assert options.data_src == DATA_SRC.BAO_STOCK
    assert options.lv_list == [KL_TYPE.K_WEEK, KL_TYPE.K_DAY, KL_TYPE.K_30M, KL_TYPE.K_5M]
    assert options.begin_time[KL_TYPE.K_WEEK] == "2019-12-26"
    assert options.begin_time[KL_TYPE.K_5M] == "2026-06-01"
```

- [ ] **步骤 2：运行失败测试**

运行：`pytest tests/test_cli.py::test_默认参数包含四个级别与分级别起始日期 -q`

预期：因无法导入 `CLI` 而失败。

- [ ] **步骤 3：实现最小解析器**

在 `CLI.py` 中定义不可变 `CliOptions` 数据类、`parse_args(argv, today=None)`、`DATA_SRC` 的中文帮助说明、`K_WEEK,K_DAY,K_30M,K_5M` 默认列表，以及 `{K_WEEK: 2400, K_DAY: 1200, K_30M: 180, K_5M: 20}` 的日期回溯映射。所有 argparse 文本使用中文。

- [ ] **步骤 4：运行测试确认通过**

运行：`pytest tests/test_cli.py::test_默认参数包含四个级别与分级别起始日期 -q`

预期：通过。

### 任务 2：显式参数与错误输入

**文件：**
- 修改：`tests/test_cli.py`
- 修改：`CLI.py`

- [ ] **步骤 1：编写失败测试**

```python
def test_显式起始日期覆盖所有选中级别():
    options = parse_args(
        ["--code", "sh.600000", "--start", "2020-01-02", "--end", "2024-01-01", "--kl-type", "K_DAY,K_30M"],
        today=date(2026, 6, 21),
    )

    assert options.code == "sh.600000"
    assert options.end_time == "2024-01-01"
    assert options.begin_time == {KL_TYPE.K_DAY: "2020-01-02", KL_TYPE.K_30M: "2020-01-02"}
```

- [ ] **步骤 2：运行失败测试**

运行：`pytest tests/test_cli.py::test_显式起始日期覆盖所有选中级别 -q`

预期：失败，因为显式参数尚未完整解析。

- [ ] **步骤 3：实现校验**

支持 `--data-src`、`--code`、`--start`、`--end`、`--kl-type` 和 `--output-dir`；使用 `date.fromisoformat` 校验日期，将无效级别和空级别列表转换为中文 argparse 错误。

- [ ] **步骤 4：运行 CLI 测试**

运行：`pytest tests/test_cli.py -q`

预期：全部通过。

### 任务 3：按级别向数据源传递日期

**文件：**
- 修改：`Chan.py:20-40,96-98`
- 新建：`tests/test_chan_begin_time.py`

- [ ] **步骤 1：编写失败测试**

```python
def test_按级别日期映射传给数据源():
    chan = CChan.__new__(CChan)
    chan.code = "sz.000001"
    chan.begin_time = {KL_TYPE.K_WEEK: "2020-01-01", KL_TYPE.K_DAY: "2024-01-01"}
    chan.end_time = None
    chan.autype = AUTYPE.QFQ

    weekly = chan.get_load_stock_iter(RecordingApi, KL_TYPE.K_WEEK)
    daily = chan.get_load_stock_iter(RecordingApi, KL_TYPE.K_DAY)

    assert weekly.begin_date == "2020-01-01"
    assert daily.begin_date == "2024-01-01"
```

- [ ] **步骤 2：运行失败测试**

运行：`pytest tests/test_chan_begin_time.py::test_按级别日期映射传给数据源 -q`

预期：失败，因为当前实现把整个映射传入每个数据源。

- [ ] **步骤 3：实现兼容选择逻辑**

为 `CChan` 添加私有方法：当 `begin_time` 是映射时返回 `begin_time.get(lv)`，否则返回原标量；在 `get_load_stock_iter()` 调用数据源时使用该方法。保留原有标量行为和深拷贝行为。

- [ ] **步骤 4：运行相关测试**

运行：`pytest tests/test_chan_begin_time.py tests/test_cli.py -q`

预期：全部通过。

### 任务 4：入口、输出目录与忽略规则

**文件：**
- 修改：`main.py`
- 修改：`.gitignore`
- 修改：`tests/test_cli.py`

- [ ] **步骤 1：编写失败测试**

```python
def test_输出文件路径使用指定目录和代码():
    options = parse_args(["--code", "sh.600000", "--output-dir", "images"])

    assert options.output_path == Path("images") / "sh.600000.png"
```

- [ ] **步骤 2：运行失败测试**

运行：`pytest tests/test_cli.py::test_输出文件路径使用指定目录和代码 -q`

预期：失败，因为尚未提供 `output_path`。

- [ ] **步骤 3：实现入口连接**

在 `main.py` 中调用 `parse_args()`，以 `options` 建立 `CChan`；静态绘图时执行 `options.output_dir.mkdir(parents=True, exist_ok=True)` 并保存至 `options.output_path`。在 `.gitignore` 添加 `/output/`。

- [ ] **步骤 4：运行完整验证**

运行：`pytest -q`

预期：所有测试通过；再运行 `python main.py --help`，确认帮助文本为中文且不请求网络数据。

- [ ] **步骤 5：提交实现**

运行：`git add CLI.py Chan.py main.py .gitignore tests/test_cli.py tests/test_chan_begin_time.py docs/superpowers/plans/2026-06-21-cli-arguments.md && git commit -m "feat: add command-line analysis options"`

预期：仅提交本功能文件，不包含用户已暂存的 `test.png`。
