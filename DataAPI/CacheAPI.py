from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from Common.CEnum import KL_TYPE
from DataAPI.SinaAPI import CSina

from .CacheStore import CacheStore
from .CommonStockAPI import CCommonStockApi


class CCache(CCommonStockApi):
    DEFAULT_PATH = Path(".chanpy/cache.sqlite3")
    RETENTION_DAYS = {
        KL_TYPE.K_WEEK: 2400,
        KL_TYPE.K_DAY: 1200,
        KL_TYPE.K_60M: 360,
        KL_TYPE.K_30M: 180,
        KL_TYPE.K_15M: 90,
        KL_TYPE.K_5M: 20,
        KL_TYPE.K_1M: 5,
    }
    MINUTE_TYPES = {KL_TYPE.K_1M, KL_TYPE.K_5M, KL_TYPE.K_15M, KL_TYPE.K_30M, KL_TYPE.K_60M}

    def __init__(
        self,
        code,
        k_type,
        begin_date=None,
        end_date=None,
        autype=None,
        cache_path=None,
        now=None,
        provider_classes=None,
        mode="auto",
    ):
        super().__init__(code, k_type, begin_date, end_date, autype)
        if mode not in {"auto", "live", "eod"}:
            raise ValueError(f"unknown cache refresh mode: {mode}")
        self.symbol = CSina.normalize_symbol(code)
        self.store = CacheStore(cache_path or self.DEFAULT_PATH)
        self.now = now or datetime.now(ZoneInfo("Asia/Shanghai"))
        self.mode = mode
        self.provider_classes = provider_classes or self._default_providers()

    def get_kl_data(self):
        begin_date, end_date = self._requested_range()
        if not self.store.covers(self.symbol, self.k_type, begin_date, end_date):
            provider_name = self._provider_name()
            if provider_name:
                self._refresh(provider_name, begin_date, end_date)
        yield from self.store.read_bars(self.symbol, self.k_type, begin_date, end_date)

    def refresh(self):
        begin_date, end_date = self._requested_range()
        provider_name = self._provider_name()
        if provider_name:
            self._refresh(provider_name, begin_date, end_date)

    def _refresh(self, provider_name, begin_date, end_date):
        provider_class = self.provider_classes[provider_name]
        if hasattr(provider_class, "do_init"):
            provider_class.do_init()
        provider = provider_class(
            self._provider_code(provider_name), self.k_type, begin_date, end_date, self.autype
        )
        bars = list(provider.get_kl_data())
        if bars:
            self.store.upsert_bars(self.symbol, self.k_type, bars, provider_name)
            self.store.mark_covered(self.symbol, self.k_type, begin_date, end_date, provider_name)

    def _requested_range(self):
        end_date = self.end_date[:10] if self.end_date else self.now.date().isoformat()
        if self.begin_date:
            return self.begin_date[:10], end_date
        try:
            days = self.RETENTION_DAYS[self.k_type]
        except KeyError as exc:
            raise ValueError(f"no cache retention configured for {self.k_type}") from exc
        begin_date = (datetime.fromisoformat(end_date).date() - timedelta(days=days)).isoformat()
        return begin_date, end_date

    def _provider_name(self):
        mode = self.mode
        if mode == "auto":
            mode = "live" if self._is_market_open() else "eod"
        if mode == "live" and self.k_type in self.MINUTE_TYPES:
            return "sina"
        if mode == "eod" and self.k_type == KL_TYPE.K_1M:
            return None
        return "baostock"

    def _is_market_open(self):
        now = self.now
        if now.weekday() >= 5:
            return False
        clock = now.time()
        return (clock.hour, clock.minute) >= (9, 30) and (clock.hour, clock.minute) <= (11, 30) or (
            (clock.hour, clock.minute) >= (13, 0) and (clock.hour, clock.minute) <= (15, 0)
        )

    def _provider_code(self, provider_name):
        if provider_name == "sina":
            return self.symbol
        return f"{self.symbol[:2]}.{self.symbol[2:]}"

    @staticmethod
    def _default_providers():
        from DataAPI.BaoStockAPI import CBaoStock

        return {"sina": CSina, "baostock": CBaoStock}

    def SetBasciInfo(self):
        self.name = self.code
        self.is_stock = True

    @classmethod
    def do_init(cls):
        pass

    @classmethod
    def do_close(cls):
        from DataAPI.BaoStockAPI import CBaoStock

        CBaoStock.do_close()
