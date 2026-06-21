from pathlib import Path

import pytest

from App.cache_cli import EOD_TYPES, LIVE_TYPES, main, parse_args


class FakeCache:
    calls = []

    def __init__(self, code, k_type, begin_date=None, end_date=None, autype=None, cache_path=None, now=None, provider_classes=None, mode="auto"):
        self.code = code
        self.k_type = k_type
        self.cache_path = cache_path
        self.mode = mode

    def refresh(self):
        self.__class__.calls.append((self.code, self.k_type, self.mode, self.cache_path))


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


@pytest.fixture(autouse=True)
def reset_calls():
    FakeCache.calls = []


def test_update_live_parses_codes_and_refreshes_minute_types(tmp_path):
    cache_path = tmp_path / "cache.sqlite3"
    main(
        ["update", "--mode", "live", "--codes", "600000,000001", "--cache-path", str(cache_path)],
        cache_class=FakeCache,
        store_class=FakeStore,
    )

    expected = [(code, k_type, "live", cache_path) for code in ["600000", "000001"] for k_type in LIVE_TYPES]
    assert FakeCache.calls == expected


def test_update_eod_parses_codes_and_refreshes_eod_types(tmp_path):
    cache_path = tmp_path / "cache.sqlite3"
    main(
        ["update", "--mode", "eod", "--codes", "600000", "--cache-path", str(cache_path)],
        cache_class=FakeCache,
        store_class=FakeStore,
    )

    expected = [("600000", k_type, "eod", cache_path) for k_type in EOD_TYPES]
    assert FakeCache.calls == expected


def test_status_prints_cache_summary(capsys, tmp_path):
    cache_path = tmp_path / "cache.sqlite3"
    main(["status", "--cache-path", str(cache_path)], cache_class=FakeCache, store_class=FakeStore)

    captured = capsys.readouterr()
    assert "sh600000" in captured.out
    assert "K_5M" in captured.out
    assert "10" in captured.out


def test_parse_args_defaults_update_mode_to_auto():
    assert parse_args(["update", "--codes", "600000"]).mode == "auto"


def test_parse_args_requires_update_codes():
    with pytest.raises(SystemExit):
        parse_args(["update", "--mode", "eod"])
