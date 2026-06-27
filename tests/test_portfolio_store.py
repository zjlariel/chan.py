from App.portfolio_store import PortfolioStore


def test_initializes_confirmed_positions_without_overwriting_existing_records(tmp_path):
    store = PortfolioStore(tmp_path / "cache.sqlite3")

    store.initialize()
    store.set_position("002536", "飞龙股份", quantity=500, available_quantity=500, cost_price=40.0)
    store.initialize()

    positions = {position["symbol"]: position for position in store.list_positions()}
    assert len(positions) == 5
    assert positions["688008"]["name"] == "澜起科技"
    assert positions["002536"]["quantity"] == 500
    assert positions["002536"]["cost_price"] == 40.0


def test_updates_watch_stock_to_holding_and_clears_cost_after_exit(tmp_path):
    store = PortfolioStore(tmp_path / "cache.sqlite3")
    store.initialize()

    store.set_position("000001", "平安银行", quantity=0)
    watching = {position["symbol"]: position for position in store.list_positions()}["000001"]
    assert watching["status"] == "watching"
    assert watching["cost_price"] is None

    store.set_position("000001", "平安银行", quantity=100, available_quantity=100, cost_price=11.2)
    holding = {position["symbol"]: position for position in store.list_positions()}["000001"]
    assert holding["status"] == "holding"
    assert holding["cost_price"] == 11.2

    store.set_position("000001", "平安银行", quantity=0)
    exited = {position["symbol"]: position for position in store.list_positions()}["000001"]
    assert exited["status"] == "watching"
    assert exited["cost_price"] is None


def test_deletes_position_by_marking_it_inactive_without_losing_record(tmp_path):
    store = PortfolioStore(tmp_path / "cache.sqlite3")
    store.initialize()
    store.set_position("000001", "平安银行", quantity=0)

    deleted = store.delete_position("000001")

    assert deleted is True
    assert "000001" not in {position["symbol"] for position in store.list_positions()}
    inactive_positions = {position["symbol"]: position for position in store.list_positions(active_only=False)}
    assert inactive_positions["000001"]["active"] == 0
    assert inactive_positions["000001"]["name"] == "平安银行"


def test_delete_position_reports_missing_stock_without_creating_record(tmp_path):
    store = PortfolioStore(tmp_path / "cache.sqlite3")

    deleted = store.delete_position("000001")

    assert deleted is False
    assert "000001" not in {position["symbol"] for position in store.list_positions(active_only=False)}
