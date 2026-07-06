from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from Common.CEnum import AUTYPE, KL_TYPE
from Common.ChanException import CChanException, ErrCode
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
        if mode not in {"auto", "live", "eod", "readonly"}:
            raise ValueError(f"unknown cache refresh mode: {mode}")
        self.symbol = CSina.normalize_symbol(code)
        self.store = CacheStore(cache_path or self.DEFAULT_PATH)
        self.now = now or datetime.now(ZoneInfo("Asia/Shanghai"))
        self.mode = mode
        self.provider_classes = provider_classes or self._default_providers()

    def get_kl_data(self):
        begin_date, end_date = self._requested_range()
        if not self.store.covers(self.symbol, self.k_type, begin_date, end_date):
            if self.mode == "readonly":
                raise CChanException(
                    f"缓存缺失：{self.symbol} {self.k_type.name} {begin_date} 至 {end_date}，请先使用 --refresh 或 cache update 刷新数据",
                    ErrCode.SRC_DATA_NOT_FOUND,
                )
            self._refresh_first_available(begin_date, end_date, begin_date)
        yield from self.store.read_bars(self.symbol, self.k_type, begin_date, end_date)

    def refresh(self, full=False):
        begin_date, end_date = self._requested_range()
        if self.mode == "readonly":
            return {}
        if self.mode == "auto":
            return self._refresh_auto(begin_date, end_date, full)
        provider_names = self._provider_names()
        if provider_names:
            fetch_begin = begin_date if full or not self.store.covers(self.symbol, self.k_type, begin_date, end_date) else self._incremental_begin(begin_date)
            return self._refresh_first_available(fetch_begin, end_date, begin_date)
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
            self._merge_refresh_counts(refresh_counts, self._refresh_first_available(fetch_begin, min(end_date, yesterday)))

        if refresh_counts:
            self.store.prune_before(self.symbol, self.k_type, begin_date)
            actual_range = self.store.timestamp_range(self.symbol, self.k_type, begin_date, end_date)
            if actual_range:
                self.store.replace_coverage(self.symbol, self.k_type, actual_range[0], actual_range[1], "auto")
        return refresh_counts

    def _refresh_first_available(self, begin_date, end_date, retention_begin=None):
        provider_names = self._provider_names()
        if not provider_names:
            return {}
        last_error = None
        for provider_name in provider_names:
            try:
                refresh_counts = self._refresh(provider_name, begin_date, end_date, retention_begin)
                if refresh_counts:
                    return refresh_counts
            except (CChanException, RuntimeError, ValueError) as exc:
                last_error = exc
        if last_error:
            raise last_error
        return {}

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
            actual_begin, actual_end = self._bar_date_range(bars)
            coverage_begin, coverage_end = self._coverage_range_for_refresh(
                begin_date, end_date, actual_begin, actual_end, retention_begin
            )
            if retention_begin:
                self.store.prune_before(self.symbol, self.k_type, retention_begin)
                self.store.replace_coverage(self.symbol, self.k_type, coverage_begin, coverage_end, provider_name)
            else:
                self.store.mark_covered(self.symbol, self.k_type, coverage_begin, coverage_end, provider_name)
            return {provider_name: written}
        return {}

    @staticmethod
    def _bar_date_range(bars):
        first = min(bar.time for bar in bars)
        last = max(bar.time for bar in bars)
        return (
            f"{first.year:04}-{first.month:02}-{first.day:02}",
            f"{last.year:04}-{last.month:02}-{last.day:02}",
        )

    @staticmethod
    def _coverage_range_for_refresh(begin_date, end_date, actual_begin, actual_end, retention_begin=None):
        requested_begin = retention_begin or begin_date
        if CCache._is_edge_only_gap(requested_begin, end_date, actual_begin, actual_end):
            return requested_begin, end_date
        return max(requested_begin, actual_begin), actual_end

    @staticmethod
    def _is_edge_only_gap(requested_begin, requested_end, actual_begin, actual_end):
        tolerance = timedelta(days=CacheStore.CONFIRMED_EDGE_TOLERANCE_DAYS)
        requested_start = datetime.fromisoformat(requested_begin[:10]).date()
        requested_finish = datetime.fromisoformat(requested_end[:10]).date()
        actual_start = datetime.fromisoformat(actual_begin[:10]).date()
        actual_finish = datetime.fromisoformat(actual_end[:10]).date()
        return actual_start <= requested_start + tolerance and actual_finish >= requested_finish - tolerance

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

    def _provider_names(self):
        mode = self.mode
        if mode == "auto":
            mode = "live" if self._is_market_open() else "eod"
        if mode == "live" and self.k_type in self.MINUTE_TYPES:
            return ["sina"]
        if mode == "eod" and self.k_type == KL_TYPE.K_1M:
            return []
        if mode == "eod" and is_etf_symbol(self.symbol) and self.k_type in {KL_TYPE.K_DAY, KL_TYPE.K_WEEK}:
            return ["yahoo", "eastmoney"]
        return ["baostock"]

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
        if provider_name in {"eastmoney", "yahoo"}:
            return self.symbol[2:]
        return f"{self.symbol[:2]}.{self.symbol[2:]}"

    @staticmethod
    def _default_providers():
        from DataAPI.BaoStockAPI import CBaoStock
        from DataAPI.EastMoneyAPI import CEastMoney
        from DataAPI.YahooFinanceAPI import CYahooFinance

        return {"sina": CSina, "baostock": CBaoStock, "eastmoney": CEastMoney, "yahoo": CYahooFinance}

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


class CReadonlyCache(CCache):
    def __init__(self, *args, **kwargs):
        kwargs["mode"] = "readonly"
        super().__init__(*args, **kwargs)
