from datetime import date

from Common.CEnum import DATA_SRC, KL_TYPE


def test_default_arguments_include_levels_and_start_dates():
    from CLI import parse_args

    options = parse_args([], today=date(2026, 6, 21))

    assert options.data_src == DATA_SRC.BAO_STOCK
    assert options.code == "sz.000001"
    assert options.lv_list == [KL_TYPE.K_WEEK, KL_TYPE.K_DAY, KL_TYPE.K_30M, KL_TYPE.K_5M]
    assert options.begin_time == {
        KL_TYPE.K_WEEK: "2019-11-25",
        KL_TYPE.K_DAY: "2023-03-09",
        KL_TYPE.K_30M: "2025-12-23",
        KL_TYPE.K_5M: "2026-06-01",
    }


def test_explicit_arguments_override_defaults():
    from CLI import parse_args

    options = parse_args(
        [
            "--data-src", "akshare",
            "--code", "sh.600000",
            "--start", "2020-01-02",
            "--end", "2024-01-01",
            "--kl-type", "K_DAY,K_30M",
            "--output-dir", "images",
        ],
        today=date(2026, 6, 21),
    )

    assert options.data_src == DATA_SRC.AKSHARE
    assert options.end_time == "2024-01-01"
    assert options.lv_list == [KL_TYPE.K_DAY, KL_TYPE.K_30M]
    assert options.begin_time == {KL_TYPE.K_DAY: "2020-01-02", KL_TYPE.K_30M: "2020-01-02"}
    assert options.output_path.as_posix() == "images/sh.600000.png"


def test_sina_data_source_is_supported():
    from CLI import parse_args

    options = parse_args(["--data-src", "sina"])

    assert options.data_src == DATA_SRC.SINA
