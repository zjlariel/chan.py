from unittest.mock import Mock, patch

import pytest

from Common.CEnum import KL_TYPE
from DataAPI.BaoStockAPI import CBaoStock


def teardown_function():
    CBaoStock.is_connect = None
    CBaoStock.keep_alive_depth = 0


@pytest.mark.parametrize(
    ("code", "expected"),
    [
        ("002536", "sz.002536"),
        ("600000", "sh.600000"),
        ("513130", "sh.513130"),
        ("159530", "sz.159530"),
        ("sz002536", "sz.002536"),
        ("sh.000001", "sh.000001"),
        ("sh513130", "sh.513130"),
    ],
)
@patch("DataAPI.BaoStockAPI.bs.query_stock_basic")
def test_normalizes_shenzhen_and_shanghai_symbols(mock_query, code, expected):
    response = Mock(error_code="0")
    response.get_row_data.return_value = [expected, "name", "", "", "1", "1"]
    mock_query.return_value = response

    api = CBaoStock(code, begin_date="2026-01-01", end_date="2026-01-02")

    assert api.code == expected
    mock_query.assert_called_once_with(code=expected)


@patch("DataAPI.BaoStockAPI.bs.query_history_k_data_plus")
@patch("DataAPI.BaoStockAPI.bs.query_stock_basic")
def test_allows_etf_minute_k_lines(mock_query_basic, mock_query_history):
    basic_response = Mock(error_code="0")
    basic_response.get_row_data.return_value = ["sh.513130", "恒生科技ETF", "", "", "5", "1"]
    mock_query_basic.return_value = basic_response
    history_response = Mock(error_code="0")
    history_response.next.return_value = False
    mock_query_history.return_value = history_response

    api = CBaoStock("513130", k_type=KL_TYPE.K_30M)

    assert list(api.get_kl_data()) == []
    mock_query_history.assert_called_once()


@pytest.mark.parametrize("code", ["430047", "abc", "12345"])
def test_rejects_unsupported_bare_symbols(code):
    with pytest.raises(ValueError, match="unsupported A-share symbol"):
        CBaoStock.normalize_symbol(code)


@patch("DataAPI.BaoStockAPI.bs.logout")
@patch("DataAPI.BaoStockAPI.bs.login")
def test_keep_alive_defers_logout_until_command_finishes(mock_login, mock_logout):
    mock_login.return_value = Mock(error_code="0")

    with CBaoStock.keep_alive():
        CBaoStock.do_init()
        CBaoStock.do_close()
        CBaoStock.do_init()

    mock_login.assert_called_once()
    mock_logout.assert_called_once()
    assert CBaoStock.is_connect is None
