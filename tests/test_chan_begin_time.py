from Chan import CChan
from Common.CEnum import AUTYPE, KL_TYPE


class RecordingApi:
    instances = []

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.instances.append(self)

    def get_kl_data(self):
        return iter(())


def test_per_level_start_dates_are_passed_to_data_source():
    RecordingApi.instances.clear()
    chan = CChan.__new__(CChan)
    chan.code = "sz.000001"
    chan.begin_time = {KL_TYPE.K_WEEK: "2020-01-01", KL_TYPE.K_DAY: "2024-01-01"}
    chan.end_time = None
    chan.autype = AUTYPE.QFQ

    chan.get_load_stock_iter(RecordingApi, KL_TYPE.K_WEEK)
    chan.get_load_stock_iter(RecordingApi, KL_TYPE.K_DAY)

    assert [item.kwargs["begin_date"] for item in RecordingApi.instances] == ["2020-01-01", "2024-01-01"]
