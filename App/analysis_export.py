from datetime import datetime


def serialize_level(kl_list):
    klus = list(kl_list.klu_iter())
    return {
        "data_range": {
            "start": _time(klus[0]) if klus else None,
            "end": _time(klus[-1]) if klus else None,
        },
        "bi": [_serialize_bi(bi) for bi in _sort_by_begin_time(kl_list.bi_list, lambda bi: bi.get_begin_klu())],
        "segments": [_serialize_segment(segment) for segment in _sort_by_begin_time(kl_list.seg_list, lambda segment: segment.start_bi.get_begin_klu())],
        "seg_segments": [_serialize_segment(segment) for segment in _sort_by_begin_time(kl_list.segseg_list, lambda segment: segment.start_bi.get_begin_klu())],
        "zs": [_serialize_zs(zs) for zs in _sort_by_begin_time(kl_list.zs_list, lambda zs: zs.begin)],
        "seg_zs": [_serialize_zs(zs) for zs in _sort_by_begin_time(kl_list.segzs_list, lambda zs: zs.begin)],
        "buy_sell_points": [_serialize_bsp(bsp) for bsp in kl_list.bs_point_lst.getSortedBspList()],
        "segment_buy_sell_points": [_serialize_bsp(bsp) for bsp in kl_list.seg_bs_point_lst.getSortedBspList()],
    }


def build_document(code, source, levels):
    return {
        "code": code,
        "data_source": source,
        "generated_at": datetime.now().astimezone().isoformat(),
        "levels": {level.name: serialize_level(kl_list) for level, kl_list in levels.items()},
    }


def _serialize_bi(bi):
    return {
        "idx": bi.idx,
        "direction": bi.dir.name,
        "type": bi.type.name,
        "is_sure": bi.is_sure,
        "begin_time": _time(bi.get_begin_klu()),
        "end_time": _time(bi.get_end_klu()),
        "begin_value": bi.get_begin_val(),
        "end_value": bi.get_end_val(),
    }


def _serialize_segment(segment):
    return {
        "idx": segment.idx,
        "direction": segment.dir.name,
        "is_sure": segment.is_sure,
        "reason": segment.reason,
        "start_bi_idx": segment.start_bi.idx,
        "end_bi_idx": segment.end_bi.idx,
        "begin_time": _time(segment.start_bi.get_begin_klu()),
        "end_time": _time(segment.end_bi.get_end_klu()),
        "begin_value": segment.start_bi.get_begin_val(),
        "end_value": segment.end_bi.get_end_val(),
    }


def _serialize_zs(zs):
    return {
        "is_sure": zs.is_sure,
        "begin_time": _time(zs.begin),
        "end_time": _time(zs.end),
        "low": zs.low,
        "high": zs.high,
        "peak_low": zs.peak_low,
        "peak_high": zs.peak_high,
        "begin_bi_idx": zs.begin_bi.idx,
        "end_bi_idx": zs.end_bi.idx,
        "sub_zs": [_serialize_zs(sub_zs) for sub_zs in zs.sub_zs_lst],
    }


def _serialize_bsp(bsp):
    return {
        "time": _time(bsp.klu),
        "is_buy": bsp.is_buy,
        "type": bsp.type2str(),
        "bi_idx": bsp.bi.idx,
        "is_segment_point": bsp.is_segbsp,
    }


def _time(klu):
    return klu.time.to_str()


def _sort_by_begin_time(items, get_begin_klu):
    return sorted(items, key=lambda item: _time(get_begin_klu(item)))
