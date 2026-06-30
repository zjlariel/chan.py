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
    lines.extend(_level_linkage_lines(levels.get("K_DAY"), levels.get("K_30M")))
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


def _level_linkage_lines(day_data, m30_data):
    lines = ["  级别联动："]
    lines.append(f"    日线结构：{_daily_construction_text(day_data)}")
    day_state = _point_state(day_data, "日线", current_days=10, weak_days=20)
    m30_state = _point_state(m30_data, "30分钟", current_days=3, weak_days=5)
    lines.append(f"    日线买点新鲜度：{_point_state_text(day_state)}")
    lines.append(f"    30分钟确认：{_m30_confirmation_text(m30_state)}")
    lines.append(f"    联动标签：{_linkage_label(day_state, m30_state)}")
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
    if not data:
        return {"status": "no_data", "level": level_name}

    points = data.get("buy_sell_points") or []
    latest_point = _latest_point(points)
    latest_buy = _latest_point([point for point in points if point.get("is_buy")])
    end_time = (data.get("data_range") or {}).get("end")
    age_days = _days_between(latest_buy.get("time") if latest_buy else None, end_time)

    if latest_buy is None:
        return {"status": "no_buy", "level": level_name, "latest_point": latest_point}
    if latest_point and not latest_point.get("is_buy") and latest_point.get("time") > latest_buy.get("time"):
        return {
            "status": "invalidated",
            "level": level_name,
            "point": latest_buy,
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
        "point": latest_buy,
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
    if status == "invalidated":
        point = state["point"]
        latest = state["latest_point"]
        return (
            f"买 {point['type']}（{point['time']}），已被后续"
            f"{'买' if latest['is_buy'] else '卖'} {latest['type']}（{latest['time']}）覆盖"
        )
    if status != "buy":
        return "无"
    return f"{_point_text(state['point'])}，距最新{state['level']} {_age_text(state.get('age_days'))}，{_freshness_text(state.get('freshness'))}"


def _m30_confirmation_text(state):
    if state.get("status") != "buy":
        return _point_state_text(state)
    return f"{_point_text(state['point'])}，距最新{state['level']} {_age_text(state.get('age_days'))}，{_freshness_text(state.get('freshness'))}"


def _linkage_label(day_state, m30_state):
    day_status = day_state.get("status")
    m30_is_current_buy = m30_state.get("status") == "buy" and m30_state.get("freshness") == "current"
    if day_status == "buy" and day_state.get("freshness") == "current" and m30_is_current_buy:
        return "当前区间套候选"
    if day_status == "buy" and day_state.get("freshness") == "current":
        return "日线新买点待30分钟确认"
    if day_status == "buy" and day_state.get("freshness") == "weak" and m30_is_current_buy:
        return "弱区间套观察"
    if day_status == "buy" and day_state.get("freshness") == "old" and m30_is_current_buy:
        return "旧日线买点背景，小级别反弹"
    if day_status == "invalidated" and m30_is_current_buy:
        return "日线卖点后小级别反弹"
    return "仅客观观察，未形成级别联动"


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
