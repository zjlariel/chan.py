from App.portfolio_analysis import build_advice


def test_holding_advice_prioritizes_sell_signal_and_cost_context():
    advice = build_advice(
        {"symbol": "002536", "name": "飞龙股份", "quantity": 400, "cost_price": 41.343, "status": "holding"},
        {
            "K_WEEK": {"buy_sell_points": []},
            "K_DAY": {"buy_sell_points": [{"time": "2026/06/23", "is_buy": False, "type": "2"}]},
            "K_30M": {"buy_sell_points": []},
            "K_5M": {"buy_sell_points": []},
        },
        latest_price=43.07,
    )

    assert advice["priority"] == "日线卖点待30分钟确认"
    assert "日线卖点" in advice["basis"]
    assert "高于成本 4.18%" in advice["basis"]


def test_watch_advice_prioritizes_day_or_30m_buy_signal():
    advice = build_advice(
        {"symbol": "000001", "name": "平安银行", "quantity": 0, "cost_price": None, "status": "watching"},
        {
            "K_WEEK": {"buy_sell_points": []},
            "K_DAY": {"buy_sell_points": []},
            "K_30M": {"buy_sell_points": [{"time": "2026/06/23 10:00", "is_buy": True, "type": "1,2"}]},
            "K_5M": {"buy_sell_points": []},
        },
        latest_price=11.2,
    )

    assert advice["priority"] == "30分钟买点，等待日线确认"
    assert "30分钟买点" in advice["basis"]


def test_holding_advice_uses_newest_sell_signal_and_keeps_weekly_as_context():
    advice = build_advice(
        {"symbol": "002536", "name": "飞龙股份", "quantity": 400, "cost_price": 41.343, "status": "holding"},
        {
            "K_WEEK": {"buy_sell_points": [{"time": "2026/05/22", "is_buy": False, "type": "1p"}]},
            "K_DAY": {"buy_sell_points": []},
            "K_30M": {"buy_sell_points": []},
            "K_30M": {"buy_sell_points": [{"time": "2026/06/23 10:30", "is_buy": False, "type": "2"}]},
        },
        latest_price=43.07,
    )

    assert advice["priority"] == "30分钟卖点，等待日线确认"
    assert "30分钟卖点 2（2026/06/23 10:30）" in advice["basis"]
    assert "周线背景：周线卖点 1p（2026/05/22）" in advice["basis"]


def test_holding_day_buy_requires_30m_confirmation_before_add_candidate():
    position = {"symbol": "002536", "name": "飞龙股份", "quantity": 400, "cost_price": 41.343, "status": "holding"}
    levels = {
        "K_WEEK": {"buy_sell_points": []},
        "K_DAY": {"buy_sell_points": [{"time": "2026/06/23", "is_buy": True, "type": "1"}]},
        "K_30M": {"buy_sell_points": []},
    }

    waiting = build_advice(position, levels, latest_price=43.07)
    levels["K_30M"]["buy_sell_points"] = [{"time": "2026/06/23 14:30", "is_buy": True, "type": "2"}]
    confirmed = build_advice(position, levels, latest_price=43.07)

    assert waiting["priority"] == "日线买点待30分钟确认"
    assert confirmed["priority"] == "加仓候选"
