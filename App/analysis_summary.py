LEVEL_LABELS = {
    "K_WEEK": "周线",
    "K_DAY": "日线",
    "K_60M": "60分钟",
    "K_30M": "30分钟",
    "K_15M": "15分钟",
    "K_5M": "5分钟",
    "K_1M": "1分钟",
}


def format_summary(code, source, levels):
    lines = [f"{code} 缠论分析（{source}）"]
    for level_type, kl_list in levels.items():
        lines.append(_format_level(LEVEL_LABELS.get(level_type.name, level_type.name), kl_list))
    return "\n".join(lines)


def _format_level(label, kl_list):
    klus = list(kl_list.klu_iter())
    data_range = "无" if not klus else f"{_time(klus[0])} 至 {_time(klus[-1])}"
    zs_list = kl_list.zs_list
    latest_zs = "无" if not zs_list else f"{zs_list[-1].low} - {zs_list[-1].high}"
    points = kl_list.bs_point_lst.getSortedBspList()
    latest_point = "无" if not points else _format_point(points[-1])
    return (
        f"{label}：数据：{data_range}；笔：{len(kl_list.bi_list)}；线段：{len(kl_list.seg_list)}；"
        f"中枢：{len(zs_list)}（{latest_zs}）；最新买卖点：{latest_point}"
    )


def _format_point(point):
    direction = "买" if point.is_buy else "卖"
    return f"{direction} {point.type2str()}（{_time(point.klu)}）"


def _time(klu):
    return klu.time.to_str()
