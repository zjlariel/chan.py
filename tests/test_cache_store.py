from pathlib import Path

from Common.CEnum import DATA_FIELD, KL_TYPE
from Common.CTime import CTime
from DataAPI.CacheStore import CacheStore
from KLine.KLine_Unit import CKLine_Unit


def make_bar(day, hour, minute, close, year=2026, month=6):
    return CKLine_Unit(
        {
            DATA_FIELD.FIELD_TIME: CTime(year, month, day, hour, minute, auto=False),
            DATA_FIELD.FIELD_OPEN: close - 0.1,
            DATA_FIELD.FIELD_HIGH: close + 0.1,
            DATA_FIELD.FIELD_LOW: close - 0.2,
            DATA_FIELD.FIELD_CLOSE: close,
            DATA_FIELD.FIELD_VOLUME: 100,
            DATA_FIELD.FIELD_TURNOVER: close * 100,
        }
    )


def test_upserts_and_reads_ordered_bars(tmp_path: Path):
    store = CacheStore(tmp_path / "cache.sqlite3")
    early = make_bar(18, 9, 30, 9.1)
    late = make_bar(18, 9, 35, 9.2)

    first_write = store.upsert_bars("sh600000", KL_TYPE.K_5M, [late, early], "sina")
    repeated_write = store.upsert_bars("sh600000", KL_TYPE.K_5M, [make_bar(18, 9, 35, 9.3)], "baostock")

    bars = store.read_bars("sh600000", KL_TYPE.K_5M, "2026-06-18", "2026-06-18")

    assert [bar.time.to_str() for bar in bars] == ["2026/06/18 09:30", "2026/06/18 09:35"]
    assert bars[-1].close == 9.3
    assert first_write == {"inserted": 2, "updated": 0}
    assert repeated_write == {"inserted": 0, "updated": 1}


def test_records_coverage_ranges(tmp_path: Path):
    store = CacheStore(tmp_path / "cache.sqlite3")
    store.upsert_bars(
        "sh600000",
        KL_TYPE.K_DAY,
        [make_bar(1, 0, 0, 9.1), make_bar(18, 0, 0, 9.2)],
        "baostock",
    )

    store.mark_covered("sh600000", KL_TYPE.K_DAY, "2026-06-01", "2026-06-18", "baostock")

    assert store.covers("sh600000", KL_TYPE.K_DAY, "2026-06-01", "2026-06-18")
    assert not store.covers("sh600000", KL_TYPE.K_DAY, "2026-05-31", "2026-06-18")


def test_coverage_requires_actual_bars_to_span_requested_range(tmp_path: Path):
    store = CacheStore(tmp_path / "cache.sqlite3")
    store.upsert_bars(
        "sh515030",
        KL_TYPE.K_DAY,
        [make_bar(5, 0, 0, 1.0, month=1), make_bar(1, 0, 0, 1.1, month=7)],
        "baostock",
    )
    store.mark_covered("sh515030", KL_TYPE.K_DAY, "2023-03-20", "2026-07-02", "baostock")

    assert not store.covers("sh515030", KL_TYPE.K_DAY, "2023-03-20", "2026-07-02")
    assert store.covers("sh515030", KL_TYPE.K_DAY, "2026-01-05", "2026-07-02")


def test_coverage_accepts_first_available_bar_after_requested_start(tmp_path: Path):
    store = CacheStore(tmp_path / "cache.sqlite3")
    store.upsert_bars(
        "sz159530",
        KL_TYPE.K_DAY,
        [make_bar(day, 0, 0, 1.0, year=2024, month=1) for day in range(10, 32)]
        + [make_bar(day, 0, 0, 1.0, year=2024, month=2) for day in range(1, 5)]
        + [make_bar(2, 0, 0, 1.1, year=2026, month=7)],
        "yahoo",
    )
    store.mark_covered("sz159530", KL_TYPE.K_DAY, "2024-01-10", "2026-07-02", "yahoo")

    assert store.covers("sz159530", KL_TYPE.K_DAY, "2023-03-20", "2026-07-02")


def test_prunes_old_bars_and_reports_latest_timestamp(tmp_path: Path):
    store = CacheStore(tmp_path / "cache.sqlite3")
    store.upsert_bars(
        "sh600000",
        KL_TYPE.K_5M,
        [make_bar(17, 9, 30, 9.1), make_bar(18, 9, 30, 9.2)],
        "baostock",
    )

    deleted = store.prune_before("sh600000", KL_TYPE.K_5M, "2026-06-18")

    assert deleted == 1
    assert store.latest_timestamp("sh600000", KL_TYPE.K_5M) == "2026-06-18 09:30"


def test_saves_and_reads_stock_name(tmp_path: Path):
    store = CacheStore(tmp_path / "cache.sqlite3")

    store.upsert_stock_name("sz000001", "\u5e73\u5b89\u94f6\u884c", "baostock")

    assert store.stock_name("sz000001") == "\u5e73\u5b89\u94f6\u884c"
