import requests

from Common.CEnum import AUTYPE, DATA_FIELD, KL_TYPE
from Common.ChanException import CChanException, ErrCode
from Common.CTime import CTime
from Common.func_util import str2float
from KLine.KLine_Unit import CKLine_Unit

from .CommonStockAPI import CCommonStockApi
from .Symbol import is_etf_symbol


class CEastMoney(CCommonStockApi):
    KLINE_URL = "https://push2his.eastmoney.com/api/qt/stock/kline/get"
    MAX_RETRIES = 3
    SUPPORTED_TYPES = {
        KL_TYPE.K_DAY: "101",
        KL_TYPE.K_WEEK: "102",
    }

    def __init__(self, code, k_type=KL_TYPE.K_DAY, begin_date=None, end_date=None, autype=AUTYPE.NONE):
        super().__init__(self.normalize_symbol(code), k_type, begin_date, end_date, autype)

    @staticmethod
    def normalize_symbol(code):
        symbol = str(code).lower().replace(".", "")
        if symbol[:2] in {"sh", "sz"}:
            symbol = symbol[2:]
        if not is_etf_symbol(symbol):
            raise ValueError(f"东方财富 ETF 数据源不支持的代码：{code}")
        return symbol

    def get_kl_data(self):
        try:
            klt = self.SUPPORTED_TYPES[self.k_type]
        except KeyError as exc:
            raise ValueError(f"东方财富不支持{self.k_type}级别的 K 线数据") from exc

        params = {
            "secid": self._secid(),
            "fields1": "f1,f2,f3,f4,f5,f6",
            "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61",
            "klt": klt,
            "fqt": self._adjust_flag(),
            "beg": self._date_arg(self.begin_date, "19900101"),
            "end": self._date_arg(self.end_date, "20991231"),
        }
        payload = self._request_json(params)

        data = payload.get("data") if isinstance(payload, dict) else None
        if not data:
            return
        name = data.get("name")
        if name:
            self.name = name
        for row in data.get("klines") or []:
            yield CKLine_Unit(self._parse_kline(row))

    def SetBasciInfo(self):
        self.name = self.code
        self.is_stock = True

    @classmethod
    def do_init(cls):
        pass

    @classmethod
    def do_close(cls):
        pass

    def _secid(self):
        market = "1" if self.code.startswith(("51", "56", "58")) else "0"
        return f"{market}.{self.code}"

    def _adjust_flag(self):
        return {
            AUTYPE.NONE: "0",
            AUTYPE.QFQ: "1",
            AUTYPE.HFQ: "2",
        }[self.autype]

    @staticmethod
    def _date_arg(value, default):
        return value.replace("-", "")[:8] if value else default

    def _request_json(self, params):
        last_error = None
        for _ in range(self.MAX_RETRIES):
            try:
                response = requests.get(self.KLINE_URL, params=params, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
                response.raise_for_status()
                return response.json()
            except (requests.RequestException, ValueError) as exc:
                last_error = exc
        raise CChanException(
            f"东方财富 ETF K 线加载失败：{self.code} {self.k_type.name} {last_error}",
            ErrCode.SRC_DATA_FORMAT_ERROR,
        ) from last_error

    @staticmethod
    def _parse_kline(row):
        parts = row.split(",")
        if len(parts) < 7:
            raise CChanException(
                f"东方财富 ETF K 线格式错误：{row}",
                ErrCode.SRC_DATA_FORMAT_ERROR,
            )
        year = int(parts[0][0:4])
        month = int(parts[0][5:7])
        day = int(parts[0][8:10])
        return {
            DATA_FIELD.FIELD_TIME: CTime(year, month, day, 0, 0),
            DATA_FIELD.FIELD_OPEN: str2float(parts[1]),
            DATA_FIELD.FIELD_CLOSE: str2float(parts[2]),
            DATA_FIELD.FIELD_HIGH: str2float(parts[3]),
            DATA_FIELD.FIELD_LOW: str2float(parts[4]),
            DATA_FIELD.FIELD_VOLUME: str2float(parts[5]),
            DATA_FIELD.FIELD_TURNOVER: str2float(parts[6]),
        }
