from App.analysis_export import serialize_level


class FakeTime:
    def __init__(self, value):
        self.value = value

    def to_str(self):
        return self.value


class FakeMacd:
    def __init__(self, dif, dea, macd):
        self.DIF = dif
        self.DEA = dea
        self.macd = macd


class FakeKdj:
    def __init__(self, k, d, j):
        self.k = k
        self.d = d
        self.j = j


class FakeKlu:
    def __init__(self, time, macd=None, kdj=None):
        self.time = FakeTime(time)
        self.macd = macd
        if kdj is not None:
            self.kdj = kdj


class FakeEnum:
    def __init__(self, name):
        self.name = name


class FakeBi:
    idx = 2
    dir = FakeEnum("UP")
    type = FakeEnum("STRICT")
    is_sure = True

    def get_begin_klu(self):
        return FakeKlu("2026/06/20 09:30")

    def get_end_klu(self):
        return FakeKlu("2026/06/20 10:00")

    def get_begin_val(self):
        return 10.0

    def get_end_val(self):
        return 11.0


class FakeSeg:
    idx = 1
    dir = FakeEnum("UP")
    is_sure = True
    reason = "normal"
    start_bi = FakeBi()
    end_bi = FakeBi()


class FakeZs:
    is_sure = True
    begin = FakeKlu("2026/06/20 09:30")
    end = FakeKlu("2026/06/20 10:00")
    low = 10.2
    high = 10.8
    peak_low = 10.0
    peak_high = 11.0
    begin_bi = FakeBi()
    end_bi = FakeBi()
    sub_zs_lst = []


class FakeBsp:
    klu = FakeKlu("2026/06/20 10:00")
    is_buy = True
    bi = FakeBi()
    is_segbsp = False

    def type2str(self):
        return "1,2"


class FakeBspList:
    def bsp_iter(self):
        return iter([FakeBsp()])

    def getSortedBspList(self):
        return [FakeBsp()]


class FakeLevel:
    bi_list = [FakeBi()]
    seg_list = [FakeSeg()]
    segseg_list = [FakeSeg()]
    zs_list = [FakeZs()]
    segzs_list = [FakeZs()]
    bs_point_lst = FakeBspList()
    seg_bs_point_lst = FakeBspList()

    def klu_iter(self):
        return iter([FakeKlu("2026/06/20 09:30"), FakeKlu("2026/06/20 10:00")])


def test_serializes_chan_results_without_kline_payloads():
    result = serialize_level(FakeLevel())

    assert result["data_range"] == {"start": "2026/06/20 09:30", "end": "2026/06/20 10:00"}
    assert result["bi"] == [{"idx": 2, "direction": "UP", "type": "STRICT", "is_sure": True, "begin_time": "2026/06/20 09:30", "end_time": "2026/06/20 10:00", "begin_value": 10.0, "end_value": 11.0}]
    assert result["segments"][0]["reason"] == "normal"
    assert result["zs"][0]["low"] == 10.2
    assert result["buy_sell_points"][0]["type"] == "1,2"
    assert "klines" not in result


def test_serializes_buy_sell_points_in_chronological_order():
    class OrderedBspList:
        def __init__(self):
            self.earlier = _bsp(1, "2026/06/20 09:30")
            self.later = _bsp(3, "2026/06/20 10:30")

        def bsp_iter(self):
            return iter([self.later, self.earlier])

        def getSortedBspList(self):
            return [self.earlier, self.later]

    level = FakeLevel()
    level.bs_point_lst = OrderedBspList()
    level.seg_bs_point_lst = OrderedBspList()

    result = serialize_level(level)

    assert [point["time"] for point in result["buy_sell_points"]] == ["2026/06/20 09:30", "2026/06/20 10:30"]
    assert [point["time"] for point in result["segment_buy_sell_points"]] == ["2026/06/20 09:30", "2026/06/20 10:30"]


def test_serializes_structural_collections_in_chronological_order():
    early_bi = _bi(1, "2026/06/20 09:30")
    later_bi = _bi(3, "2026/06/20 10:30")
    level = FakeLevel()
    level.bi_list = [later_bi, early_bi]
    level.seg_list = [_seg(later_bi), _seg(early_bi)]
    level.segseg_list = [_seg(later_bi), _seg(early_bi)]
    level.zs_list = [_zs("2026/06/20 10:30"), _zs("2026/06/20 09:30")]
    level.segzs_list = [_zs("2026/06/20 10:30"), _zs("2026/06/20 09:30")]

    result = serialize_level(level)

    for field in ["bi", "segments", "seg_segments", "zs", "seg_zs"]:
        assert [item["begin_time"] for item in result[field]] == ["2026/06/20 09:30", "2026/06/20 10:30"]


def test_serializes_latest_indicators_and_crosses():
    class IndicatorLevel(FakeLevel):
        def klu_iter(self):
            return iter([
                FakeKlu("2026/06/20 09:30", FakeMacd(-0.2, -0.1, -0.2), FakeKdj(30, 40, 10)),
                FakeKlu("2026/06/20 10:00", FakeMacd(0.1, -0.05, 0.3), FakeKdj(45, 42, 51)),
                FakeKlu("2026/06/20 10:30", FakeMacd(0.02, 0.08, -0.12), FakeKdj(41, 44, 35)),
            ])

    result = serialize_level(IndicatorLevel())

    assert result["indicators"]["latest"]["macd"] == {
        "time": "2026/06/20 10:30",
        "dif": 0.02,
        "dea": 0.08,
        "macd": -0.12,
    }
    assert result["indicators"]["latest"]["kdj"] == {
        "time": "2026/06/20 10:30",
        "k": 41,
        "d": 44,
        "j": 35,
    }
    assert result["indicators"]["crosses"]["macd"] == [
        {"time": "2026/06/20 10:00", "type": "golden", "dif": 0.1, "dea": -0.05, "macd": 0.3},
        {"time": "2026/06/20 10:30", "type": "dead", "dif": 0.02, "dea": 0.08, "macd": -0.12},
    ]
    assert result["indicators"]["crosses"]["kdj"] == [
        {"time": "2026/06/20 10:00", "type": "golden", "k": 45, "d": 42, "j": 51},
        {"time": "2026/06/20 10:30", "type": "dead", "k": 41, "d": 44, "j": 35},
    ]


def _bsp(idx, time):
    point = FakeBsp()
    point.klu = FakeKlu(time)
    point.bi = FakeBi()
    point.bi.idx = idx
    return point


def _bi(idx, time):
    bi = FakeBi()
    bi.idx = idx
    bi.get_begin_klu = lambda: FakeKlu(time)
    bi.get_end_klu = lambda: FakeKlu(time)
    return bi


def _seg(bi):
    segment = FakeSeg()
    segment.start_bi = bi
    segment.end_bi = bi
    return segment


def _zs(time):
    zs = FakeZs()
    zs.begin = FakeKlu(time)
    zs.end = FakeKlu(time)
    return zs
