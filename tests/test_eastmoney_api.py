from unittest.mock import Mock, patch

import requests

from Common.CEnum import AUTYPE, DATA_FIELD, KL_TYPE
from DataAPI.EastMoneyAPI import CEastMoney


@patch("DataAPI.EastMoneyAPI.requests.get")
def test_converts_eastmoney_daily_etf_rows(mock_get):
    response = Mock()
    response.json.return_value = {
        "data": {
            "name": "华夏中证新能源汽车ETF",
            "klines": [
                "2023-03-20,1.000,1.020,1.030,0.990,1000,2000.5,1.2,0.01,0.0001,0.5",
                "2023-03-21,1.020,1.040,1.050,1.010,1100,2100.5,1.3,0.02,0.0002,0.6",
            ],
        }
    }
    mock_get.return_value = response
    api = CEastMoney("515030", KL_TYPE.K_DAY, "2023-03-20", "2026-07-02", AUTYPE.NONE)

    bars = list(api.get_kl_data())

    assert api.name == "华夏中证新能源汽车ETF"
    assert [bar.time.to_str() for bar in bars] == ["2023/03/20", "2023/03/21"]
    assert bars[0].open == 1.0
    assert bars[0].close == 1.02
    assert bars[0].trade_info.metric[DATA_FIELD.FIELD_VOLUME] == 1000
    assert bars[0].trade_info.metric[DATA_FIELD.FIELD_TURNOVER] == 2000.5
    mock_get.assert_called_once()
    assert mock_get.call_args.kwargs["params"]["secid"] == "1.515030"
    assert mock_get.call_args.kwargs["params"]["klt"] == "101"
    assert mock_get.call_args.kwargs["params"]["fqt"] == "0"
    assert mock_get.call_args.kwargs["params"]["beg"] == "20230320"


@patch("DataAPI.EastMoneyAPI.requests.get")
def test_weekly_etf_uses_eastmoney_week_period(mock_get):
    response = Mock()
    response.json.return_value = {"data": {"klines": ["2023-03-24,1,2,3,0.5,100,200,1,0,0,0"]}}
    mock_get.return_value = response
    api = CEastMoney("159530", KL_TYPE.K_WEEK, "2023-03-20", "2026-07-02", AUTYPE.NONE)

    bars = list(api.get_kl_data())

    assert len(bars) == 1
    assert mock_get.call_args.kwargs["params"]["secid"] == "0.159530"
    assert mock_get.call_args.kwargs["params"]["klt"] == "102"


def test_rejects_unsupported_eastmoney_level():
    api = CEastMoney("515030", KL_TYPE.K_30M, "2023-03-20", "2026-07-02", AUTYPE.NONE)

    try:
        list(api.get_kl_data())
    except ValueError as exc:
        assert "东方财富不支持" in str(exc)
    else:
        raise AssertionError("应拒绝不支持的东方财富 K 线级别")


@patch("DataAPI.EastMoneyAPI.requests.get")
def test_retries_transient_eastmoney_request_errors(mock_get):
    response = Mock()
    response.json.return_value = {"data": {"klines": ["2023-03-20,1,2,3,0.5,100,200,1,0,0,0"]}}
    mock_get.side_effect = [requests.exceptions.ProxyError("断开"), response]
    api = CEastMoney("515030", KL_TYPE.K_DAY, "2023-03-20", "2026-07-02", AUTYPE.NONE)

    bars = list(api.get_kl_data())

    assert len(bars) == 1
    assert mock_get.call_count == 2
