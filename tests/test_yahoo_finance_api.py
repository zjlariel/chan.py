from unittest.mock import Mock, patch

from Common.CEnum import AUTYPE, DATA_FIELD, KL_TYPE
from DataAPI.YahooFinanceAPI import CYahooFinance


@patch("DataAPI.YahooFinanceAPI.requests.get")
def test_converts_yahoo_daily_etf_rows(mock_get):
    response = Mock()
    response.json.return_value = {
        "chart": {
            "result": [
                {
                    "meta": {"symbol": "515030.SS", "shortName": "新能源车ETF"},
                    "timestamp": [1679270400, 1679356800],
                    "indicators": {
                        "quote": [
                            {
                                "open": [1.0, 1.02],
                                "high": [1.03, 1.05],
                                "low": [0.99, 1.01],
                                "close": [1.02, 1.04],
                                "volume": [1000, 1100],
                            }
                        ]
                    },
                }
            ],
            "error": None,
        }
    }
    mock_get.return_value = response
    api = CYahooFinance("515030", KL_TYPE.K_DAY, "2023-03-20", "2026-07-02", AUTYPE.NONE)

    bars = list(api.get_kl_data())

    assert api.name == "新能源车ETF"
    assert [bar.time.to_str() for bar in bars] == ["2023/03/20", "2023/03/21"]
    assert bars[0].open == 1.0
    assert bars[0].close == 1.02
    assert bars[0].trade_info.metric[DATA_FIELD.FIELD_VOLUME] == 1000
    assert bars[0].trade_info.metric[DATA_FIELD.FIELD_TURNOVER] == 0
    mock_get.assert_called_once()
    assert mock_get.call_args.args[0].endswith("/515030.SS")
    assert mock_get.call_args.kwargs["params"]["interval"] == "1d"
    assert mock_get.call_args.kwargs["params"]["period1"] == "1679270400"


@patch("DataAPI.YahooFinanceAPI.requests.get")
def test_skips_invalid_yahoo_partial_rows(mock_get):
    response = Mock()
    response.json.return_value = {
        "chart": {
            "result": [
                {
                    "timestamp": [1679270400, 1679356800],
                    "indicators": {
                        "quote": [
                            {
                                "open": [1.0, 0.0],
                                "high": [1.2, 0.0],
                                "low": [0.9, 0.0],
                                "close": [1.1, 1.13],
                                "volume": [1000, 0],
                            }
                        ]
                    },
                }
            ],
            "error": None,
        }
    }
    mock_get.return_value = response

    rows = list(CYahooFinance("515030", KL_TYPE.K_DAY, "2023-03-20", "2023-03-21", AUTYPE.NONE).get_kl_data())

    assert [row.time.to_str() for row in rows] == ["2023/03/20"]


@patch("DataAPI.YahooFinanceAPI.requests.get")
def test_weekly_etf_uses_yahoo_week_interval(mock_get):
    response = Mock()
    response.json.return_value = {
        "chart": {
            "result": [
                {
                    "timestamp": [1679184000],
                    "indicators": {
                        "quote": [
                            {"open": [1], "high": [2], "low": [0.5], "close": [1.5], "volume": [100]}
                        ]
                    },
                }
            ],
            "error": None,
        }
    }
    mock_get.return_value = response
    api = CYahooFinance("159530", KL_TYPE.K_WEEK, "2023-03-20", "2026-07-02", AUTYPE.NONE)

    bars = list(api.get_kl_data())

    assert len(bars) == 1
    assert mock_get.call_args.args[0].endswith("/159530.SZ")
    assert mock_get.call_args.kwargs["params"]["interval"] == "1wk"


def test_rejects_unsupported_yahoo_level():
    api = CYahooFinance("515030", KL_TYPE.K_30M, "2023-03-20", "2026-07-02", AUTYPE.NONE)

    try:
        list(api.get_kl_data())
    except ValueError as exc:
        assert "Yahoo Finance 不支持" in str(exc)
    else:
        raise AssertionError("应拒绝不支持的 Yahoo Finance K 线级别")
