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


def _header(position, latest_price):
    status = "持仓" if position["status"] == "holding" else "观察"
    parts = [f"{position['name']} ({position['symbol']})：{status}"]
    price = _price_text(position.get("cost_price"), latest_price)
    if price:
        parts.append(price)
    return "，".join(parts)


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
