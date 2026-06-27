from contextlib import contextmanager
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from Common.CEnum import DATA_SRC, KL_TYPE
from cli import DEFAULT_LEVELS, PORTFOLIO_LEVELS, _portfolio_analysis_levels, app

runner = CliRunner()


def test_analyze_defaults_fill_missing_cache_with_baostock_and_use_default_levels():
    with patch("cli.CChan") as mock_chan, patch("cli.CCache") as mock_cache, patch("cli.CPlotDriver") as mock_plot:
        mock_chan.return_value = MagicMock()
        mock_cache.return_value.get_kl_data.return_value = iter(())
        mock_plot.return_value = MagicMock()
        mock_plot.return_value.figure.show = MagicMock()
        result = runner.invoke(app, ["analyze"])

    assert result.exit_code == 0, result.output
    today = date.today()
    expected_begin_dates = {
        KL_TYPE.K_WEEK: (today - timedelta(days=2400)).isoformat(),
        KL_TYPE.K_DAY: (today - timedelta(days=1200)).isoformat(),
        KL_TYPE.K_30M: (today - timedelta(days=180)).isoformat(),
        KL_TYPE.K_5M: (today - timedelta(days=20)).isoformat(),
    }
    assert mock_chan.call_count == 4
    for call, level in zip(mock_chan.call_args_list, expected_begin_dates):
        args = call.kwargs
        assert args["code"] == "sz.000001"
        assert args["data_src"] == DATA_SRC.CACHE
        assert args["lv_list"] == [level]
        assert args["begin_time"] == {level: expected_begin_dates[level]}

    assert mock_cache.call_count == 4
    assert all(call.kwargs["mode"] == "eod" for call in mock_cache.call_args_list)
    assert [call.args[1] for call in mock_cache.call_args_list] == [
        KL_TYPE.K_WEEK,
        KL_TYPE.K_DAY,
        KL_TYPE.K_30M,
        KL_TYPE.K_5M,
    ]
    assert not mock_plot.called


def test_analyze_defaults_prints_terminal_summary():
    with patch("cli.CChan") as mock_chan, patch("cli.CCache") as mock_cache, patch("cli.format_summary") as mock_summary:
        mock_chan.return_value = MagicMock()
        mock_cache.return_value.get_kl_data.return_value = iter(())
        mock_summary.return_value = "分析摘要"

        result = runner.invoke(app, ["analyze"])

    assert result.exit_code == 0, result.output
    assert result.output == "分析摘要\n"
    assert mock_summary.call_count == 1


def test_analyze_accepts_sina_and_custom_levels():
    with patch("cli.CChan") as mock_chan, patch("cli.CPlotDriver") as mock_plot:
        mock_chan.return_value = MagicMock()
        mock_plot.return_value = MagicMock()
        mock_plot.return_value.figure.show = MagicMock()
        result = runner.invoke(app, ["analyze", "--data-src", "sina", "--code", "sh.600000", "--kl-type", "K_1M,K_5M"])

    assert result.exit_code == 0, result.output
    args = mock_chan.call_args.kwargs
    assert args["code"] == "sh.600000"
    assert args["data_src"].name == "SINA"
    assert args["lv_list"] == [KL_TYPE.K_1M, KL_TYPE.K_5M]


def test_analyze_json_writes_results_without_generating_figures(tmp_path):
    with patch("cli.CChan") as mock_chan, patch("cli.CCache") as mock_cache, patch("cli.CPlotDriver") as mock_plot, patch("cli.build_document") as mock_document:
        mock_chan.return_value = MagicMock()
        mock_cache.return_value.get_kl_data.return_value = iter(())
        mock_document.return_value = {"code": "sz.000001", "levels": {}}

        result = runner.invoke(
            app,
            ["analyze", "--json", "--output-dir", str(tmp_path)],
        )

    assert result.exit_code == 0, result.output
    assert not mock_plot.called
    assert (tmp_path / "sz.000001_analysis.json").read_text(encoding="utf-8") == '{\n  "code": "sz.000001",\n  "levels": {}\n}'


def test_analyze_figure_option_generates_images():
    with patch("cli.CChan") as mock_chan, patch("cli.CCache") as mock_cache, patch("cli.CPlotDriver") as mock_plot:
        mock_chan.return_value = MagicMock()
        mock_cache.return_value.get_kl_data.return_value = iter(())
        mock_plot.return_value = MagicMock()

        result = runner.invoke(app, ["analyze", "--figure"])

    assert result.exit_code == 0, result.output
    assert mock_plot.call_count == 4


def test_analyze_html_option_generates_one_independent_plotly_html(tmp_path):
    with patch("cli.CChan") as mock_chan, patch("cli.CCache") as mock_cache, patch("cli.CPlotlyDriver") as mock_plotly:
        mock_chan.return_value = MagicMock()
        mock_cache.return_value.get_kl_data.return_value = iter(())
        mock_plotly.return_value = MagicMock()

        result = runner.invoke(app, ["analyze", "--html", "--output-dir", str(tmp_path)])

    assert result.exit_code == 0, result.output
    assert mock_plotly.call_count == 3
    assert [call.args[1] for call in mock_plotly.call_args_list] == [KL_TYPE.K_DAY, KL_TYPE.K_30M, KL_TYPE.K_5M]
    mock_plotly.return_value.save2html.assert_called_once()
    save_args = mock_plotly.return_value.save2html.call_args
    assert save_args.args[0] == str(tmp_path / "sz.000001_analysis.html")
    assert save_args.kwargs["code"] == "sz.000001"
    assert len(save_args.kwargs["drivers"]) == 3


def test_analyze_html_with_non_cache_source_uses_loaded_day_30m_5m_levels(tmp_path):
    with patch("cli.CChan") as mock_chan, patch("cli.CPlotlyDriver") as mock_plotly:
        mock_chan.return_value = MagicMock()
        mock_plotly.return_value = MagicMock()

        result = runner.invoke(app, ["analyze", "--data-src", "sina", "--html", "--output-dir", str(tmp_path)])

    assert result.exit_code == 0, result.output
    assert mock_chan.call_args.kwargs["lv_list"] == DEFAULT_LEVELS
    assert [call.args[1] for call in mock_plotly.call_args_list] == [KL_TYPE.K_DAY, KL_TYPE.K_30M, KL_TYPE.K_5M]


def test_analyze_cache_refreshes_each_level_before_loading_cached_data():
    calls = []

    class FakeCache:
        def __init__(self, code, k_type, begin_date=None, end_date=None, autype=None, **kwargs):
            self.code = code
            self.k_type = k_type

        def refresh(self):
            calls.append(("refresh", self.k_type))

        def get_kl_data(self):
            calls.append(("load", self.k_type))
            return iter(())

    with patch("cli.CCache", FakeCache), patch("cli.CChan") as mock_chan:
        mock_chan.return_value = MagicMock()

        result = runner.invoke(app, ["analyze", "--kl-type", "K_DAY,K_30M"])

    assert result.exit_code == 0, result.output
    assert calls == [
        ("refresh", KL_TYPE.K_DAY),
        ("load", KL_TYPE.K_DAY),
        ("refresh", KL_TYPE.K_30M),
        ("load", KL_TYPE.K_30M),
    ]


def test_analyze_rejects_unknown_data_source():
    result = runner.invoke(app, ["analyze", "--data-src", "unknown"])
    assert result.exit_code != 0
    assert "未知数据源" in result.output


def test_analyze_rejects_invalid_date():
    result = runner.invoke(app, ["analyze", "--start", "not-a-date"])
    assert result.exit_code != 0
    assert "YYYY-MM-DD" in result.output


def test_cache_update_live_refreshes_minute_types(tmp_path):
    calls = []

    class FakeCache:
        def __init__(self, code, k_type, begin_date=None, end_date=None, autype=None, cache_path=None, now=None, provider_classes=None, mode="auto"):
            self.code = code
            self.k_type = k_type
            self.mode = mode
            self.cache_path = cache_path

        def refresh(self):
            calls.append((self.code, self.k_type.name, self.mode, self.cache_path))

    cache_file = tmp_path / "cache.sqlite3"
    with patch("cli.CCache", FakeCache):
        result = runner.invoke(app, ["cache", "update", "--mode", "live", "--codes", "600000,000001", "--cache-path", str(cache_file)])

    assert result.exit_code == 0, result.output
    assert len(calls) == 10  # 2 codes * 5 minute types
    assert all(mode == "live" for _, _, mode, _ in calls)


def test_cache_update_eod_refreshes_eod_types(tmp_path):
    calls = []

    class FakeCache:
        def __init__(self, code, k_type, begin_date=None, end_date=None, autype=None, cache_path=None, now=None, provider_classes=None, mode="auto"):
            self.code = code
            self.k_type = k_type
            self.mode = mode
            self.cache_path = cache_path

        def refresh(self):
            calls.append((self.code, self.k_type.name, self.mode, self.cache_path))

    cache_file = tmp_path / "cache.sqlite3"
    with patch("cli.CCache", FakeCache):
        result = runner.invoke(app, ["cache", "update", "--mode", "eod", "--codes", "600000", "--cache-path", str(cache_file)])

    assert result.exit_code == 0, result.output
    assert len(calls) == 6  # 1 code * 6 eod types
    assert all(mode == "eod" for _, _, mode, _ in calls)
    assert all(k_type != "K_1M" for _, k_type, _, _ in calls)


def test_cache_update_defaults_to_auto_mode(tmp_path):
    calls = []

    class FakeCache:
        def __init__(self, code, k_type, begin_date=None, end_date=None, autype=None, cache_path=None, now=None, provider_classes=None, mode="auto"):
            self.code = code
            self.k_type = k_type
            self.mode = mode
            self.cache_path = cache_path

        def refresh(self):
            calls.append((self.code, self.k_type.name, self.mode))

    with patch("cli.CCache", FakeCache):
        result = runner.invoke(app, ["cache", "update", "--codes", "600000", "--cache-path", str(tmp_path / "cache.sqlite3")])

    assert result.exit_code == 0, result.output
    assert [item[1] for item in calls] == ["K_WEEK", "K_DAY", "K_60M", "K_30M", "K_15M", "K_5M", "K_1M"]
    assert all(item[2] == "auto" for item in calls)


def test_cache_update_all_updates_active_tracked_stocks(tmp_path):
    calls = []

    class FakeCache:
        def __init__(self, code, k_type, **kwargs):
            self.code = code
            self.k_type = k_type

        def refresh(self, full=False):
            calls.append((self.code, self.k_type.name))
            return {}

    class FakePortfolioStore:
        def __init__(self, path):
            self.path = path

        def list_positions(self):
            return [{"symbol": "002536"}, {"symbol": "600549"}]

    with patch("cli.CCache", FakeCache), patch("cli.PortfolioStore", FakePortfolioStore):
        result = runner.invoke(app, ["cache", "update", "--all", "--mode", "eod", "--cache-path", str(tmp_path / "cache.sqlite3")])

    assert result.exit_code == 0, result.output
    assert calls == [(code, k_type) for code in ["002536", "600549"] for k_type in ["K_WEEK", "K_DAY", "K_60M", "K_30M", "K_15M", "K_5M"]]


def test_cache_update_wraps_multiple_stocks_in_one_baostock_session(tmp_path):
    sessions = []

    @contextmanager
    def fake_keep_alive():
        sessions.append("enter")
        yield
        sessions.append("exit")

    class FakeCache:
        def __init__(self, code, k_type, **kwargs):
            pass

        def refresh(self, full=False):
            return {}

    with patch("cli.CCache", FakeCache), patch("cli.CBaoStock.keep_alive", fake_keep_alive):
        result = runner.invoke(app, ["cache", "update", "--codes", "002536,600549", "--mode", "eod", "--cache-path", str(tmp_path / "cache.sqlite3")])

    assert result.exit_code == 0, result.output
    assert sessions == ["enter", "exit"]


def test_cache_update_prints_written_bar_counts_by_source(tmp_path):
    class FakeCache:
        def __init__(self, code, k_type, **kwargs):
            self.symbol = f"sz{code}"
            self.k_type = k_type

        def refresh(self, full=False):
            return {"sina": {"inserted": 1, "updated": 3}}

    with patch("cli.CCache", FakeCache):
        result = runner.invoke(
            app,
            ["cache", "update", "--mode", "live", "--codes", "002536", "--cache-path", str(tmp_path / "cache.sqlite3")],
        )

    assert result.exit_code == 0, result.output
    assert result.output.count("新增 1 根，覆盖 3 根（sina：新增 1，覆盖 3）") == 5


def test_cache_update_full_requests_full_refresh(tmp_path):
    full_values = []

    class FakeCache:
        def __init__(self, *args, **kwargs):
            pass

        def refresh(self, full=False):
            full_values.append(full)

    with patch("cli.CCache", FakeCache):
        result = runner.invoke(
            app,
            ["cache", "update", "--codes", "600000", "--mode", "eod", "--full", "--cache-path", str(tmp_path / "cache.sqlite3")],
        )

    assert result.exit_code == 0, result.output
    assert full_values == [True] * 6


def test_cache_update_requires_codes_or_all():
    result = runner.invoke(app, ["cache", "update", "--mode", "live"])
    assert result.exit_code != 0
    assert "--codes" in result.output
    assert "--all" in result.output


def test_cache_status_prints_summary(tmp_path):
    cache_file = tmp_path / "cache.sqlite3"

    class FakeStore:
        def __init__(self, path):
            self.path = Path(path)

        def status(self):
            return [
                {
                    "symbol": "sh600000",
                    "k_type": "K_5M",
                    "first_timestamp": "2026-06-18 09:30",
                    "last_timestamp": "2026-06-18 15:00",
                    "bar_count": 10,
                    "updated_at": "2026-06-18 12:00:00",
                }
            ]

    with patch("cli.CacheStore", FakeStore):
        result = runner.invoke(app, ["cache", "status", "--cache-path", str(cache_file)])

    assert result.exit_code == 0, result.output
    assert "sh600000" in result.output
    assert "K_5M" in result.output


def test_cache_status_shows_empty_message(tmp_path):
    cache_file = tmp_path / "cache.sqlite3"

    class FakeStore:
        def __init__(self, path):
            self.path = Path(path)

        def status(self):
            return []

    with patch("cli.CacheStore", FakeStore):
        result = runner.invoke(app, ["cache", "status", "--cache-path", str(cache_file)])

    assert result.exit_code == 0, result.output
    assert "缓存为空" in result.output


def test_portfolio_init_and_set_manage_one_tracked_stock_table(tmp_path):
    cache_file = tmp_path / "cache.sqlite3"

    initialized = runner.invoke(app, ["portfolio", "init", "--cache-path", str(cache_file)])
    updated = runner.invoke(
        app,
        ["portfolio", "set", "--code", "000001", "--name", "平安银行", "--quantity", "0", "--cache-path", str(cache_file)],
    )
    listed = runner.invoke(app, ["portfolio", "list", "--cache-path", str(cache_file)])

    assert initialized.exit_code == 0, initialized.output
    assert updated.exit_code == 0, updated.output
    assert "澜起科技" in listed.output
    assert "平安银行" in listed.output
    assert "观察" in listed.output


def test_portfolio_delete_hides_tracked_stock_from_list(tmp_path):
    cache_file = tmp_path / "cache.sqlite3"

    created = runner.invoke(
        app,
        ["portfolio", "set", "--code", "000001", "--name", "平安银行", "--quantity", "0", "--cache-path", str(cache_file)],
    )
    deleted = runner.invoke(app, ["portfolio", "delete", "--code", "000001", "--cache-path", str(cache_file)])
    listed = runner.invoke(app, ["portfolio", "list", "--cache-path", str(cache_file)])

    assert created.exit_code == 0, created.output
    assert deleted.exit_code == 0, deleted.output
    assert "已删除 000001" in deleted.output
    assert "平安银行" not in listed.output


def test_portfolio_delete_reports_missing_stock(tmp_path):
    cache_file = tmp_path / "cache.sqlite3"

    result = runner.invoke(app, ["portfolio", "delete", "--code", "000001", "--cache-path", str(cache_file)])

    assert result.exit_code != 0
    assert "未找到跟踪股票：000001" in result.output


def test_portfolio_analyze_outputs_holding_and_watch_sections(tmp_path):
    positions = [
        {"symbol": "002536", "name": "飞龙股份", "quantity": 400, "cost_price": 41.343, "status": "holding"},
        {"symbol": "000001", "name": "平安银行", "quantity": 0, "cost_price": None, "status": "watching"},
    ]
    levels = {"K_WEEK": {"buy_sell_points": []}, "K_DAY": {"buy_sell_points": []}, "K_30M": {"buy_sell_points": []}, "K_5M": {"buy_sell_points": []}}
    with patch("cli.PortfolioStore") as mock_store, patch("cli._portfolio_analysis_levels", return_value=(levels, 43.07)):
        mock_store.return_value.list_positions.return_value = positions

        result = runner.invoke(app, ["portfolio", "analyze", "--cache-path", str(tmp_path / "cache.sqlite3")])

    assert result.exit_code == 0, result.output
    assert "持仓股" in result.output
    assert "观察股" in result.output
    assert "飞龙股份" in result.output
    assert "平安银行" in result.output


def test_portfolio_analyze_prints_detailed_report_lines(tmp_path):
    positions = [
        {"symbol": "002536", "name": "飞龙股份", "quantity": 400, "cost_price": 41.343, "status": "holding"},
    ]
    levels = {
        "K_WEEK": {
            "data_range": {"start": "2026/01/01", "end": "2026/06/19"},
            "segments": [{"direction": "UP", "begin_time": "2026/04/02", "end_time": "2026/06/19"}],
        },
        "K_DAY": {
            "data_range": {"start": "2026/04/01", "end": "2026/06/23"},
            "buy_sell_points": [{"time": "2026/06/23", "is_buy": True, "type": "2"}],
            "indicators": {
                "latest": {
                    "macd": {"time": "2026/06/23", "dif": 0.02, "dea": 0.08, "macd": -0.12},
                    "kdj": {"time": "2026/06/23", "k": 41.0, "d": 44.0, "j": 35.0},
                },
                "crosses": {"macd": [], "kdj": []},
            },
        },
        "K_30M": {"data_range": {"start": "2026/06/01 09:30", "end": "2026/06/23 14:30"}},
    }
    with patch("cli.PortfolioStore") as mock_store, patch("cli._portfolio_analysis_levels", return_value=(levels, 43.07)):
        mock_store.return_value.list_positions.return_value = positions

        result = runner.invoke(app, ["portfolio", "analyze", "--cache-path", str(tmp_path / "cache.sqlite3")])

    assert result.exit_code == 0, result.output
    assert "详细报告：" in result.output
    assert "最近买卖点：" in result.output
    assert "结构：" in result.output


def test_portfolio_analyze_wraps_multiple_stocks_in_one_baostock_session(tmp_path):
    sessions = []
    positions = [
        {"symbol": "002536", "name": "飞龙股份", "quantity": 400, "cost_price": 41.343, "status": "holding"},
        {"symbol": "600549", "name": "厦门钨业", "quantity": 200, "cost_price": 65.086, "status": "holding"},
    ]
    levels = {"K_WEEK": {"buy_sell_points": []}, "K_DAY": {"buy_sell_points": []}, "K_30M": {"buy_sell_points": []}}

    @contextmanager
    def fake_keep_alive():
        sessions.append("enter")
        yield
        sessions.append("exit")

    with (
        patch("cli.PortfolioStore") as mock_store,
        patch("cli._portfolio_analysis_levels", return_value=(levels, 43.07)),
        patch("cli.CBaoStock.keep_alive", fake_keep_alive),
    ):
        mock_store.return_value.list_positions.return_value = positions

        result = runner.invoke(app, ["portfolio", "analyze", "--cache-path", str(tmp_path / "cache.sqlite3")])

    assert result.exit_code == 0, result.output
    assert sessions == ["enter", "exit"]


def test_portfolio_analyze_code_limits_refresh_and_analysis_to_one_tracked_stock(tmp_path):
    positions = [
        {"symbol": "002050", "name": "三花智控", "quantity": 0, "cost_price": None, "status": "watching"},
        {"symbol": "002536", "name": "飞龙股份", "quantity": 0, "cost_price": None, "status": "watching"},
    ]
    levels = {"K_WEEK": {"buy_sell_points": []}, "K_DAY": {"buy_sell_points": []}, "K_30M": {"buy_sell_points": []}}
    with patch("cli.PortfolioStore") as mock_store, patch("cli._portfolio_analysis_levels", return_value=(levels, 43.07)) as mock_levels:
        mock_store.return_value.list_positions.return_value = positions

        result = runner.invoke(app, ["portfolio", "analyze", "--code", "sz.002050", "--refresh", "--cache-path", str(tmp_path / "cache.sqlite3")])

    assert result.exit_code == 0, result.output
    assert "三花智控" in result.output
    assert "飞龙股份" not in result.output
    assert mock_levels.call_args.args[0] == "002050"
    assert mock_levels.call_args.args[2] is True


def test_portfolio_analyze_code_allows_untracked_stock_without_persisting_it(tmp_path):
    levels = {"K_WEEK": {"buy_sell_points": []}, "K_DAY": {"buy_sell_points": []}, "K_30M": {"buy_sell_points": []}}
    with patch("cli.PortfolioStore") as mock_store, patch("cli._portfolio_analysis_levels", return_value=(levels, 10.0)) as mock_levels:
        mock_store.return_value.list_positions.return_value = []

        result = runner.invoke(app, ["portfolio", "analyze", "--code", "002240", "--refresh", "--cache-path", str(tmp_path / "cache.sqlite3")])

    assert result.exit_code == 0, result.output
    assert "临时观察股" in result.output
    assert "002240" in result.output
    assert mock_levels.call_args.args[0] == "002240"
    assert not mock_store.return_value.set_position.called


def test_portfolio_analysis_calculates_each_level_independently(tmp_path):
    fake_bar = MagicMock(close=43.07)
    fake_cache = MagicMock()
    fake_cache.get_kl_data.return_value = iter([fake_bar])
    document = {"levels": {level.name: {"buy_sell_points": []} for level in PORTFOLIO_LEVELS}}
    with patch("cli.CCache", return_value=fake_cache), patch("cli.CChan") as mock_chan, patch("cli.build_document", return_value=document):
        _portfolio_analysis_levels("002536", tmp_path / "cache.sqlite3", refresh=False)

    assert mock_chan.call_count == len(PORTFOLIO_LEVELS)
    assert [call.kwargs["lv_list"] for call in mock_chan.call_args_list] == [[level] for level in PORTFOLIO_LEVELS]
    assert KL_TYPE.K_5M not in PORTFOLIO_LEVELS


def test_portfolio_analysis_skips_weekly_kdj_calculation(tmp_path):
    fake_bar = MagicMock(close=43.07)
    fake_cache = MagicMock()
    fake_cache.get_kl_data.return_value = iter([fake_bar])
    document = {"levels": {level.name: {"buy_sell_points": []} for level in PORTFOLIO_LEVELS}}
    with patch("cli.CCache", return_value=fake_cache), patch("cli.CChan") as mock_chan, patch("cli.build_document", return_value=document):
        _portfolio_analysis_levels("002536", tmp_path / "cache.sqlite3", refresh=False)

    config_by_level = {
        call.kwargs["lv_list"][0]: call.kwargs["config"]
        for call in mock_chan.call_args_list
    }
    assert config_by_level[KL_TYPE.K_WEEK].cal_kdj is False
    assert config_by_level[KL_TYPE.K_DAY].cal_kdj is True
    assert config_by_level[KL_TYPE.K_30M].cal_kdj is True
