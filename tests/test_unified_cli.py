from datetime import date, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from Common.CEnum import DATA_SRC, KL_TYPE
from cli import DEFAULT_LEVELS, _portfolio_analysis_levels, app

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


def test_cache_update_requires_codes():
    result = runner.invoke(app, ["cache", "update", "--mode", "live"])
    assert result.exit_code != 0
    assert "--codes" in result.output


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


def test_portfolio_analysis_calculates_each_level_independently(tmp_path):
    fake_bar = MagicMock(close=43.07)
    fake_cache = MagicMock()
    fake_cache.get_kl_data.return_value = iter([fake_bar])
    document = {"levels": {level.name: {"buy_sell_points": []} for level in DEFAULT_LEVELS}}
    with patch("cli.CCache", return_value=fake_cache), patch("cli.CChan") as mock_chan, patch("cli.build_document", return_value=document):
        _portfolio_analysis_levels("002536", tmp_path / "cache.sqlite3", refresh=False)

    assert mock_chan.call_count == len(DEFAULT_LEVELS)
    assert [call.kwargs["lv_list"] for call in mock_chan.call_args_list] == [[level] for level in DEFAULT_LEVELS]
