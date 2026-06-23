LEVEL_LABELS = {
    "K_WEEK": "周线",
    "K_DAY": "日线",
    "K_30M": "30分钟",
    "K_5M": "5分钟",
}


def build_advice(position, levels, latest_price):
    if position["status"] == "holding":
        return _holding_advice(position, levels, latest_price)
    return _watching_advice(position, levels, latest_price)


def _holding_advice(position, levels, latest_price):
    sell_signal = _latest_signal(levels, is_buy=False, level_order=("K_WEEK", "K_DAY", "K_30M", "K_5M"))
    higher_sell_signal = _latest_signal(levels, is_buy=False, level_order=("K_WEEK", "K_DAY"))
    if sell_signal and sell_signal[0] in {"K_WEEK", "K_DAY"}:
        priority = "风险提示"
    elif sell_signal:
        priority = "留意卖点"
    else:
        priority = "持有观察"

    basis = [_cost_basis(position["cost_price"], latest_price)]
    if sell_signal:
        basis.append(_signal_basis(sell_signal, "卖点"))
        if higher_sell_signal and higher_sell_signal != sell_signal:
            basis.append(f"高周期背景：{_signal_basis(higher_sell_signal, '卖点')}")
    else:
        basis.append("未检测到已导出级别的最新卖点")
    return {"priority": priority, "basis": "；".join(basis), "latest_price": latest_price}


def _watching_advice(position, levels, latest_price):
    buy_signal = _latest_signal(levels, is_buy=True, level_order=("K_WEEK", "K_DAY", "K_30M", "K_5M"))
    higher_buy_signal = _latest_signal(levels, is_buy=True, level_order=("K_WEEK", "K_DAY"))
    if buy_signal and buy_signal[0] in {"K_WEEK", "K_DAY", "K_30M"}:
        priority = "重点关注"
    elif buy_signal:
        priority = "持续观察"
    else:
        priority = "暂不关注"

    basis = [_signal_basis(buy_signal, "买点") if buy_signal else "未检测到已导出级别的最新买点"]
    if buy_signal and higher_buy_signal and higher_buy_signal != buy_signal:
        basis.append(f"高周期背景：{_signal_basis(higher_buy_signal, '买点')}")
    return {"priority": priority, "basis": "；".join(basis), "latest_price": latest_price}


def _latest_signal(levels, is_buy, level_order):
    signals = []
    for level in level_order:
        points = [point for point in levels.get(level, {}).get("buy_sell_points", []) if point["is_buy"] == is_buy]
        if points:
            signals.append((level, max(points, key=lambda point: point["time"])))
    return max(signals, key=lambda signal: signal[1]["time"]) if signals else None


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
