from datetime import datetime
from pathlib import Path

from Chan import CChan
from Common.CEnum import AUTYPE, DATA_FIELD, DATA_SRC, KL_TYPE
from Common.CTime import CTime
from DataAPI.CacheAPI import CCache
from DataAPI.CacheStore import CacheStore
from KLine.KLine_Unit import CKLine_Unit


def make_bar(close=9.1, time=None):
    if time is None:
        time = CTime(2026, 6, 18, 10, 0, auto=False)
    return CKLine_Unit(
        {
            DATA_FIELD.FIELD_TIME: time,
            DATA_FIELD.FIELD_OPEN: close - 0.1,
            DATA_FIELD.FIELD_HIGH: close + 0.1,
            DATA_FIELD.FIELD_LOW: close - 0.2,
            DATA_FIELD.FIELD_CLOSE: close,
            DATA_FIELD.FIELD_VOLUME: 100,
            DATA_FIELD.FIELD_TURNOVER: close * 100,
        }
    )


class FakeSina:
    calls = []

    def __init__(self, code, k_type, begin_date, end_date, autype):
        self.__class__.calls.append((code, k_type, begin_date, end_date, autype))

    def get_kl_data(self):
        yield make_bar()


class FakeBao(FakeSina):
    calls = []
    name = "\u6d66\u53d1\u94f6\u884c"


class FakeEastMoney(FakeSina):
    calls = []
    name = "ETF"


class FakeYahoo(FakeSina):
    calls = []
    name = "ETF Yahoo"


class FailingYahoo(FakeSina):
    calls = []

    def get_kl_data(self):
        raise RuntimeError("Yahoo 暂不可用")


class PartialBao(FakeSina):
    calls = []

    def get_kl_data(self):
        yield make_bar(1.0, CTime(2026, 1, 5, 0, 0, auto=False))
        yield make_bar(1.1, CTime(2026, 7, 1, 0, 0, auto=False))


class RangeBao(FakeSina):
    calls = []

    def __init__(self, code, k_type, begin_date, end_date, autype):
        super().__init__(code, k_type, begin_date, end_date, autype)
        self.begin_date = begin_date
        self.end_date = end_date

    def get_kl_data(self):
        begin = datetime.fromisoformat(self.begin_date[:10])
        end = datetime.fromisoformat(self.end_date[:10])
        yield make_bar(1.0, CTime(begin.year, begin.month, begin.day, 0, 0, auto=False))
        yield make_bar(1.1, CTime(end.year, end.month, end.day, 0, 0, auto=False))


def build_api(tmp_path: Path, k_type, now):
    FakeSina.calls = []
    FakeBao.calls = []
    return CCache(
        "600000",
        k_type,
        "2026-06-18",
        "2026-06-18",
        AUTYPE.QFQ,
        cache_path=tmp_path / "cache.sqlite3",
        now=now,
        provider_classes={"sina": FakeSina, "baostock": FakeBao},
    )


def test_returns_covered_cache_without_requesting_provider(tmp_path):
    api = build_api(tmp_path, KL_TYPE.K_5M, datetime(2026, 6, 18, 10, 0))
    api.store.upsert_bars(api.symbol, KL_TYPE.K_5M, [make_bar(9.5)], "baostock")
    api.store.mark_covered(api.symbol, KL_TYPE.K_5M, "2026-06-18", "2026-06-18", "baostock")

    bars = list(api.get_kl_data())

    assert [bar.close for bar in bars] == [9.5]
    assert FakeSina.calls == []
    assert FakeBao.calls == []


def test_live_cache_miss_fetches_sina_and_persists_result(tmp_path):
    api = build_api(tmp_path, KL_TYPE.K_5M, datetime(2026, 6, 18, 10, 0))

    bars = list(api.get_kl_data())

    assert [bar.close for bar in bars] == [9.1]
    assert FakeSina.calls[0][:4] == ("sh600000", KL_TYPE.K_5M, "2026-06-18", "2026-06-18")
    assert api.store.covers(api.symbol, KL_TYPE.K_5M, "2026-06-18", "2026-06-18")


def test_end_of_day_cache_miss_fetches_baostock(tmp_path):
    api = build_api(tmp_path, KL_TYPE.K_5M, datetime(2026, 6, 18, 19, 0))

    list(api.get_kl_data())

    assert FakeBao.calls[0][:4] == ("sh.600000", KL_TYPE.K_5M, "2026-06-18", "2026-06-18")
    assert FakeSina.calls == []


def test_cache_accepts_bare_etf_symbols_and_fetches_daily_from_yahoo(tmp_path):
    FakeSina.calls = []
    FakeBao.calls = []
    FakeEastMoney.calls = []
    FakeYahoo.calls = []
    api = CCache(
        "513130",
        KL_TYPE.K_DAY,
        "2026-06-18",
        "2026-06-18",
        AUTYPE.NONE,
        cache_path=tmp_path / "cache.sqlite3",
        now=datetime(2026, 6, 18, 19, 0),
        provider_classes={"sina": FakeSina, "baostock": FakeBao, "eastmoney": FakeEastMoney, "yahoo": FakeYahoo},
        mode="eod",
    )

    list(api.get_kl_data())

    assert api.symbol == "sh513130"
    assert FakeYahoo.calls[0][:4] == ("513130", KL_TYPE.K_DAY, "2026-06-18", "2026-06-18")
    assert FakeEastMoney.calls == []
    assert FakeBao.calls == []


def test_refresh_persists_provider_stock_name(tmp_path):
    api = CCache(
        "600000",
        KL_TYPE.K_DAY,
        "2026-06-18",
        "2026-06-18",
        AUTYPE.QFQ,
        cache_path=tmp_path / "cache.sqlite3",
        now=datetime(2026, 6, 18, 19, 0),
        provider_classes={"sina": FakeSina, "baostock": FakeBao},
        mode="eod",
    )

    api.refresh()

    assert api.store.stock_name("sh600000") == "\u6d66\u53d1\u94f6\u884c"


def test_end_of_day_cache_uses_qfq_when_autype_is_omitted(tmp_path):
    FakeSina.calls = []
    FakeBao.calls = []
    api = CCache(
        "002460",
        KL_TYPE.K_DAY,
        "2026-06-18",
        "2026-06-18",
        cache_path=tmp_path / "cache.sqlite3",
        now=datetime(2026, 6, 18, 19, 0),
        provider_classes={"sina": FakeSina, "baostock": FakeBao},
        mode="eod",
    )

    list(api.get_kl_data())

    assert FakeBao.calls[0][-1] == AUTYPE.QFQ


def test_etf_cache_uses_none_autype_when_autype_is_omitted(tmp_path):
    FakeSina.calls = []
    FakeBao.calls = []
    FakeEastMoney.calls = []
    FakeYahoo.calls = []
    api = CCache(
        "513130",
        KL_TYPE.K_DAY,
        "2026-06-18",
        "2026-06-18",
        cache_path=tmp_path / "cache.sqlite3",
        now=datetime(2026, 6, 18, 19, 0),
        provider_classes={"sina": FakeSina, "baostock": FakeBao, "eastmoney": FakeEastMoney, "yahoo": FakeYahoo},
        mode="eod",
    )

    list(api.get_kl_data())

    assert FakeYahoo.calls[0][-1] == AUTYPE.NONE


def test_etf_weekly_eod_cache_uses_yahoo(tmp_path):
    FakeBao.calls = []
    FakeEastMoney.calls = []
    FakeYahoo.calls = []
    api = CCache(
        "515030",
        KL_TYPE.K_WEEK,
        "2023-03-20",
        "2026-07-02",
        cache_path=tmp_path / "cache.sqlite3",
        now=datetime(2026, 7, 2, 19, 0),
        provider_classes={"sina": FakeSina, "baostock": FakeBao, "eastmoney": FakeEastMoney, "yahoo": FakeYahoo},
        mode="eod",
    )

    api.refresh()

    assert FakeYahoo.calls[0][:4] == ("515030", KL_TYPE.K_WEEK, "2023-03-20", "2026-07-02")
    assert FakeEastMoney.calls == []
    assert FakeBao.calls == []


def test_etf_daily_eod_cache_falls_back_to_eastmoney_when_yahoo_fails(tmp_path):
    FailingYahoo.calls = []
    FakeEastMoney.calls = []
    api = CCache(
        "515030",
        KL_TYPE.K_DAY,
        "2023-03-20",
        "2026-07-02",
        cache_path=tmp_path / "cache.sqlite3",
        now=datetime(2026, 7, 2, 19, 0),
        provider_classes={"sina": FakeSina, "baostock": FakeBao, "eastmoney": FakeEastMoney, "yahoo": FailingYahoo},
        mode="eod",
    )

    result = api.refresh()

    assert FailingYahoo.calls[0][:4] == ("515030", KL_TYPE.K_DAY, "2023-03-20", "2026-07-02")
    assert FakeEastMoney.calls[0][:4] == ("515030", KL_TYPE.K_DAY, "2023-03-20", "2026-07-02")
    assert result == {"eastmoney": {"inserted": 1, "updated": 0}}


def test_etf_minute_eod_cache_keeps_using_baostock(tmp_path):
    FakeBao.calls = []
    FakeEastMoney.calls = []
    FakeYahoo.calls = []
    api = CCache(
        "515030",
        KL_TYPE.K_30M,
        "2026-06-01",
        "2026-06-18",
        cache_path=tmp_path / "cache.sqlite3",
        now=datetime(2026, 6, 18, 19, 0),
        provider_classes={"sina": FakeSina, "baostock": FakeBao, "eastmoney": FakeEastMoney, "yahoo": FakeYahoo},
        mode="eod",
    )

    api.refresh()

    assert FakeBao.calls[0][:4] == ("sh.515030", KL_TYPE.K_30M, "2026-06-01", "2026-06-18")
    assert FakeEastMoney.calls == []
    assert FakeYahoo.calls == []


def test_refresh_marks_coverage_from_actual_returned_bar_range(tmp_path):
    PartialBao.calls = []
    api = CCache(
        "515030",
        KL_TYPE.K_DAY,
        "2023-03-20",
        "2026-07-02",
        AUTYPE.NONE,
        cache_path=tmp_path / "cache.sqlite3",
        now=datetime(2026, 7, 2, 19, 0),
        provider_classes={"sina": FakeSina, "baostock": FakeBao, "eastmoney": FakeEastMoney, "yahoo": PartialBao},
        mode="eod",
    )

    api.refresh()

    assert not api.store.covers(api.symbol, KL_TYPE.K_DAY, "2023-03-20", "2026-07-02")
    assert api.store.covers(api.symbol, KL_TYPE.K_DAY, "2026-01-05", "2026-07-01")


def test_auto_refresh_does_not_overstate_coverage_when_provider_returns_partial_range(tmp_path):
    PartialBao.calls = []
    api = CCache(
        "515030",
        KL_TYPE.K_DAY,
        "2023-03-20",
        "2026-07-02",
        AUTYPE.NONE,
        cache_path=tmp_path / "cache.sqlite3",
        now=datetime(2026, 7, 2, 19, 0),
        provider_classes={"sina": FakeSina, "baostock": FakeBao, "eastmoney": FakeEastMoney, "yahoo": PartialBao},
        mode="auto",
    )

    api.refresh()

    assert not api.store.covers(api.symbol, KL_TYPE.K_DAY, "2023-03-20", "2026-07-02")
    assert api.store.covers(api.symbol, KL_TYPE.K_DAY, "2026-01-05", "2026-07-01")


def test_subsequent_refresh_uses_a_short_overlap_instead_of_full_window(tmp_path):
    FakeSina.calls = []
    RangeBao.calls = []
    api = CCache(
        "002460",
        KL_TYPE.K_DAY,
        "2026-06-01",
        "2026-06-18",
        cache_path=tmp_path / "cache.sqlite3",
        now=datetime(2026, 6, 18, 19, 0),
        provider_classes={"sina": FakeSina, "baostock": RangeBao},
        mode="eod",
    )

    api.refresh()
    api.refresh()

    assert RangeBao.calls[0][2:4] == ("2026-06-01", "2026-06-18")
    assert RangeBao.calls[1][2:4] == ("2026-06-15", "2026-06-18")


def test_auto_refresh_uses_baostock_for_history_and_sina_for_today(tmp_path):
    FakeSina.calls = []
    FakeBao.calls = []
    api = CCache(
        "002460",
        KL_TYPE.K_5M,
        "2026-06-01",
        "2026-06-18",
        cache_path=tmp_path / "cache.sqlite3",
        now=datetime(2026, 6, 18, 19, 0),
        provider_classes={"sina": FakeSina, "baostock": FakeBao},
        mode="auto",
    )

    result = api.refresh()

    assert FakeBao.calls[0][2:4] == ("2026-06-01", "2026-06-17")
    assert FakeSina.calls[0][2:4] == ("2026-06-18", "2026-06-18")
    assert result == {
        "baostock": {"inserted": 1, "updated": 0},
        "sina": {"inserted": 0, "updated": 1},
    }


def test_end_of_day_skips_one_minute_refresh(tmp_path):
    api = build_api(tmp_path, KL_TYPE.K_1M, datetime(2026, 6, 18, 19, 0))

    assert list(api.get_kl_data()) == []
    assert FakeSina.calls == []
    assert FakeBao.calls == []


def test_cchan_registers_cache_data_source():
    chan = CChan.__new__(CChan)
    chan.data_src = DATA_SRC.CACHE

    assert chan.GetStockAPI() is CCache
