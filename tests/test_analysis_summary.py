from types import SimpleNamespace

from App.analysis_summary import format_summary
from Common.CEnum import KL_TYPE


def test_format_summary_shows_latest_structure_for_each_level():
    level = SimpleNamespace(
        klu_iter=lambda: iter([
            SimpleNamespace(time=SimpleNamespace(to_str=lambda: "2026-06-01")),
            SimpleNamespace(time=SimpleNamespace(to_str=lambda: "2026-06-20")),
        ]),
        bi_list=[object(), object()],
        seg_list=[object()],
        zs_list=[SimpleNamespace(low=10.25, high=12.75)],
        bs_point_lst=SimpleNamespace(
            getSortedBspList=lambda: [
                SimpleNamespace(
                    is_buy=True,
                    type2str=lambda: "1,2",
                    klu=SimpleNamespace(time=SimpleNamespace(to_str=lambda: "2026-06-20")),
                )
            ]
        ),
    )

    output = format_summary("002536", "cache", {KL_TYPE.K_DAY: level})

    assert "002536 缠论分析（cache）" in output
    assert "日线" in output
    assert "数据：2026-06-01 至 2026-06-20" in output
    assert "笔：2" in output
    assert "线段：1" in output
    assert "中枢：1（10.25 - 12.75）" in output
    assert "最新买卖点：买 1,2（2026-06-20）" in output


def test_format_summary_marks_missing_structure_as_none():
    level = SimpleNamespace(
        klu_iter=lambda: iter(()),
        bi_list=[],
        seg_list=[],
        zs_list=[],
        bs_point_lst=SimpleNamespace(getSortedBspList=lambda: []),
    )

    output = format_summary("002536", "cache", {KL_TYPE.K_5M: level})

    assert "5分钟" in output
    assert "数据：无" in output
    assert "中枢：0（无）" in output
    assert "最新买卖点：无" in output


def test_format_summary_uses_latest_buy_sell_point_by_chronological_order():
    earlier = SimpleNamespace(
        is_buy=True,
        type2str=lambda: "1",
        klu=SimpleNamespace(time=SimpleNamespace(to_str=lambda: "2026-06-01")),
    )
    later = SimpleNamespace(
        is_buy=False,
        type2str=lambda: "3a",
        klu=SimpleNamespace(time=SimpleNamespace(to_str=lambda: "2026-06-20")),
    )
    level = SimpleNamespace(
        klu_iter=lambda: iter(()),
        bi_list=[],
        seg_list=[],
        zs_list=[],
        bs_point_lst=SimpleNamespace(
            bsp_iter=lambda: iter([later, earlier]),
            getSortedBspList=lambda: [earlier, later],
        ),
    )

    output = format_summary("002536", "cache", {KL_TYPE.K_5M: level})

    assert "最新买卖点：卖 3a（2026-06-20）" in output
