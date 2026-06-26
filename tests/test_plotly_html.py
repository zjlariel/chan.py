from pathlib import Path
from unittest.mock import MagicMock, patch

from Common.CEnum import KL_TYPE
from Plot.PlotlyDriver import CPlotlyDriver


def test_plotly_driver_uses_sparse_auto_x_ticks():
    chan = MagicMock()
    chan.code = "sz.000001"
    chan.__getitem__.return_value = MagicMock()

    meta = MagicMock()
    meta.datetick = [f"2026/06/{day:02}" for day in range(1, 31)]
    meta.klu_iter.return_value = iter(())
    meta.bi_list = []
    meta.seg_list = []
    meta.zs_lst = []
    meta.bs_point_lst = []

    with patch("Plot.PlotlyDriver.CChanPlotMeta", return_value=meta):
        driver = CPlotlyDriver(chan, KL_TYPE.K_DAY)

    assert driver.figure.layout.xaxis.tickmode == "auto"
    assert driver.figure.layout.xaxis.nticks == 8


def test_plotly_driver_uses_a_share_candlestick_colors():
    chan = MagicMock()
    chan.code = "sz.000001"
    chan.__getitem__.return_value = MagicMock()

    up_klu = MagicMock()
    up_klu.time.to_str.return_value = "2026/06/25"
    up_klu.open = 10.0
    up_klu.high = 11.0
    up_klu.low = 9.8
    up_klu.close = 10.8

    down_klu = MagicMock()
    down_klu.time.to_str.return_value = "2026/06/26"
    down_klu.open = 10.8
    down_klu.high = 11.0
    down_klu.low = 10.0
    down_klu.close = 10.2

    meta = MagicMock()
    meta.datetick = ["2026/06/25", "2026/06/26"]
    meta.klu_iter.return_value = iter([up_klu, down_klu])
    meta.bi_list = []
    meta.seg_list = []
    meta.zs_lst = []
    meta.bs_point_lst = []

    with patch("Plot.PlotlyDriver.CChanPlotMeta", return_value=meta):
        driver = CPlotlyDriver(chan, KL_TYPE.K_DAY)

    kline = driver.figure.data[0]
    assert kline.increasing.line.color == "red"
    assert kline.increasing.fillcolor == "red"
    assert kline.decreasing.line.color == "green"
    assert kline.decreasing.fillcolor == "green"


def test_plotly_driver_writes_single_html_with_independent_level_divs(tmp_path):
    day_driver = CPlotlyDriver.__new__(CPlotlyDriver)
    day_driver.level = KL_TYPE.K_DAY
    day_driver.figure = MagicMock()
    day_driver.figure.to_html.return_value = "<div>day</div>"

    m30_driver = CPlotlyDriver.__new__(CPlotlyDriver)
    m30_driver.level = KL_TYPE.K_30M
    m30_driver.figure = MagicMock()
    m30_driver.figure.to_html.return_value = "<div>30m</div>"

    m5_driver = CPlotlyDriver.__new__(CPlotlyDriver)
    m5_driver.level = KL_TYPE.K_5M
    m5_driver.figure = MagicMock()
    m5_driver.figure.to_html.return_value = "<div>5m</div>"

    output = tmp_path / "analysis.html"

    CPlotlyDriver.save_multi_level_html([day_driver, m30_driver, m5_driver], output, "sz.000001")

    html = output.read_text(encoding="utf-8")
    assert "sz.000001 缠论分析" in html
    assert html.count('class="chart-section"') == 3
    assert "日线" in html
    assert "30分钟线" in html
    assert "5分钟线" in html
    assert "<div>day</div>" in html
    assert "<div>30m</div>" in html
    assert "<div>5m</div>" in html

    day_driver.figure.to_html.assert_called_once_with(full_html=False, include_plotlyjs="cdn", config={"responsive": True})
    m30_driver.figure.to_html.assert_called_once_with(full_html=False, include_plotlyjs=False, config={"responsive": True})
    m5_driver.figure.to_html.assert_called_once_with(full_html=False, include_plotlyjs=False, config={"responsive": True})


def test_plotly_driver_adds_candlestick_and_toggleable_chan_traces():
    chan = MagicMock()
    chan.code = "sz.000001"
    chan.__getitem__.return_value = MagicMock()

    klu = MagicMock()
    klu.time.to_str.return_value = "2026/06/26"
    klu.open = 10.0
    klu.high = 11.0
    klu.low = 9.0
    klu.close = 10.5

    meta = MagicMock()
    meta.datetick = ["2026/06/26"]
    meta.klu_iter.return_value = iter([klu])
    meta.bi_list = [MagicMock(begin_x=0, end_x=0, begin_y=10.0, end_y=10.5, is_sure=True)]
    meta.seg_list = [MagicMock(begin_x=0, end_x=0, begin_y=9.5, end_y=10.8, is_sure=False)]
    meta.zs_lst = [MagicMock(begin=0, end=0, low=9.5, high=10.5, is_sure=True, sub_zs_lst=[], is_onebi_zs=False)]
    meta.bs_point_lst = [MagicMock(x=0, y=9.0, is_buy=True, desc=lambda: "b1")]

    with patch("Plot.PlotlyDriver.CChanPlotMeta", return_value=meta):
        driver = CPlotlyDriver(chan, KL_TYPE.K_DAY)

    assert [trace.name for trace in driver.figure.data] == ["K线", "笔", "线段", "中枢", "买卖点"]
