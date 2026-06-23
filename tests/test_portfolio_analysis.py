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

    assert advice["priority"] == "风险提示"
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

    assert advice["priority"] == "重点关注"
    assert "30分钟买点" in advice["basis"]


def test_holding_advice_uses_newest_sell_signal_and_keeps_weekly_as_context():
    advice = build_advice(
        {"symbol": "002536", "name": "飞龙股份", "quantity": 400, "cost_price": 41.343, "status": "holding"},
        {
            "K_WEEK": {"buy_sell_points": [{"time": "2026/05/22", "is_buy": False, "type": "1p"}]},
            "K_DAY": {"buy_sell_points": []},
            "K_30M": {"buy_sell_points": []},
            "K_5M": {"buy_sell_points": [{"time": "2026/06/23 10:30", "is_buy": False, "type": "2"}]},
        },
        latest_price=43.07,
    )

    assert advice["priority"] == "留意卖点"
    assert "5分钟卖点 2（2026/06/23 10:30）" in advice["basis"]
    assert "高周期背景：周线卖点 1p（2026/05/22）" in advice["basis"]
