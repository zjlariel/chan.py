from pathlib import Path

from Common.CEnum import DATA_FIELD, KL_TYPE
from Common.CTime import CTime
from DataAPI.CacheStore import CacheStore
from KLine.KLine_Unit import CKLine_Unit


def make_bar(day, hour, minute, close):
    return CKLine_Unit(
        {
            DATA_FIELD.FIELD_TIME: CTime(2026, 6, day, hour, minute, auto=False),
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

    store.upsert_bars("sh600000", KL_TYPE.K_5M, [late, early], "sina")
    store.upsert_bars("sh600000", KL_TYPE.K_5M, [make_bar(18, 9, 35, 9.3)], "baostock")

    bars = store.read_bars("sh600000", KL_TYPE.K_5M, "2026-06-18", "2026-06-18")

    assert [bar.time.to_str() for bar in bars] == ["2026/06/18 09:30", "2026/06/18 09:35"]
    assert bars[-1].close == 9.3


def test_records_coverage_ranges(tmp_path: Path):
    store = CacheStore(tmp_path / "cache.sqlite3")

    store.mark_covered("sh600000", KL_TYPE.K_DAY, "2023-01-01", "2026-06-18", "baostock")

    assert store.covers("sh600000", KL_TYPE.K_DAY, "2024-01-01", "2026-06-18")
    assert not store.covers("sh600000", KL_TYPE.K_DAY, "2022-12-31", "2026-06-18")
