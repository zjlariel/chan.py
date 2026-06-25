from App.portfolio_analysis import build_observation


def test_build_observation_outputs_objective_level_facts():
    observation = build_observation(
        {"symbol": "002536", "name": "飞龙股份", "quantity": 400, "cost_price": 41.343, "status": "holding"},
        {
            "K_WEEK": {
                "data_range": {"start": "2026/01/01", "end": "2026/06/19"},
                "segments": [
                    {"direction": "DOWN", "begin_time": "2026/02/01", "end_time": "2026/04/01"},
                    {"direction": "UP", "begin_time": "2026/04/02", "end_time": "2026/06/19"},
                ],
                "buy_sell_points": [{"time": "2026/05/22", "is_buy": False, "type": "1p"}],
                "indicators": {
                    "latest": {
                        "macd": {"time": "2026/06/19", "dif": 0.12, "dea": 0.08, "macd": 0.08},
                        "kdj": {"time": "2026/06/19", "k": 55.0, "d": 50.0, "j": 65.0},
                    },
                    "crosses": {"macd": [], "kdj": []},
                },
            },
            "K_DAY": {
                "data_range": {"start": "2026/04/01", "end": "2026/06/23"},
                "buy_sell_points": [
                    {"time": "2026/06/18", "is_buy": False, "type": "3a"},
                    {"time": "2026/06/23", "is_buy": True, "type": "2"},
                ],
                "bi": [
                    {"direction": "DOWN", "begin_time": "2026/06/10", "end_time": "2026/06/18", "begin_value": 46.0, "end_value": 40.0},
                    {"direction": "UP", "begin_time": "2026/06/18", "end_time": "2026/06/23", "begin_value": 40.0, "end_value": 43.0},
                ],
                "segments": [
                    {"direction": "UP", "begin_time": "2026/06/01", "end_time": "2026/06/23", "begin_value": 35.0, "end_value": 43.0},
                ],
                "zs": [
                    {"begin_time": "2026/06/11", "end_time": "2026/06/20", "low": 39.5, "high": 42.0, "is_sure": True},
                ],
                "indicators": {
                    "latest": {
                        "macd": {"time": "2026/06/23", "dif": 0.02, "dea": 0.08, "macd": -0.12},
                        "kdj": {"time": "2026/06/23", "k": 41.0, "d": 44.0, "j": 35.0},
                    },
                    "crosses": {
                        "macd": [
                            {"time": "2026/06/19", "type": "dead", "dif": -0.1, "dea": 0.02, "macd": -0.24},
                            {"time": "2026/06/20", "type": "golden", "dif": 0.1, "dea": -0.05, "macd": 0.3},
                        ],
                        "kdj": [{"time": "2026/06/23", "type": "dead", "k": 41.0, "d": 44.0, "j": 35.0}],
                    },
                },
            },
            "K_30M": {
                "data_range": {"start": "2026/06/01 09:30", "end": "2026/06/23 14:30"},
                "buy_sell_points": [],
                "indicators": {
                    "latest": {"macd": None, "kdj": None},
                    "crosses": {"macd": [], "kdj": []},
                },
            },
        },
        latest_price=43.07,
    )

    assert observation["header"] == "飞龙股份 (002536)：持仓，最新价 43.070，高于成本 4.18%"
    assert observation["levels"][0] == "周线背景：数据 2026/01/01 至 2026/06/19；趋势 线段向上（2026/04/02 至 2026/06/19）"
    assert observation["levels"][1] == "日线：数据 2026/04/01 至 2026/06/23；最新买卖点 买 2（2026/06/23）；MACD DIF 0.020 / DEA 0.080 / 柱 -0.120（2026/06/23）；MACD交叉 金叉（2026/06/20）；KDJ K 41.00 / D 44.00 / J 35.00（2026/06/23）；KDJ交叉 死叉（2026/06/23）"
    assert observation["levels"][2] == "30分钟：数据 2026/06/01 09:30 至 2026/06/23 14:30；最新买卖点 无；MACD 无；MACD交叉 无；KDJ 无；KDJ交叉 无"
    assert observation["details"] == [
        "详细报告：",
        "  周线背景：",
        "    数据：2026/01/01 至 2026/06/19",
        "    趋势：线段向上（2026/04/02 至 2026/06/19）",
        "  日线：",
        "    数据：2026/04/01 至 2026/06/23",
        "    最新指标：MACD DIF 0.020 / DEA 0.080 / 柱 -0.120（2026/06/23）；KDJ K 41.00 / D 44.00 / J 35.00（2026/06/23）",
        "    最近买卖点：",
        "      - 卖 3a（2026/06/18）",
        "      - 买 2（2026/06/23）",
        "    最近 MACD 交叉：",
        "      - 死叉（2026/06/19）",
        "      - 金叉（2026/06/20）",
        "    最近 KDJ 交叉：",
        "      - 死叉（2026/06/23）",
        "    结构：",
        "      最新笔：向上（2026/06/18 至 2026/06/23，40.000 -> 43.000）",
        "      最新线段：向上（2026/06/01 至 2026/06/23，35.000 -> 43.000）",
        "      最新中枢：2026/06/11 至 2026/06/20，区间 39.500 - 42.000，已确认",
        "  30分钟：",
        "    数据：2026/06/01 09:30 至 2026/06/23 14:30",
        "    最新指标：MACD 无；KDJ 无",
        "    最近买卖点：无",
        "    最近 MACD 交叉：无",
        "    最近 KDJ 交叉：无",
        "    结构：无",
    ]


def test_build_observation_outputs_watch_status_without_strategy_priority():
    observation = build_observation(
        {"symbol": "000001", "name": "平安银行", "quantity": 0, "cost_price": None, "status": "watching"},
        {},
        latest_price=11.2,
    )

    assert observation["header"] == "平安银行 (000001)：观察，最新价 11.200"
    assert observation["levels"] == ["周线：无数据", "日线：无数据", "30分钟：无数据"]


def test_weekly_background_falls_back_to_latest_bi_trend():
    observation = build_observation(
        {"symbol": "000001", "name": "平安银行", "quantity": 0, "cost_price": None, "status": "watching"},
        {
            "K_WEEK": {
                "data_range": {"start": "2026/01/01", "end": "2026/06/19"},
                "segments": [],
                "bi": [
                    {"direction": "UP", "begin_time": "2026/03/01", "end_time": "2026/05/01"},
                    {"direction": "DOWN", "begin_time": "2026/05/02", "end_time": "2026/06/19"},
                ],
            },
        },
        latest_price=11.2,
    )

    assert observation["levels"][0] == "周线背景：数据 2026/01/01 至 2026/06/19；趋势 笔向下（2026/05/02 至 2026/06/19）"
