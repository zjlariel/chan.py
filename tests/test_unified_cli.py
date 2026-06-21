from datetime import date, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from Common.CEnum import DATA_SRC, KL_TYPE
from cli import app

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
        KL_TYPE.K_30M: (today - timedelta(days=300)).isoformat(),
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
    assert mock_plot.call_count == 4
    assert [Path(call.args[0]).name for call in mock_plot.return_value.save2img.call_args_list] == [
        "sz.000001_K_WEEK.png",
        "sz.000001_K_DAY.png",
        "sz.000001_K_30M.png",
        "sz.000001_K_5M.png",
    ]


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
