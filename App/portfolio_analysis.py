LEVEL_LABELS = {
    "K_WEEK": "周线",
    "K_DAY": "日线",
    "K_30M": "30分钟",
}


def build_advice(position, levels, latest_price):
    if position["status"] == "holding":
        return _holding_advice(position, levels, latest_price)
    return _watching_advice(position, levels, latest_price)


def _holding_advice(position, levels, latest_price):
    day_sell = _latest_signal(levels, is_buy=False, level_order=("K_DAY",))
    day_buy = _latest_signal(levels, is_buy=True, level_order=("K_DAY",))
    minute_sell = _latest_signal(levels, is_buy=False, level_order=("K_30M",))
    minute_buy = _latest_signal(levels, is_buy=True, level_order=("K_30M",))
    if day_sell:
        signal = minute_sell if _confirms(day_sell, minute_sell) else day_sell
        priority = "减仓风险确认" if signal is minute_sell else "日线卖点待30分钟确认"
    elif day_buy:
        signal = minute_buy if _confirms(day_buy, minute_buy) else day_buy
        priority = "加仓候选" if signal is minute_buy else "日线买点待30分钟确认"
    elif minute_sell:
        signal = minute_sell
        priority = "30分钟卖点，等待日线确认"
    elif minute_buy:
        signal = minute_buy
        priority = "30分钟买点，等待日线确认"
    else:
        signal = None
        priority = "持有观察"

    basis = [_cost_basis(position["cost_price"], latest_price)]
    if signal:
        basis.append(_signal_basis(signal, "买点" if signal[1]["is_buy"] else "卖点"))
        _append_weekly_context(basis, levels, signal)
    else:
        basis.append("未检测到日线或30分钟买卖点")
    return {"priority": priority, "basis": "；".join(basis), "latest_price": latest_price}


def _watching_advice(position, levels, latest_price):
    day_buy = _latest_signal(levels, is_buy=True, level_order=("K_DAY",))
    minute_buy = _latest_signal(levels, is_buy=True, level_order=("K_30M",))
    if day_buy:
        signal = minute_buy if _confirms(day_buy, minute_buy) else day_buy
        priority = "重点关注" if signal is minute_buy else "日线买点待30分钟确认"
    elif minute_buy:
        signal = minute_buy
        priority = "30分钟买点，等待日线确认"
    else:
        signal = None
        priority = "暂不关注"

    basis = [_signal_basis(signal, "买点") if signal else "未检测到日线或30分钟买点"]
    if signal:
        _append_weekly_context(basis, levels, signal)
    return {"priority": priority, "basis": "；".join(basis), "latest_price": latest_price}


def _latest_signal(levels, is_buy, level_order):
    signals = []
    for level in level_order:
        points = [point for point in levels.get(level, {}).get("buy_sell_points", []) if point["is_buy"] == is_buy]
        if points:
            signals.append((level, max(points, key=lambda point: point["time"])))
    return max(signals, key=lambda signal: signal[1]["time"]) if signals else None


def _confirms(day_signal, minute_signal):
    return minute_signal is not None and minute_signal[1]["time"] >= day_signal[1]["time"]


def _append_weekly_context(basis, levels, signal):
    weekly_signal = _latest_signal(levels, is_buy=signal[1]["is_buy"], level_order=("K_WEEK",))
    if weekly_signal and weekly_signal != signal:
        label = "买点" if weekly_signal[1]["is_buy"] else "卖点"
        basis.append(f"周线背景：{_signal_basis(weekly_signal, label)}")


def _signal_basis(signal, label):
    level, point = signal
    return f"{LEVEL_LABELS[level]}{label} {point['type']}（{point['time']}）"


def _cost_basis(cost_price, latest_price):
    if latest_price is None:
        return "缓存中没有最新价格"
    if cost_price is None:
        return f"最新价 {latest_price:.3f}"
    change = (latest_price - cost_price) / cost_price * 100
    relation = "高于" if change >= 0 else "低于"
    return f"最新价 {latest_price:.3f}，{relation}成本 {abs(change):.2f}%"
