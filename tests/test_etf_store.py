from App.etf_store import EtfStore


def test_updates_watch_etf_to_holding_and_clears_cost_after_exit(tmp_path):
    store = EtfStore(tmp_path / "cache.sqlite3")
    store.initialize()

    store.set_position("513130", "恒生科技ETF", quantity=0, category="港股科技", tracking_index="恒生科技指数")
    watching = {position["symbol"]: position for position in store.list_positions()}["513130"]
    assert watching["status"] == "watching"
    assert watching["cost_price"] is None
    assert watching["category"] == "港股科技"
    assert watching["tracking_index"] == "恒生科技指数"

    store.set_position("513130", "恒生科技ETF", quantity=10000, available_quantity=10000, cost_price=0.733, category="港股科技")
    holding = {position["symbol"]: position for position in store.list_positions()}["513130"]
    assert holding["status"] == "holding"
    assert holding["quantity"] == 10000
    assert holding["available_quantity"] == 10000
    assert holding["cost_price"] == 0.733

    store.set_position("513130", "恒生科技ETF", quantity=0, category="港股科技")
    exited = {position["symbol"]: position for position in store.list_positions()}["513130"]
    assert exited["status"] == "watching"
    assert exited["cost_price"] is None


def test_rejects_invalid_etf_symbol_and_missing_cost_for_holding(tmp_path):
    store = EtfStore(tmp_path / "cache.sqlite3")

    try:
        store.set_position("688008", "澜起科技", quantity=0)
    except ValueError as exc:
        assert "不支持的 ETF 代码" in str(exc)
    else:
        raise AssertionError("应拒绝非 ETF 号段")

    try:
        store.set_position("513130", "恒生科技ETF", quantity=1000)
    except ValueError as exc:
        assert "成本价" in str(exc)
    else:
        raise AssertionError("持仓 ETF 应要求成本价")


def test_deletes_etf_by_marking_it_inactive_without_losing_record(tmp_path):
    store = EtfStore(tmp_path / "cache.sqlite3")
    store.initialize()
    store.set_position("159995", "芯片ETF", quantity=0, category="半导体")

    deleted = store.delete_position("159995")

    assert deleted is True
    assert "159995" not in {position["symbol"] for position in store.list_positions()}
    inactive_positions = {position["symbol"]: position for position in store.list_positions(active_only=False)}
    assert inactive_positions["159995"]["active"] == 0
    assert inactive_positions["159995"]["name"] == "芯片ETF"


def test_delete_etf_reports_missing_symbol_without_creating_record(tmp_path):
    store = EtfStore(tmp_path / "cache.sqlite3")

    deleted = store.delete_position("513130")

    assert deleted is False
    assert "513130" not in {position["symbol"] for position in store.list_positions(active_only=False)}
