from App.portfolio_analysis import build_model_item, build_observation


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
                        "ma": {"time": "2026/06/23", "ma5": 42.5, "ma10": 41.8, "ma20": 40.5, "ma60": 38.0},
                        "boll": {"time": "2026/06/23", "mid": 40.5, "up": 45.0, "down": 36.0, "position": "upper_half", "band_width": 0.2222222222},
                        "rsi": {"time": "2026/06/23", "rsi": 58.2},
                        "volume": {"time": "2026/06/23", "volume": 1200000, "volume_ma5": 1000000, "volume_ma20": 800000, "volume_ratio_ma5": 1.2, "volume_ratio_ma20": 1.5},
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
        "  中长线决策：",
        "    日线结构：最新线段已确认，方向向上（2026/06/01 至 2026/06/23）",
        "    日线买点：买 2（2026/06/23），距最新日线 0 天，当前有效",
        "    日线卖点：卖 3a（2026/06/18），已被后续买 2（2026/06/23）覆盖",
        "    30分钟执行：无最新买点；30分钟尚未转强，适合观察挂低",
        "    买点标签：日线买点当前有效",
        "    卖点标签：日线卖点已被买点覆盖",
        "  日线：",
        "    数据：2026/04/01 至 2026/06/23",
        "    最新指标：MACD DIF 0.020 / DEA 0.080 / 柱 -0.120（2026/06/23）；KDJ K 41.00 / D 44.00 / J 35.00（2026/06/23）",
        "    趋势过滤：MA5 42.500 / MA10 41.800 / MA20 40.500 / MA60 38.000（2026/06/23），价格位于 MA20 上方",
        "    动量确认：MACD DIF 0.020 / DEA 0.080 / 柱 -0.120（2026/06/23）；KDJ K 41.00 / D 44.00 / J 35.00（2026/06/23）；RSI14 58.20（2026/06/23）",
        "    波动位置：BOLL MID 40.500 / UP 45.000 / DOWN 36.000（2026/06/23），上半区，带宽 22.22%",
        "    量能确认：成交量 1200000，较5周期均量 1.20 倍，较20周期均量 1.50 倍（2026/06/23）",
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
        "    趋势过滤：无",
        "    动量确认：MACD 无；KDJ 无；RSI14 无",
        "    波动位置：无",
        "    量能确认：无",
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


def test_model_item_uses_daily_decision_and_m30_execution_reference():
    item = build_model_item(
        {"symbol": "601138", "name": "工业富联", "quantity": 0, "cost_price": None, "status": "watching"},
        {
            "K_DAY": {
                "data_range": {"start": "2026/04/01", "end": "2026/06/29"},
                "buy_sell_points": [
                    {"time": "2026/06/20", "is_buy": False, "type": "1"},
                    {"time": "2026/06/29", "is_buy": True, "type": "2s"},
                ],
            },
            "K_30M": {
                "data_range": {"start": "2026/06/20 09:30", "end": "2026/06/29 15:00"},
                "buy_sell_points": [
                    {"time": "2026/06/27 14:30", "is_buy": False, "type": "1"},
                    {"time": "2026/06/29 14:30", "is_buy": True, "type": "1p"},
                ],
            },
        },
        latest_price=70.5,
    )

    assert item["daily_decision"]["label"] == "日线买点当前有效"
    assert item["m30_execution"]["hint"] == "30分钟买点过夜，仅作参考，次日需重看"
    assert "linkage" not in item


def test_model_item_exposes_daily_sell_risk_for_holdings():
    item = build_model_item(
        {"symbol": "002536", "name": "飞龙股份", "quantity": 400, "cost_price": 41.343, "status": "holding"},
        {
            "K_DAY": {
                "data_range": {"start": "2026/04/01", "end": "2026/06/30"},
                "buy_sell_points": [
                    {"time": "2026/06/20", "is_buy": True, "type": "2"},
                    {"time": "2026/06/30", "is_buy": False, "type": "1"},
                ],
            },
            "K_30M": {
                "data_range": {"start": "2026/06/20 09:30", "end": "2026/06/30 15:00"},
                "buy_sell_points": [{"time": "2026/06/30 14:30", "is_buy": False, "type": "1"}],
            },
        },
        latest_price=43.0,
    )

    assert item["daily_sell_risk"]["label"] == "日线卖点当前有效"
    assert item["daily_sell_risk"]["sell"]["point"]["text"] == "卖 1（2026/06/30）"
    assert item["position_decision"]["label"] == "持仓风控：日线卖点当前有效"
    assert item["position_decision"]["focus"] == "sell"


def test_model_item_includes_recent_evidence_sequences():
    item = build_model_item(
        {"symbol": "601138", "name": "工业富联", "quantity": 0, "cost_price": None, "status": "watching"},
        {
            "K_WEEK": {
                "buy_sell_points": [
                    {"time": "2026/01/02", "is_buy": True, "type": "1"},
                    {"time": "2026/02/06", "is_buy": False, "type": "2"},
                    {"time": "2026/03/06", "is_buy": True, "type": "2s"},
                    {"time": "2026/04/03", "is_buy": False, "type": "1p"},
                ],
                "segments": [
                    {"idx": 1, "direction": "UP", "begin_time": "2026/01/02", "end_time": "2026/02/06"},
                    {"idx": 2, "direction": "DOWN", "begin_time": "2026/02/06", "end_time": "2026/03/06"},
                    {"idx": 3, "direction": "UP", "begin_time": "2026/03/06", "end_time": "2026/04/03"},
                    {"idx": 4, "direction": "DOWN", "begin_time": "2026/04/03", "end_time": "2026/05/08"},
                ],
                "zs": [
                    {"begin_time": "2026/01/02", "end_time": "2026/02/06", "low": 10.0, "high": 12.0, "is_sure": True},
                    {"begin_time": "2026/03/06", "end_time": "2026/04/03", "low": 11.0, "high": 13.0, "is_sure": False},
                    {"begin_time": "2026/04/03", "end_time": "2026/05/08", "low": 12.0, "high": 14.0, "is_sure": True},
                ],
            },
            "K_DAY": {
                "data_range": {"start": "2026/04/01", "end": "2026/06/29"},
                "buy_sell_points": [
                    {"time": "2026/06/01", "is_buy": True, "type": "1"},
                    {"time": "2026/06/05", "is_buy": False, "type": "1"},
                    {"time": "2026/06/10", "is_buy": True, "type": "2"},
                    {"time": "2026/06/15", "is_buy": False, "type": "2"},
                    {"time": "2026/06/20", "is_buy": True, "type": "3a"},
                    {"time": "2026/06/29", "is_buy": True, "type": "2s"},
                ],
                "bi": [
                    {"idx": 1, "direction": "DOWN", "begin_time": "2026/06/01", "end_time": "2026/06/05"},
                    {"idx": 2, "direction": "UP", "begin_time": "2026/06/05", "end_time": "2026/06/10"},
                    {"idx": 3, "direction": "DOWN", "begin_time": "2026/06/10", "end_time": "2026/06/15"},
                    {"idx": 4, "direction": "UP", "begin_time": "2026/06/15", "end_time": "2026/06/20"},
                    {"idx": 5, "direction": "DOWN", "begin_time": "2026/06/20", "end_time": "2026/06/25"},
                    {"idx": 6, "direction": "UP", "begin_time": "2026/06/25", "end_time": "2026/06/29"},
                ],
                "segments": [
                    {"idx": 1, "direction": "DOWN", "begin_time": "2026/06/01", "end_time": "2026/06/10"},
                    {"idx": 2, "direction": "UP", "begin_time": "2026/06/10", "end_time": "2026/06/20"},
                    {"idx": 3, "direction": "DOWN", "begin_time": "2026/06/20", "end_time": "2026/06/29"},
                    {"idx": 4, "direction": "UP", "begin_time": "2026/06/29", "end_time": "2026/07/02"},
                ],
                "zs": [
                    {"begin_time": "2026/06/01", "end_time": "2026/06/10", "low": 60.0, "high": 65.0, "is_sure": True},
                    {"begin_time": "2026/06/10", "end_time": "2026/06/20", "low": 62.0, "high": 66.0, "is_sure": True},
                    {"begin_time": "2026/06/20", "end_time": "2026/06/29", "low": 61.0, "high": 64.0, "is_sure": False},
                    {"begin_time": "2026/06/29", "end_time": "2026/07/02", "low": 63.0, "high": 67.0, "is_sure": False},
                ],
                "indicators": {
                    "crosses": {
                        "macd": [
                            {"time": "2026/06/01", "type": "dead"},
                            {"time": "2026/06/05", "type": "golden"},
                            {"time": "2026/06/10", "type": "dead"},
                            {"time": "2026/06/15", "type": "golden"},
                            {"time": "2026/06/20", "type": "dead"},
                            {"time": "2026/06/29", "type": "golden"},
                        ],
                        "kdj": [
                            {"time": "2026/06/03", "type": "dead"},
                            {"time": "2026/06/08", "type": "golden"},
                            {"time": "2026/06/12", "type": "dead"},
                            {"time": "2026/06/18", "type": "golden"},
                            {"time": "2026/06/24", "type": "dead"},
                            {"time": "2026/06/29", "type": "golden"},
                        ],
                    }
                },
            },
            "K_30M": {
                "data_range": {"start": "2026/06/20 09:30", "end": "2026/06/29 15:00"},
                "buy_sell_points": [
                    {"time": "2026/06/27 10:00", "is_buy": True, "type": "1"},
                    {"time": "2026/06/27 14:30", "is_buy": False, "type": "1"},
                    {"time": "2026/06/28 10:00", "is_buy": True, "type": "2"},
                    {"time": "2026/06/28 14:30", "is_buy": False, "type": "2"},
                    {"time": "2026/06/29 10:00", "is_buy": True, "type": "3a"},
                    {"time": "2026/06/29 14:30", "is_buy": True, "type": "1p"},
                ],
                "bi": [
                    {"idx": 1, "direction": "DOWN", "begin_time": "2026/06/27 09:30", "end_time": "2026/06/27 10:00"},
                    {"idx": 2, "direction": "UP", "begin_time": "2026/06/27 10:00", "end_time": "2026/06/27 14:30"},
                    {"idx": 3, "direction": "DOWN", "begin_time": "2026/06/27 14:30", "end_time": "2026/06/28 10:00"},
                    {"idx": 4, "direction": "UP", "begin_time": "2026/06/28 10:00", "end_time": "2026/06/28 14:30"},
                    {"idx": 5, "direction": "DOWN", "begin_time": "2026/06/28 14:30", "end_time": "2026/06/29 10:00"},
                    {"idx": 6, "direction": "UP", "begin_time": "2026/06/29 10:00", "end_time": "2026/06/29 14:30"},
                ],
                "segments": [
                    {"idx": 1, "direction": "DOWN", "begin_time": "2026/06/27 09:30", "end_time": "2026/06/28 10:00"},
                    {"idx": 2, "direction": "UP", "begin_time": "2026/06/28 10:00", "end_time": "2026/06/29 10:00"},
                    {"idx": 3, "direction": "UP", "begin_time": "2026/06/29 10:00", "end_time": "2026/06/29 14:30"},
                    {"idx": 4, "direction": "DOWN", "begin_time": "2026/06/29 14:30", "end_time": "2026/06/30 10:00"},
                ],
                "zs": [
                    {"begin_time": "2026/06/27 09:30", "end_time": "2026/06/28 10:00", "low": 60.0, "high": 61.0, "is_sure": True},
                    {"begin_time": "2026/06/28 10:00", "end_time": "2026/06/29 10:00", "low": 61.0, "high": 62.0, "is_sure": False},
                    {"begin_time": "2026/06/29 10:00", "end_time": "2026/06/29 14:30", "low": 62.0, "high": 63.0, "is_sure": False},
                ],
            },
        },
        latest_price=70.5,
    )

    assert [point["time"] for point in item["evidence"]["daily"]["recent_buy_sell_points"]] == [
        "2026/06/05",
        "2026/06/10",
        "2026/06/15",
        "2026/06/20",
        "2026/06/29",
    ]
    assert [bi["idx"] for bi in item["evidence"]["daily"]["recent_bi"]] == [2, 3, 4, 5, 6]
    assert [segment["idx"] for segment in item["evidence"]["daily"]["recent_segments"]] == [2, 3, 4]
    assert len(item["evidence"]["daily"]["recent_zs"]) == 3
    assert [cross["time"] for cross in item["evidence"]["daily"]["recent_macd_crosses"]] == [
        "2026/06/05",
        "2026/06/10",
        "2026/06/15",
        "2026/06/20",
        "2026/06/29",
    ]
    assert len(item["evidence"]["weekly"]["recent_buy_sell_points"]) == 3
    assert len(item["evidence"]["weekly"]["recent_segments"]) == 3
    assert len(item["evidence"]["weekly"]["recent_zs"]) == 2
    assert len(item["evidence"]["m30"]["recent_buy_sell_points"]) == 5
    assert len(item["evidence"]["m30"]["recent_bi"]) == 5
    assert len(item["evidence"]["m30"]["recent_segments"]) == 3
    assert len(item["evidence"]["m30"]["recent_zs"]) == 2


def test_daily_decision_keeps_m30_as_execution_reference():
    observation = build_observation(
        {"symbol": "601138", "name": "工业富联", "quantity": 0, "cost_price": None, "status": "watching"},
        {
            "K_DAY": {
                "data_range": {"start": "2026/04/01", "end": "2026/06/29"},
                "buy_sell_points": [
                    {"time": "2026/06/20", "is_buy": False, "type": "1"},
                    {"time": "2026/06/29", "is_buy": True, "type": "2s"},
                ],
                "segments": [
                    {
                        "direction": "DOWN",
                        "is_sure": False,
                        "begin_time": "2026/06/10",
                        "end_time": "2026/06/29",
                        "begin_value": 80.0,
                        "end_value": 68.0,
                    },
                ],
            },
            "K_30M": {
                "data_range": {"start": "2026/06/20 09:30", "end": "2026/06/29 15:00"},
                "buy_sell_points": [
                    {"time": "2026/06/27 14:30", "is_buy": False, "type": "1"},
                    {"time": "2026/06/29 14:30", "is_buy": True, "type": "1p"},
                ],
            },
        },
        latest_price=70.5,
    )

    assert observation["details"][:6] == [
        "详细报告：",
        "  周线背景：",
        "    数据：无",
        "    趋势：无",
        "  中长线决策：",
        "    日线结构：最新线段未确认，方向向下（2026/06/10 至 2026/06/29）",
    ]
    assert observation["details"][6:11] == [
        "    日线买点：买 2s（2026/06/29），距最新日线 0 天，当前有效",
        "    日线卖点：卖 1（2026/06/20），已被后续买 2s（2026/06/29）覆盖",
        "    30分钟执行：买 1p（2026/06/29 14:30），距最新30分钟 0 天，当前有效；30分钟买点过夜，仅作参考，次日需重看",
        "    买点标签：日线买点当前有效",
        "    卖点标签：日线卖点已被买点覆盖",
    ]


def test_daily_decision_marks_old_daily_buy_as_background():
    observation = build_observation(
        {"symbol": "600549", "name": "厦门钨业", "quantity": 200, "cost_price": 65.086, "status": "holding"},
        {
            "K_DAY": {
                "data_range": {"start": "2026/04/01", "end": "2026/06/29"},
                "buy_sell_points": [{"time": "2026/05/20", "is_buy": True, "type": "1p"}],
                "segments": [
                    {
                        "direction": "UP",
                        "is_sure": True,
                        "begin_time": "2026/05/20",
                        "end_time": "2026/06/29",
                        "begin_value": 55.0,
                        "end_value": 69.0,
                    },
                ],
            },
            "K_30M": {
                "data_range": {"start": "2026/06/20 09:30", "end": "2026/06/29 15:00"},
                "buy_sell_points": [{"time": "2026/06/29 14:30", "is_buy": True, "type": "2"}],
            },
        },
        latest_price=69.2,
    )

    assert observation["details"][6:11] == [
        "    日线买点：买 1p（2026/05/20），距最新日线 40 天，过期背景",
        "    日线卖点：无最新卖点",
        "    30分钟执行：买 2（2026/06/29 14:30），距最新30分钟 0 天，当前有效；30分钟买点过夜，仅作参考，次日需重看",
        "    买点标签：日线买点过期背景",
        "    卖点标签：日线无卖点",
    ]


def test_daily_decision_treats_daily_buy_over_twenty_days_as_old_background():
    observation = build_observation(
        {"symbol": "002837", "name": "英维克", "quantity": 300, "cost_price": 71.94, "status": "holding"},
        {
            "K_DAY": {
                "data_range": {"start": "2026/04/01", "end": "2026/06/29"},
                "buy_sell_points": [{"time": "2026/06/08", "is_buy": True, "type": "1"}],
                "segments": [
                    {
                        "direction": "UP",
                        "is_sure": False,
                        "begin_time": "2026/06/08",
                        "end_time": "2026/06/25",
                    },
                ],
            },
            "K_30M": {
                "data_range": {"start": "2026/06/20 09:30", "end": "2026/06/30 10:00"},
                "buy_sell_points": [{"time": "2026/06/29 11:00", "is_buy": True, "type": "2"}],
            },
        },
        latest_price=75.11,
    )

    assert observation["details"][6:11] == [
        "    日线买点：买 1（2026/06/08），距最新日线 21 天，过期背景",
        "    日线卖点：无最新卖点",
        "    30分钟执行：买 2（2026/06/29 11:00），距最新30分钟 1 天，当前有效；30分钟买点过夜，仅作参考，次日需重看",
        "    买点标签：日线买点过期背景",
        "    卖点标签：日线无卖点",
    ]
