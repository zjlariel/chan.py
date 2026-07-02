from datetime import datetime, timezone

import requests

from Common.CEnum import AUTYPE, DATA_FIELD, KL_TYPE
from Common.ChanException import CChanException, ErrCode
from Common.CTime import CTime
from KLine.KLine_Unit import CKLine_Unit

from .CommonStockAPI import CCommonStockApi
from .Symbol import is_etf_symbol


class CYahooFinance(CCommonStockApi):
    CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart"
    SUPPORTED_TYPES = {
        KL_TYPE.K_DAY: "1d",
        KL_TYPE.K_WEEK: "1wk",
    }

    def __init__(self, code, k_type=KL_TYPE.K_DAY, begin_date=None, end_date=None, autype=AUTYPE.NONE):
        super().__init__(self.normalize_symbol(code), k_type, begin_date, end_date, autype)

    @staticmethod
    def normalize_symbol(code):
        symbol = str(code).lower().replace(".", "")
        if symbol[:2] in {"sh", "sz"}:
            symbol = symbol[2:]
        if not is_etf_symbol(symbol):
            raise ValueError(f"Yahoo Finance ETF 数据源不支持的代码：{code}")
        return symbol

    def get_kl_data(self):
        try:
            interval = self.SUPPORTED_TYPES[self.k_type]
        except KeyError as exc:
            raise ValueError(f"Yahoo Finance 不支持{self.k_type}级别的 K 线数据") from exc

        payload = self._request_json(
            {
                "period1": self._timestamp_arg(self.begin_date, "0"),
                "period2": self._timestamp_arg(self.end_date, "4102444800", end_of_day=True),
                "interval": interval,
                "events": "history",
            }
        )
        result = self._chart_result(payload)
        meta = result.get("meta") or {}
        name = meta.get("shortName") or meta.get("longName")
        if name:
            self.name = name
        timestamps = result.get("timestamp") or []
        quote = ((result.get("indicators") or {}).get("quote") or [{}])[0]
        for index, timestamp in enumerate(timestamps):
            item = self._parse_bar(timestamp, quote, index)
            if item:
                yield CKLine_Unit(item)

    def SetBasciInfo(self):
        self.name = self.code
        self.is_stock = True

    @classmethod
    def do_init(cls):
        pass

    @classmethod
    def do_close(cls):
        pass

    def _request_json(self, params):
        url = f"{self.CHART_URL}/{self._yahoo_symbol()}"
        try:
            response = requests.get(url, params=params, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
            response.raise_for_status()
            return response.json()
        except (requests.RequestException, ValueError) as exc:
            raise CChanException(
                f"Yahoo Finance ETF K 线加载失败：{self.code} {self.k_type.name} {exc}",
                ErrCode.SRC_DATA_FORMAT_ERROR,
            ) from exc

    def _yahoo_symbol(self):
        suffix = ".SS" if self.code.startswith(("51", "56", "58")) else ".SZ"
        return f"{self.code}{suffix}"

    @staticmethod
    def _timestamp_arg(value, default, end_of_day=False):
        if not value:
            return default
        date_value = datetime.fromisoformat(value[:10]).replace(tzinfo=timezone.utc)
        if end_of_day:
            date_value = date_value.replace(hour=23, minute=59, second=59)
        return str(int(date_value.timestamp()))

    @staticmethod
    def _chart_result(payload):
        chart = payload.get("chart") if isinstance(payload, dict) else None
        if not chart:
            raise CChanException("Yahoo Finance 返回格式缺少 chart", ErrCode.SRC_DATA_FORMAT_ERROR)
        if chart.get("error"):
            raise CChanException(f"Yahoo Finance 返回错误：{chart['error']}", ErrCode.SRC_DATA_FORMAT_ERROR)
        results = chart.get("result") or []
        if not results:
            raise CChanException("Yahoo Finance 返回结果为空", ErrCode.SRC_DATA_FORMAT_ERROR)
        return results[0]

    @staticmethod
    def _parse_bar(timestamp, quote, index):
        try:
            open_price = quote["open"][index]
            high_price = quote["high"][index]
            low_price = quote["low"][index]
            close_price = quote["close"][index]
            volume = quote["volume"][index]
        except (KeyError, IndexError, TypeError) as exc:
            raise CChanException("Yahoo Finance K 线字段缺失", ErrCode.SRC_DATA_FORMAT_ERROR) from exc
        if None in {open_price, high_price, low_price, close_price}:
            return None
        if min(open_price, high_price, low_price, close_price) <= 0:
            return None
        if low_price > min(open_price, high_price, low_price, close_price):
            return None
        if high_price < max(open_price, high_price, low_price, close_price):
            return None
        bar_time = datetime.fromtimestamp(timestamp, tz=timezone.utc)
        return {
            DATA_FIELD.FIELD_TIME: CTime(bar_time.year, bar_time.month, bar_time.day, 0, 0),
            DATA_FIELD.FIELD_OPEN: float(open_price),
            DATA_FIELD.FIELD_HIGH: float(high_price),
            DATA_FIELD.FIELD_LOW: float(low_price),
            DATA_FIELD.FIELD_CLOSE: float(close_price),
            DATA_FIELD.FIELD_VOLUME: 0 if volume is None else float(volume),
            DATA_FIELD.FIELD_TURNOVER: 0,
        }
