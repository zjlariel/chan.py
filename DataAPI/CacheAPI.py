from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from Common.CEnum import AUTYPE, KL_TYPE
from DataAPI.SinaAPI import CSina
from DataAPI.Symbol import is_etf_symbol

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
    REFRESH_OVERLAP_DAYS = 3

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
        effective_autype = autype or (AUTYPE.NONE if is_etf_symbol(code) else AUTYPE.QFQ)
        super().__init__(code, k_type, begin_date, end_date, effective_autype)
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
                self._refresh(provider_name, begin_date, end_date, begin_date)
        yield from self.store.read_bars(self.symbol, self.k_type, begin_date, end_date)

    def refresh(self, full=False):
        begin_date, end_date = self._requested_range()
        if self.mode == "auto":
            return self._refresh_auto(begin_date, end_date, full)
        provider_name = self._provider_name()
        if provider_name:
            fetch_begin = begin_date if full or not self.store.covers(self.symbol, self.k_type, begin_date, end_date) else self._incremental_begin(begin_date)
            return self._refresh(provider_name, fetch_begin, end_date, begin_date)
        return {}

    def _refresh_auto(self, begin_date, end_date, full):
        fetch_begin = begin_date if full or not self.store.covers(self.symbol, self.k_type, begin_date, end_date) else self._incremental_begin(begin_date)
        today = self.now.date().isoformat()
        yesterday = (self.now.date() - timedelta(days=1)).isoformat()
        refresh_counts = {}

        if self.k_type in self.MINUTE_TYPES and self.k_type != KL_TYPE.K_1M:
            history_end = min(end_date, yesterday)
            if fetch_begin <= history_end:
                self._merge_refresh_counts(refresh_counts, self._refresh("baostock", fetch_begin, history_end))

        if self.k_type in self.MINUTE_TYPES:
            today_begin = max(fetch_begin, today)
            if today_begin <= end_date:
                self._merge_refresh_counts(refresh_counts, self._refresh("sina", today_begin, end_date))
        elif fetch_begin <= min(end_date, yesterday):
            self._merge_refresh_counts(refresh_counts, self._refresh("baostock", fetch_begin, min(end_date, yesterday)))

        if refresh_counts:
            self.store.prune_before(self.symbol, self.k_type, begin_date)
            self.store.replace_coverage(self.symbol, self.k_type, begin_date, end_date, "auto")
        return refresh_counts

    def _refresh(self, provider_name, begin_date, end_date, retention_begin=None):
        provider_class = self.provider_classes[provider_name]
        if hasattr(provider_class, "do_init"):
            provider_class.do_init()
        provider = provider_class(
            self._provider_code(provider_name), self.k_type, begin_date, end_date, self.autype
        )
        self._remember_stock_name(provider, provider_name)
        bars = list(provider.get_kl_data())
        if bars:
            written = self.store.upsert_bars(self.symbol, self.k_type, bars, provider_name)
            if retention_begin:
                self.store.prune_before(self.symbol, self.k_type, retention_begin)
                self.store.replace_coverage(
                    self.symbol, self.k_type, retention_begin, end_date, provider_name
                )
            else:
                self.store.mark_covered(self.symbol, self.k_type, begin_date, end_date, provider_name)
            return {provider_name: written}
        return {}

    @staticmethod
    def _merge_refresh_counts(target, source):
        for provider_name, stats in source.items():
            target.setdefault(provider_name, {"inserted": 0, "updated": 0})
            for key in ("inserted", "updated"):
                target[provider_name][key] += stats[key]

    def _incremental_begin(self, retention_begin):
        latest_timestamp = self.store.latest_timestamp(self.symbol, self.k_type)
        if not latest_timestamp:
            return retention_begin
        overlap_begin = (
            datetime.fromisoformat(latest_timestamp).date() - timedelta(days=self.REFRESH_OVERLAP_DAYS)
        ).isoformat()
        return max(retention_begin, overlap_begin)

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

    def _remember_stock_name(self, provider, provider_name):
        name = getattr(provider, "name", None)
        if not name or name in {getattr(provider, "code", None), self.symbol}:
            return
        self.store.upsert_stock_name(self.symbol, name, provider_name)

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
