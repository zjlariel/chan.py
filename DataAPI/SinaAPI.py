from datetime import datetime

import requests

from Common.CEnum import DATA_FIELD, KL_TYPE
from Common.ChanException import CChanException, ErrCode
from Common.CTime import CTime
from Common.func_util import str2float
from KLine.KLine_Unit import CKLine_Unit

from .CommonStockAPI import CCommonStockApi
from .Symbol import normalize_cn_symbol


class CSina(CCommonStockApi):
    KLINE_URL = "https://quotes.sina.cn/cn/api/json_v2.php/CN_MarketDataService.getKLineData"
    _SCALES = {
        KL_TYPE.K_1M: 1,
        KL_TYPE.K_5M: 5,
        KL_TYPE.K_15M: 15,
        KL_TYPE.K_30M: 30,
        KL_TYPE.K_60M: 60,
    }

    def __init__(self, code, k_type, begin_date, end_date, autype):
        super().__init__(code, k_type, begin_date, end_date, autype)
        self.symbol = self.normalize_symbol(code)

    @staticmethod
    def normalize_symbol(code):
        try:
            return normalize_cn_symbol(code)
        except ValueError as exc:
            raise ValueError(f"unsupported A-share or ETF symbol: {code}") from exc

    @classmethod
    def scale_for(cls, k_type):
        try:
            return cls._SCALES[k_type]
        except KeyError as exc:
            raise ValueError(f"Sina only supports minute K-lines, got: {k_type}") from exc

    def get_kl_data(self):
        scale = self.scale_for(self.k_type)
        params = {"symbol": self.symbol, "scale": scale, "ma": "no", "datalen": 1023}
        try:
            response = requests.get(self.KLINE_URL, params=params, timeout=10)
            response.raise_for_status()
            rows = response.json()
        except (requests.RequestException, ValueError) as exc:
            raise CChanException(
                f"failed to load Sina minute data for {self.symbol} ({scale}m): {exc}",
                ErrCode.SRC_DATA_FORMAT_ERROR,
            ) from exc

        if not isinstance(rows, list):
            raise CChanException(
                f"invalid Sina minute response for {self.symbol} ({scale}m)",
                ErrCode.SRC_DATA_FORMAT_ERROR,
            )

        for row in rows:
            try:
                timestamp = datetime.strptime(row["day"], "%Y-%m-%d %H:%M:%S")
                if not self._in_requested_range(timestamp):
                    continue
                item = {
                    DATA_FIELD.FIELD_TIME: CTime(
                        timestamp.year, timestamp.month, timestamp.day, timestamp.hour, timestamp.minute, auto=False
                    ),
                    DATA_FIELD.FIELD_OPEN: str2float(row["open"]),
                    DATA_FIELD.FIELD_HIGH: str2float(row["high"]),
                    DATA_FIELD.FIELD_LOW: str2float(row["low"]),
                    DATA_FIELD.FIELD_CLOSE: str2float(row["close"]),
                    DATA_FIELD.FIELD_VOLUME: str2float(row["volume"]),
                    DATA_FIELD.FIELD_TURNOVER: str2float(row["amount"]),
                }
            except (KeyError, TypeError, ValueError) as exc:
                raise CChanException(
                    f"invalid Sina K-line row for {self.symbol} ({scale}m): {row}",
                    ErrCode.SRC_DATA_FORMAT_ERROR,
                ) from exc
            yield CKLine_Unit(item)

    def _in_requested_range(self, timestamp):
        date = timestamp.date().isoformat()
        return (not self.begin_date or date >= self.begin_date[:10]) and (
            not self.end_date or date <= self.end_date[:10]
        )

    def SetBasciInfo(self):
        self.name = self.code
        self.is_stock = True

    @classmethod
    def do_init(cls):
        pass

    @classmethod
    def do_close(cls):
        pass
