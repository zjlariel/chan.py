from datetime import datetime


LEVEL_LABELS = {
    "K_WEEK": "周线",
    "K_DAY": "日线",
    "K_30M": "30分钟",
}

LEVEL_ORDER = ("K_WEEK", "K_DAY", "K_30M")
CROSS_LABELS = {
    "golden": "金叉",
    "dead": "死叉",
}
TREND_LABELS = {
    "UP": "向上",
    "DOWN": "向下",
}


def build_observation(position, levels, latest_price):
    return {
        "header": _header(position, latest_price),
        "levels": [_level_observation(level, levels.get(level)) for level in LEVEL_ORDER],
        "details": _detail_lines(levels),
        "latest_price": latest_price,
    }


def build_model_input_item(position, levels, latest_price):
    return {
        "symbol": position["symbol"],
        "name": position["name"],
        "status": position["status"],
        "quantity": position.get("quantity"),
        "available_quantity": position.get("available_quantity"),
        "cost_price": position.get("cost_price"),
        "latest_price": latest_price,
        "levels": {
            "K_WEEK": _raw_level_model(levels.get("K_WEEK"), point_limit=3, bi_limit=5, segment_limit=3, zs_limit=2, cross_limit=0),
            "K_DAY": _raw_level_model(levels.get("K_DAY"), point_limit=5, bi_limit=5, segment_limit=3, zs_limit=3, cross_limit=5),
            "K_30M": _raw_level_model(levels.get("K_30M"), point_limit=5, bi_limit=5, segment_limit=3, zs_limit=2, cross_limit=0),
        },
    }


def build_model_item(position, levels, latest_price):
    day_state = _point_state(levels.get("K_DAY"), "日线", current_days=10, weak_days=20)
    day_sell_state = _sell_point_state(levels.get("K_DAY"), "日线", current_days=10, weak_days=20)
    m30_state = _point_state(levels.get("K_30M"), "30分钟", current_days=3, weak_days=5)
    daily_decision = _model_daily_decision(levels.get("K_DAY"), day_state)
    daily_sell_risk = _model_daily_sell_risk(day_sell_state)
    m30_execution = _model_m30_execution(m30_state)
    position_decision = _model_position_decision(position, daily_decision, daily_sell_risk)
    return {
        "symbol": position["symbol"],
        "name": position["name"],
        "status": position["status"],
        "quantity": position.get("quantity"),
        "available_quantity": position.get("available_quantity"),
        "cost_price": position.get("cost_price"),
        "latest_price": latest_price,
        "weekly": _model_weekly(levels.get("K_WEEK")),
        "daily": _model_decision_level(levels.get("K_DAY"), day_state),
        "m30": _model_decision_level(levels.get("K_30M"), m30_state),
        "daily_decision": daily_decision,
        "daily_sell_risk": daily_sell_risk,
        "position_decision": position_decision,
        "m30_execution": m30_execution,
        "evidence": _model_evidence(levels),
        "model_input": build_model_input_item(position, levels, latest_price),
    }


def format_portfolio_summary(items):
    lines = ["股票池分析摘要"]
    for section in _summary_sections(items):
        lines.extend(_summary_status_lines(section, _summary_sorted_items([item for item in items if item.get("section") == section])))
    lines.append("")
    lines.append("持仓/观察决策分组：")
    labels = [
        "持仓风控：日线卖点当前有效",
        "持仓风控：日线卖点转弱观察",
        "持仓风控：日线卖点过期背景",
        "持仓观察：暂无日线卖点",
        "日线买点当前有效",
        "日线买点转弱观察",
        "日线买点过期背景",
        "日线买点已被卖点覆盖",
        "无日线买点",
        "日线数据不足",
    ]
    for label in labels:
        grouped = _summary_sorted_items([item for item in items if item["position_decision"]["label"] == label])
        if not grouped:
            continue
        lines.append(f"  {label}：")
        for item in grouped:
            lines.append(f"    - {_summary_item_text(item)}")
    return "\n".join(lines) + "\n"


def _header(position, latest_price):
    status = "持仓" if position["status"] == "holding" else "观察"
    parts = [f"{position['name']} ({position['symbol']})：{status}"]
    price = _price_text(position.get("cost_price"), latest_price)
    if price:
        parts.append(price)
    return "，".join(parts)


def _model_weekly(data):
    data_range = (data or {}).get("data_range") or {}
    return {
        "data_range": data_range,
        "trend": _trend_text(data) if data else "无",
    }


def _raw_level_model(data, point_limit, bi_limit, segment_limit, zs_limit, cross_limit):
    data = data or {}
    indicators = data.get("indicators") or {}
    crosses = indicators.get("crosses") or {}
    latest_indicators = indicators.get("latest") or {}
    recent = {
        "buy_sell_points": _recent_items(data.get("buy_sell_points") or [], point_limit),
        "bi": _recent_items(data.get("bi") or [], bi_limit),
        "segments": _recent_items(data.get("segments") or [], segment_limit),
        "zs": _recent_items(data.get("zs") or [], zs_limit),
    }
    if cross_limit:
        recent["macd_crosses"] = _recent_items(crosses.get("macd") or [], cross_limit)
        recent["kdj_crosses"] = _recent_items(crosses.get("kdj") or [], cross_limit)
    return {
        "data_range": data.get("data_range") or {},
        "latest": {
            "buy_sell_point": _latest_point(data.get("buy_sell_points") or []),
            "bi": _latest_structure(data.get("bi") or []),
            "segment": _latest_structure(data.get("segments") or []),
            "zs": _latest_structure(data.get("zs") or []),
            "indicators": {
                "macd": latest_indicators.get("macd"),
                "kdj": latest_indicators.get("kdj"),
                "ma": latest_indicators.get("ma"),
                "boll": latest_indicators.get("boll"),
                "rsi": latest_indicators.get("rsi"),
                "volume": latest_indicators.get("volume"),
            },
        },
        "recent": recent,
    }


def _model_decision_level(data, point_state):
    if not data:
        return {
            "data_range": {},
            "structure": "无数据",
            "latest_point": None,
            "buy_freshness": _model_point_state(point_state),
            "indicators": _model_indicators({}),
        }
    latest_point = _latest_point(data.get("buy_sell_points") or [])
    return {
        "data_range": data.get("data_range") or {},
        "structure": _daily_construction_text(data),
        "latest_point": _model_point(latest_point),
        "buy_freshness": _model_point_state(point_state),
        "indicators": _model_indicators(data.get("indicators") or {}),
    }


def _model_indicators(indicators):
    latest = indicators.get("latest") or {}
    crosses = indicators.get("crosses") or {}
    return {
        "macd": latest.get("macd"),
        "macd_text": _macd_text(latest.get("macd")),
        "latest_macd_cross": _model_cross(_latest_point(crosses.get("macd") or [])),
        "kdj": latest.get("kdj"),
        "kdj_text": _kdj_text(latest.get("kdj")),
        "latest_kdj_cross": _model_cross(_latest_point(crosses.get("kdj") or [])),
        "ma": latest.get("ma"),
        "ma_text": _ma_text(latest.get("ma")),
        "boll": latest.get("boll"),
        "boll_text": _boll_text(latest.get("boll")),
        "rsi": latest.get("rsi"),
        "rsi_text": _rsi_text(latest.get("rsi")),
        "volume": latest.get("volume"),
        "volume_text": _volume_text(latest.get("volume")),
    }


def _model_point(point):
    if point is None:
        return None
    return {
        "direction": "buy" if point["is_buy"] else "sell",
        "type": point["type"],
        "time": point["time"],
        "text": _point_text(point),
    }


def _model_cross(cross):
    if cross is None:
        return None
    return {
        "type": cross["type"],
        "time": cross["time"],
        "text": f"{CROSS_LABELS[cross['type']]}（{cross['time']}）",
    }


def _model_point_state(state):
    return {
        "status": state.get("status"),
        "freshness": state.get("freshness"),
        "age_days": state.get("age_days"),
        "point": _model_point(state.get("point")),
        "latest_point": _model_point(state.get("latest_point")),
        "text": _point_state_text(state),
    }


def _model_daily_decision(data, day_state):
    return {
        "structure": _daily_construction_text(data),
        "buy": _model_point_state(day_state),
        "label": _daily_decision_label(day_state),
    }


def _model_daily_sell_risk(day_sell_state):
    return {
        "sell": _model_point_state(day_sell_state),
        "label": _daily_sell_risk_label(day_sell_state),
    }


def _model_position_decision(position, daily_decision, daily_sell_risk):
    if position["status"] == "holding":
        sell_label = daily_sell_risk["label"]
        if sell_label in {"日线无卖点", "日线卖点已被买点覆盖"}:
            return {"focus": "sell", "label": "持仓观察：暂无日线卖点"}
        return {"focus": "sell", "label": f"持仓风控：{sell_label}"}
    return {"focus": "buy", "label": daily_decision["label"]}


def _model_evidence(levels):
    return {
        "weekly": _level_evidence(
            levels.get("K_WEEK"),
            point_limit=3,
            bi_limit=0,
            segment_limit=3,
            zs_limit=2,
            cross_limit=0,
        ),
        "daily": _level_evidence(
            levels.get("K_DAY"),
            point_limit=5,
            bi_limit=5,
            segment_limit=3,
            zs_limit=3,
            cross_limit=5,
        ),
        "m30": _level_evidence(
            levels.get("K_30M"),
            point_limit=5,
            bi_limit=5,
            segment_limit=3,
            zs_limit=2,
            cross_limit=0,
        ),
    }


def _level_evidence(data, point_limit, bi_limit, segment_limit, zs_limit, cross_limit):
    data = data or {}
    indicators = data.get("indicators") or {}
    crosses = indicators.get("crosses") or {}
    evidence = {
        "recent_buy_sell_points": _recent_items(data.get("buy_sell_points") or [], point_limit),
        "recent_bi": _recent_items(data.get("bi") or [], bi_limit),
        "recent_segments": _recent_items(data.get("segments") or [], segment_limit),
        "recent_zs": _recent_items(data.get("zs") or [], zs_limit),
    }
    if cross_limit:
        evidence["recent_macd_crosses"] = _recent_items(crosses.get("macd") or [], cross_limit)
        evidence["recent_kdj_crosses"] = _recent_items(crosses.get("kdj") or [], cross_limit)
    return evidence


def _model_m30_execution(m30_state):
    return {
        "state": _model_point_state(m30_state),
        "hint": _m30_execution_hint(m30_state),
        "text": _m30_execution_text(m30_state),
    }


def _summary_status_lines(title, items):
    lines = ["", f"{title}："]
    if not items:
        lines.append("  无")
        return lines
    for item in items:
        lines.append(f"  - {_summary_item_text(item)}")
    return lines


def _summary_sorted_items(items):
    return sorted(items, key=_summary_sort_key)


def _summary_sort_key(item):
    buy = ((item.get("daily_decision") or {}).get("buy") or {})
    status_order = {
        "buy": 0,
        "invalidated": 1,
        "no_buy": 2,
        "no_data": 3,
    }
    freshness_order = {
        "current": 0,
        "weak": 1,
        "old": 2,
        "unknown": 3,
        None: 4,
    }
    age_days = buy.get("age_days")
    if age_days is None:
        age_days = 999999
    point = buy.get("point") or {}
    return (
        status_order.get(buy.get("status"), 4),
        freshness_order.get(buy.get("freshness"), 4),
        age_days,
        point.get("time") or "",
        item.get("symbol") or "",
    )


def _summary_sections(items):
    sections = []
    for fallback in ("持仓股", "观察股", "临时观察股"):
        if any(item.get("section") == fallback for item in items):
            sections.append(fallback)
    for item in items:
        section = item.get("section")
        if section and section not in sections:
            sections.append(section)
    return sections


def _summary_item_text(item):
    price = "无" if item.get("latest_price") is None else f"{item['latest_price']:.3f}"
    return (
        f"{item['name']}({item['symbol']}) 最新价 {price}；"
        f"{item['position_decision']['label']}；"
        f"日线 {item['daily_decision']['buy']['text']}；"
        f"卖点 {item['daily_sell_risk']['sell']['text']}；"
        f"30分钟执行 {item['m30_execution']['hint']}"
    )


def _price_text(cost_price, latest_price):
    if latest_price is None:
        return "缓存中没有最新价格"
    if cost_price is None:
        return f"最新价 {latest_price:.3f}"
    change = (latest_price - cost_price) / cost_price * 100
    relation = "高于" if change >= 0 else "低于"
    return f"最新价 {latest_price:.3f}，{relation}成本 {abs(change):.2f}%"


def _level_observation(level, data):
    label = LEVEL_LABELS[level]
    if not data:
        return f"{label}：无数据"

    data_range = data.get("data_range") or {}
    start = data_range.get("start")
    end = data_range.get("end")
    if not start and not end:
        return f"{label}：无数据"
    if level == "K_WEEK":
        return _weekly_background(start, end, data)

    indicators = data.get("indicators") or {}
    latest = indicators.get("latest") or {}
    crosses = indicators.get("crosses") or {}
    parts = [
        f"数据 {_range_text(start, end)}",
        f"最新买卖点 {_latest_buy_sell_point(data.get('buy_sell_points') or [])}",
        f"MACD {_macd_text(latest.get('macd'))}",
        f"MACD交叉 {_cross_text(crosses.get('macd') or [])}",
        f"KDJ {_kdj_text(latest.get('kdj'))}",
        f"KDJ交叉 {_cross_text(crosses.get('kdj') or [])}",
    ]
    return f"{label}：" + "；".join(parts)


def _range_text(start, end):
    if start and end:
        return f"{start} 至 {end}"
    return start or end or "无"


def _weekly_background(start, end, data):
    return "；".join([
        f"周线背景：数据 {_range_text(start, end)}",
        f"趋势 {_trend_text(data)}",
    ])


def _trend_text(data):
    latest_segment = _latest_structure(data.get("segments") or [])
    if latest_segment:
        return _structure_trend_text("线段", latest_segment)
    latest_bi = _latest_structure(data.get("bi") or [])
    if latest_bi:
        return _structure_trend_text("笔", latest_bi)
    return "无"


def _latest_structure(items):
    if not items:
        return None
    return max(items, key=lambda item: item.get("end_time") or item.get("begin_time") or "")


def _recent_items(items, limit):
    if limit <= 0 or not items:
        return []
    return sorted(items, key=_item_sort_time)[-limit:]


def _item_sort_time(item):
    return item.get("time") or item.get("end_time") or item.get("begin_time") or ""


def _structure_trend_text(name, item):
    direction = TREND_LABELS.get(item.get("direction"), item.get("direction", "未知"))
    begin = item.get("begin_time")
    end = item.get("end_time")
    time_text = f"（{_range_text(begin, end)}）" if begin or end else ""
    return f"{name}{direction}{time_text}"


def _latest_buy_sell_point(points):
    if not points:
        return "无"
    point = max(points, key=lambda item: item["time"])
    direction = "买" if point["is_buy"] else "卖"
    return f"{direction} {point['type']}（{point['time']}）"


def _macd_text(macd):
    if macd is None:
        return "无"
    return f"DIF {macd['dif']:.3f} / DEA {macd['dea']:.3f} / 柱 {macd['macd']:.3f}（{macd['time']}）"


def _kdj_text(kdj):
    if kdj is None:
        return "无"
    return f"K {kdj['k']:.2f} / D {kdj['d']:.2f} / J {kdj['j']:.2f}（{kdj['time']}）"


def _cross_text(crosses):
    if not crosses:
        return "无"
    cross = max(crosses, key=lambda item: item["time"])
    return f"{CROSS_LABELS[cross['type']]}（{cross['time']}）"


def _detail_lines(levels, limit=5):
    lines = ["详细报告："]
    weekly = levels.get("K_WEEK")
    lines.extend(_weekly_detail_lines(weekly))
    lines.extend(_decision_execution_lines(levels.get("K_DAY"), levels.get("K_30M")))
    for level in ("K_DAY", "K_30M"):
        lines.extend(_decision_level_detail_lines(level, levels.get(level), limit))
    return lines


def _weekly_detail_lines(data):
    lines = ["  周线背景："]
    if not data:
        lines.append("    数据：无")
        lines.append("    趋势：无")
        return lines
    data_range = data.get("data_range") or {}
    lines.append(f"    数据：{_range_text(data_range.get('start'), data_range.get('end'))}")
    lines.append(f"    趋势：{_trend_text(data)}")
    return lines


def _decision_level_detail_lines(level, data, limit):
    label = LEVEL_LABELS[level]
    lines = [f"  {label}："]
    if not data:
        lines.append("    数据：无")
        lines.append("    最新指标：MACD 无；KDJ 无")
        lines.append("    最近买卖点：无")
        lines.append("    最近 MACD 交叉：无")
        lines.append("    最近 KDJ 交叉：无")
        lines.append("    结构：无")
        return lines

    data_range = data.get("data_range") or {}
    indicators = data.get("indicators") or {}
    latest = indicators.get("latest") or {}
    crosses = indicators.get("crosses") or {}
    lines.append(f"    数据：{_range_text(data_range.get('start'), data_range.get('end'))}")
    lines.append(f"    最新指标：MACD {_macd_text(latest.get('macd'))}；KDJ {_kdj_text(latest.get('kdj'))}")
    lines.append(f"    趋势过滤：{_ma_text(latest.get('ma'))}")
    lines.append(f"    动量确认：MACD {_macd_text(latest.get('macd'))}；KDJ {_kdj_text(latest.get('kdj'))}；RSI14 {_rsi_text(latest.get('rsi'))}")
    lines.append(f"    波动位置：{_boll_text(latest.get('boll'))}")
    lines.append(f"    量能确认：{_volume_text(latest.get('volume'))}")
    lines.extend(_list_detail_lines("最近买卖点", _recent_buy_sell_points(data.get("buy_sell_points") or [], limit)))
    lines.extend(_list_detail_lines("最近 MACD 交叉", _recent_crosses(crosses.get("macd") or [], limit)))
    lines.extend(_list_detail_lines("最近 KDJ 交叉", _recent_crosses(crosses.get("kdj") or [], limit)))
    lines.extend(_structure_detail_lines(data))
    return lines


def _list_detail_lines(title, items):
    if not items:
        return [f"    {title}：无"]
    return [f"    {title}：", *[f"      - {item}" for item in items]]


def _recent_buy_sell_points(points, limit):
    recent = sorted(points, key=lambda item: item["time"])[-limit:]
    return [
        f"{'买' if point['is_buy'] else '卖'} {point['type']}（{point['time']}）"
        for point in recent
    ]


def _recent_crosses(crosses, limit):
    recent = sorted(crosses, key=lambda item: item["time"])[-limit:]
    return [f"{CROSS_LABELS[cross['type']]}（{cross['time']}）" for cross in recent]


def _structure_detail_lines(data):
    items = []
    latest_bi = _latest_structure(data.get("bi") or [])
    if latest_bi:
        items.append(f"      最新笔：{_structure_detail_text(latest_bi)}")
    latest_segment = _latest_structure(data.get("segments") or [])
    if latest_segment:
        items.append(f"      最新线段：{_structure_detail_text(latest_segment)}")
    latest_zs = _latest_structure(data.get("zs") or [])
    if latest_zs:
        items.append(f"      最新中枢：{_zs_detail_text(latest_zs)}")
    if not items:
        return ["    结构：无"]
    return ["    结构：", *items]


def _decision_execution_lines(day_data, m30_data):
    lines = ["  中长线决策："]
    lines.append(f"    日线结构：{_daily_construction_text(day_data)}")
    day_state = _point_state(day_data, "日线", current_days=10, weak_days=20)
    day_sell_state = _sell_point_state(day_data, "日线", current_days=10, weak_days=20)
    m30_state = _point_state(m30_data, "30分钟", current_days=3, weak_days=5)
    lines.append(f"    日线买点：{_point_state_text(day_state)}")
    lines.append(f"    日线卖点：{_point_state_text(day_sell_state)}")
    lines.append(f"    30分钟执行：{_m30_execution_text(m30_state)}")
    lines.append(f"    买点标签：{_daily_decision_label(day_state)}")
    lines.append(f"    卖点标签：{_daily_sell_risk_label(day_sell_state)}")
    return lines


def _daily_construction_text(data):
    if not data:
        return "无数据"
    structure = _latest_structure(data.get("segments") or [])
    name = "线段"
    if not structure:
        structure = _latest_structure(data.get("bi") or [])
        name = "笔"
    if not structure:
        return "无结构"
    sure_text = "已确认" if structure.get("is_sure", True) else "未确认"
    direction = TREND_LABELS.get(structure.get("direction"), structure.get("direction", "未知"))
    begin = structure.get("begin_time")
    end = structure.get("end_time")
    time_text = f"（{_range_text(begin, end)}）" if begin or end else ""
    return f"最新{name}{sure_text}，方向{direction}{time_text}"


def _point_state(data, level_name, current_days, weak_days):
    return _directional_point_state(data, level_name, current_days, weak_days, is_buy=True)


def _sell_point_state(data, level_name, current_days, weak_days):
    return _directional_point_state(data, level_name, current_days, weak_days, is_buy=False)


def _directional_point_state(data, level_name, current_days, weak_days, is_buy):
    if not data:
        return {"status": "no_data", "level": level_name}

    points = data.get("buy_sell_points") or []
    latest_point = _latest_point(points)
    latest_selected = _latest_point([point for point in points if point.get("is_buy") is is_buy])
    end_time = (data.get("data_range") or {}).get("end")
    age_days = _days_between(latest_selected.get("time") if latest_selected else None, end_time)

    if latest_selected is None:
        return {"status": "no_buy" if is_buy else "no_sell", "level": level_name, "latest_point": latest_point}
    if latest_point and latest_point.get("is_buy") is not is_buy and latest_point.get("time") > latest_selected.get("time"):
        return {
            "status": "invalidated",
            "level": level_name,
            "point": latest_selected,
            "latest_point": latest_point,
            "age_days": age_days,
        }
    if age_days is None:
        freshness = "unknown"
    elif age_days <= current_days:
        freshness = "current"
    elif age_days <= weak_days:
        freshness = "weak"
    else:
        freshness = "old"
    return {
        "status": "buy",
        "level": level_name,
        "point": latest_selected,
        "latest_point": latest_point,
        "age_days": age_days,
        "freshness": freshness,
    }


def _latest_point(points):
    if not points:
        return None
    return max(points, key=lambda item: item["time"])


def _point_state_text(state):
    status = state.get("status")
    if status == "no_data":
        return "无数据"
    if status == "no_buy":
        return "无最新买点"
    if status == "no_sell":
        return "无最新卖点"
    if status == "invalidated":
        point = state["point"]
        latest = state["latest_point"]
        return (
            f"{'买' if point['is_buy'] else '卖'} {point['type']}（{point['time']}），已被后续"
            f"{'买' if latest['is_buy'] else '卖'} {latest['type']}（{latest['time']}）覆盖"
        )
    if status != "buy":
        return "无"
    return f"{_point_text(state['point'])}，距最新{state['level']} {_age_text(state.get('age_days'))}，{_freshness_text(state.get('freshness'))}"


def _daily_decision_label(day_state):
    status = day_state.get("status")
    if status == "no_data":
        return "日线数据不足"
    if status == "no_buy":
        return "无日线买点"
    if status == "invalidated":
        return "日线买点已被卖点覆盖"
    if status != "buy":
        return "日线数据不足"
    freshness = day_state.get("freshness")
    if freshness == "current":
        return "日线买点当前有效"
    if freshness == "weak":
        return "日线买点转弱观察"
    if freshness == "old":
        return "日线买点过期背景"
    return "日线买点时间未知"


def _daily_sell_risk_label(day_sell_state):
    status = day_sell_state.get("status")
    if status == "no_data":
        return "日线数据不足"
    if status == "no_sell":
        return "日线无卖点"
    if status == "invalidated":
        return "日线卖点已被买点覆盖"
    if status != "buy":
        return "日线数据不足"
    freshness = day_sell_state.get("freshness")
    if freshness == "current":
        return "日线卖点当前有效"
    if freshness == "weak":
        return "日线卖点转弱观察"
    if freshness == "old":
        return "日线卖点过期背景"
    return "日线卖点时间未知"


def _m30_execution_text(state):
    base = _point_state_text(state)
    return f"{base}；{_m30_execution_hint(state)}"


def _m30_execution_hint(state):
    status = state.get("status")
    latest_point = state.get("latest_point")
    if status == "no_data":
        return "30分钟无数据，次日按日线计划观察"
    if status == "invalidated":
        return "30分钟买点已被卖点覆盖，避免追高"
    if status == "no_buy":
        if latest_point and not latest_point.get("is_buy"):
            return "30分钟回落中，可等回踩低吸"
        return "30分钟尚未转强，适合观察挂低"
    if status != "buy":
        return "30分钟状态未知，次日需重看"
    freshness = state.get("freshness")
    if freshness == "current":
        return "30分钟买点过夜，仅作参考，次日需重看"
    if freshness == "weak":
        return "30分钟已反弹，避免追高"
    if freshness == "old":
        return "30分钟买点已过期，次日需重看"
    return "30分钟状态未知，次日需重看"


def _point_text(point):
    direction = "买" if point["is_buy"] else "卖"
    return f"{direction} {point['type']}（{point['time']}）"


def _age_text(age_days):
    return "未知" if age_days is None else f"{age_days} 天"


def _freshness_text(freshness):
    return {
        "current": "当前有效",
        "weak": "弱关联",
        "old": "过期背景",
        "unknown": "时间未知",
    }.get(freshness, "未知")


def _days_between(start, end):
    start_date = _parse_date(start)
    end_date = _parse_date(end)
    if start_date is None or end_date is None:
        return None
    return max((end_date - start_date).days, 0)


def _parse_date(value):
    if not value:
        return None
    normalized = value.split()[0]
    for fmt in ("%Y/%m/%d", "%Y-%m-%d"):
        try:
            return datetime.strptime(normalized, fmt).date()
        except ValueError:
            continue
    return None


def _structure_detail_text(item):
    direction = TREND_LABELS.get(item.get("direction"), item.get("direction", "未知"))
    begin = item.get("begin_time")
    end = item.get("end_time")
    value_text = _value_range_text(item.get("begin_value"), item.get("end_value"))
    return f"{direction}（{_range_text(begin, end)}{value_text}）"


def _value_range_text(begin_value, end_value):
    if begin_value is None or end_value is None:
        return ""
    return f"，{begin_value:.3f} -> {end_value:.3f}"


def _zs_detail_text(zs):
    sure_text = "已确认" if zs.get("is_sure") else "未确认"
    return (
        f"{_range_text(zs.get('begin_time'), zs.get('end_time'))}，"
        f"区间 {zs['low']:.3f} - {zs['high']:.3f}，{sure_text}"
    )


def _ma_text(ma):
    if ma is None:
        return "无"
    items = [
        f"MA5 {_optional_float(ma.get('ma5'))}",
        f"MA10 {_optional_float(ma.get('ma10'))}",
        f"MA20 {_optional_float(ma.get('ma20'))}",
        f"MA60 {_optional_float(ma.get('ma60'))}",
    ]
    return f"{' / '.join(items)}（{ma['time']}），{_ma20_position_text(ma)}"


def _ma20_position_text(ma):
    ma5 = ma.get("ma5")
    ma20 = ma.get("ma20")
    if ma5 is None or ma20 is None:
        return "MA20 位置无"
    return "价格位于 MA20 上方" if ma5 >= ma20 else "价格位于 MA20 下方"


def _rsi_text(rsi):
    if rsi is None:
        return "无"
    return f"{rsi['rsi']:.2f}（{rsi['time']}）"


def _boll_text(boll):
    if boll is None:
        return "无"
    return (
        f"BOLL MID {boll['mid']:.3f} / UP {boll['up']:.3f} / DOWN {boll['down']:.3f}（{boll['time']}），"
        f"{_boll_position_text(boll.get('position'))}，带宽 {_percent_text(boll.get('band_width'))}"
    )


def _boll_position_text(position):
    return {
        "above_up": "上轨上方",
        "upper_half": "上半区",
        "lower_half": "下半区",
        "below_down": "下轨下方",
    }.get(position, "位置未知")


def _volume_text(volume):
    if volume is None:
        return "无"
    return (
        f"成交量 {_optional_plain(volume.get('volume'))}，"
        f"较5周期均量 {_ratio_text(volume.get('volume_ratio_ma5'))} 倍，"
        f"较20周期均量 {_ratio_text(volume.get('volume_ratio_ma20'))} 倍（{volume['time']}）"
    )


def _optional_float(value):
    return "无" if value is None else f"{value:.3f}"


def _optional_plain(value):
    if value is None:
        return "无"
    return str(int(value)) if float(value).is_integer() else f"{value:.3f}"


def _ratio_text(value):
    return "无" if value is None else f"{value:.2f}"


def _percent_text(value):
    return "无" if value is None else f"{value * 100:.2f}%"
