from unittest.mock import Mock, patch

import pytest

from Chan import CChan
from Common.CEnum import AUTYPE, DATA_SRC, KL_TYPE
from DataAPI.SinaAPI import CSina


SINA_ROWS = [
    {
        "day": "2026-06-17 14:59:00",
        "open": "9.00",
        "high": "9.20",
        "low": "8.90",
        "close": "9.10",
        "volume": "100",
        "amount": "910",
    },
    {
        "day": "2026-06-18 09:30:00",
        "open": "9.10",
        "high": "9.30",
        "low": "9.00",
        "close": "9.20",
        "volume": "200",
        "amount": "1840",
    },
]


@pytest.mark.parametrize(
    ("code", "expected"),
    [
        ("600000", "sh600000"),
        ("513130", "sh513130"),
        ("159530", "sz159530"),
        ("sz.000001", "sz000001"),
        ("sh600000", "sh600000"),
    ],
)
def test_normalizes_a_share_and_etf_symbols(code, expected):
    assert CSina.normalize_symbol(code) == expected


@pytest.mark.parametrize(
    ("k_type", "expected_scale"),
    [
        (KL_TYPE.K_1M, 1),
        (KL_TYPE.K_5M, 5),
        (KL_TYPE.K_15M, 15),
        (KL_TYPE.K_30M, 30),
        (KL_TYPE.K_60M, 60),
    ],
)
def test_maps_supported_minute_periods(k_type, expected_scale):
    assert CSina.scale_for(k_type) == expected_scale


def test_rejects_unsupported_symbol_and_period():
    with pytest.raises(ValueError, match="A-share"):
        CSina.normalize_symbol("430047")
    with pytest.raises(ValueError, match="minute"):
        CSina.scale_for(KL_TYPE.K_DAY)


@patch("DataAPI.SinaAPI.requests.get")
def test_converts_and_filters_sina_rows(mock_get):
    response = Mock()
    response.json.return_value = SINA_ROWS
    mock_get.return_value = response

    api = CSina("600000", KL_TYPE.K_1M, "2026-06-18", "2026-06-18", AUTYPE.NONE)

    items = list(api.get_kl_data())

    assert [item.time.to_str() for item in items] == ["2026/06/18 09:30"]
    assert items[0].open == 9.1
    assert items[0].close == 9.2
    assert items[0].trade_info.metric["volume"] == 200.0
    mock_get.assert_called_once_with(
        CSina.KLINE_URL,
        params={"symbol": "sh600000", "scale": 1, "ma": "no", "datalen": 1023},
        timeout=10,
    )


def test_cchan_registers_sina_data_source():
    chan = CChan.__new__(CChan)
    chan.data_src = DATA_SRC.SINA

    assert chan.GetStockAPI() is CSina
