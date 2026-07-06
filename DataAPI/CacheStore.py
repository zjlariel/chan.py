import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from Common.CEnum import DATA_FIELD, KL_TYPE
from Common.CTime import CTime
from DataAPI.Symbol import is_etf_symbol
from KLine.KLine_Unit import CKLine_Unit


class CacheStore:
    COVERAGE_EDGE_TOLERANCE_DAYS = 3
    CONFIRMED_EDGE_TOLERANCE_DAYS = 14
    PERIOD_EDGE_TOLERANCE_DAYS = 14
    FIRST_AVAILABLE_MIN_BARS = 20
    PERIOD_EDGE_TOLERANCE_TYPES = {KL_TYPE.K_WEEK, KL_TYPE.K_MON, KL_TYPE.K_QUARTER, KL_TYPE.K_YEAR}

    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS bars (
                    symbol TEXT NOT NULL,
                    k_type TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    open REAL NOT NULL,
                    high REAL NOT NULL,
                    low REAL NOT NULL,
                    close REAL NOT NULL,
                    volume REAL,
                    turnover REAL,
                    source TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (symbol, k_type, timestamp)
                );
                CREATE TABLE IF NOT EXISTS coverage (
                    symbol TEXT NOT NULL,
                    k_type TEXT NOT NULL,
                    start_date TEXT NOT NULL,
                    end_date TEXT NOT NULL,
                    source TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (symbol, k_type, start_date, end_date, source)
                );
                CREATE TABLE IF NOT EXISTS stock_metadata (
                    symbol TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    source TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                """
            )

    def upsert_bars(self, symbol, k_type, bars, source):
        rows = []
        for bar in bars:
            rows.append(
                (
                    symbol,
                    k_type.name,
                    self._timestamp_key(bar.time),
                    bar.open,
                    bar.high,
                    bar.low,
                    bar.close,
                    bar.trade_info.metric.get(DATA_FIELD.FIELD_VOLUME),
                    bar.trade_info.metric.get(DATA_FIELD.FIELD_TURNOVER),
                    source,
                )
            )
        if not rows:
            return {"inserted": 0, "updated": 0}
        timestamps = {row[2] for row in rows}
        with self._connect() as connection:
            existing_timestamps = {
                row["timestamp"]
                for row in connection.execute(
                    """
                    SELECT timestamp FROM bars
                    WHERE symbol = ? AND k_type = ? AND timestamp >= ? AND timestamp <= ?
                    """,
                    (symbol, k_type.name, min(timestamps), max(timestamps)),
                )
            }
        inserted = len(timestamps - existing_timestamps)
        updated = len(rows) - inserted
        updated_at = self._now()
        rows = [row + (updated_at,) for row in rows]
        with self._connect() as connection:
            connection.executemany(
                """
                INSERT INTO bars (symbol, k_type, timestamp, open, high, low, close, volume, turnover, source, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(symbol, k_type, timestamp) DO UPDATE SET
                    open = excluded.open,
                    high = excluded.high,
                    low = excluded.low,
                    close = excluded.close,
                    volume = excluded.volume,
                    turnover = excluded.turnover,
                    source = excluded.source,
                    updated_at = excluded.updated_at
                """,
                rows,
            )
        return {"inserted": inserted, "updated": updated}

    def read_bars(self, symbol, k_type, begin_date=None, end_date=None):
        clauses = ["symbol = ?", "k_type = ?"]
        params = [symbol, k_type.name]
        if begin_date:
            clauses.append("timestamp >= ?")
            params.append(self._range_start(begin_date))
        if end_date:
            clauses.append("timestamp <= ?")
            params.append(self._range_end(end_date))
        query = f"SELECT * FROM bars WHERE {' AND '.join(clauses)} ORDER BY timestamp"
        with self._connect() as connection:
            rows = connection.execute(query, params).fetchall()
        return [self._row_to_bar(row) for row in rows]

    def mark_covered(self, symbol, k_type, start_date, end_date, source):
        updated_at = self._now()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO coverage (symbol, k_type, start_date, end_date, source, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(symbol, k_type, start_date, end_date, source) DO UPDATE SET
                    updated_at = excluded.updated_at
                """,
                (symbol, k_type.name, start_date[:10], end_date[:10], source, updated_at),
            )

    def replace_coverage(self, symbol, k_type, start_date, end_date, source):
        with self._connect() as connection:
            connection.execute(
                "DELETE FROM coverage WHERE symbol = ? AND k_type = ?",
                (symbol, k_type.name),
            )
        self.mark_covered(symbol, k_type, start_date, end_date, source)

    def latest_timestamp(self, symbol, k_type):
        with self._connect() as connection:
            row = connection.execute(
                "SELECT MAX(timestamp) AS timestamp FROM bars WHERE symbol = ? AND k_type = ?",
                (symbol, k_type.name),
            ).fetchone()
        return row["timestamp"] if row and row["timestamp"] else None

    def timestamp_range(self, symbol, k_type, begin_date=None, end_date=None):
        clauses = ["symbol = ?", "k_type = ?"]
        params = [symbol, k_type.name]
        if begin_date:
            clauses.append("timestamp >= ?")
            params.append(self._range_start(begin_date))
        if end_date:
            clauses.append("timestamp <= ?")
            params.append(self._range_end(end_date))
        query = f"SELECT MIN(timestamp) AS first_timestamp, MAX(timestamp) AS last_timestamp FROM bars WHERE {' AND '.join(clauses)}"
        with self._connect() as connection:
            row = connection.execute(query, params).fetchone()
        if not row or not row["first_timestamp"] or not row["last_timestamp"]:
            return None
        return row["first_timestamp"], row["last_timestamp"]

    def prune_before(self, symbol, k_type, start_date):
        with self._connect() as connection:
            result = connection.execute(
                "DELETE FROM bars WHERE symbol = ? AND k_type = ? AND timestamp < ?",
                (symbol, k_type.name, self._range_start(start_date)),
            )
        return result.rowcount

    def covers(self, symbol, k_type, begin_date, end_date):
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT start_date, end_date FROM coverage
                WHERE symbol = ? AND k_type = ?
                """,
                (symbol, k_type.name),
            ).fetchall()
        if not rows:
            return False
        actual_range = self.timestamp_range(symbol, k_type, begin_date, end_date)
        if actual_range is None:
            return False
        actual_count = self.count_bars(symbol, k_type, begin_date, end_date)
        requested_start = datetime.fromisoformat(self._range_start(begin_date))
        requested_end = datetime.fromisoformat(self._range_end(end_date))
        actual_start = datetime.fromisoformat(actual_range[0])
        actual_end = datetime.fromisoformat(actual_range[1])
        tolerance = self._edge_tolerance(k_type)
        actual_start_date = actual_start.date().isoformat()
        for row in rows:
            coverage_start = datetime.fromisoformat(self._range_start(row["start_date"]))
            coverage_end = datetime.fromisoformat(self._range_end(row["end_date"]))
            starts_from_first_available = (
                actual_count >= self.FIRST_AVAILABLE_MIN_BARS
                and actual_start > requested_start + tolerance
                and row["start_date"] == actual_start_date
            )
            coverage_start_ok = self._start_edge_ok(coverage_start, requested_start, tolerance) or starts_from_first_available
            coverage_end_ok = self._end_edge_ok(coverage_end, requested_end, tolerance)
            actual_start_tolerance = self._actual_edge_tolerance(k_type, coverage_start <= requested_start)
            actual_end_tolerance = self._actual_edge_tolerance(k_type, coverage_end >= requested_end)
            actual_start_ok = actual_start <= requested_start + actual_start_tolerance or starts_from_first_available
            actual_end_ok = self._end_edge_ok(actual_end, requested_end, actual_end_tolerance)
            if coverage_start_ok and coverage_end_ok and actual_start_ok and actual_end_ok:
                return True
        return False

    @staticmethod
    def _start_edge_ok(edge_start, requested_start, tolerance):
        return edge_start <= requested_start + tolerance

    @staticmethod
    def _end_edge_ok(edge_end, requested_end, tolerance):
        return edge_end.date() >= (requested_end - tolerance).date()

    @classmethod
    def _edge_tolerance(cls, k_type):
        days = cls.PERIOD_EDGE_TOLERANCE_DAYS if k_type in cls.PERIOD_EDGE_TOLERANCE_TYPES else cls.COVERAGE_EDGE_TOLERANCE_DAYS
        return timedelta(days=days)

    @classmethod
    def _actual_edge_tolerance(cls, k_type, coverage_confirms_edge):
        if not coverage_confirms_edge:
            return cls._edge_tolerance(k_type)
        days = max(cls.CONFIRMED_EDGE_TOLERANCE_DAYS, cls.PERIOD_EDGE_TOLERANCE_DAYS if k_type in cls.PERIOD_EDGE_TOLERANCE_TYPES else cls.COVERAGE_EDGE_TOLERANCE_DAYS)
        return timedelta(days=days)

    def count_bars(self, symbol, k_type, begin_date=None, end_date=None):
        clauses = ["symbol = ?", "k_type = ?"]
        params = [symbol, k_type.name]
        if begin_date:
            clauses.append("timestamp >= ?")
            params.append(self._range_start(begin_date))
        if end_date:
            clauses.append("timestamp <= ?")
            params.append(self._range_end(end_date))
        query = f"SELECT COUNT(*) AS count FROM bars WHERE {' AND '.join(clauses)}"
        with self._connect() as connection:
            row = connection.execute(query, params).fetchone()
        return row["count"] if row else 0

    def upsert_stock_name(self, symbol, name, source):
        name = str(name).strip()
        if not name:
            return
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO stock_metadata (symbol, name, source, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(symbol) DO UPDATE SET
                    name = excluded.name,
                    source = excluded.source,
                    updated_at = excluded.updated_at
                """,
                (symbol, name, source, self._now()),
            )

    def stock_name(self, symbol):
        with self._connect() as connection:
            row = connection.execute(
                "SELECT name FROM stock_metadata WHERE symbol = ?",
                (symbol,),
            ).fetchone()
        return row["name"] if row else None

    def status(self):
        with self._connect() as connection:
            return connection.execute(
                """
                SELECT symbol, k_type, MIN(timestamp) AS first_timestamp, MAX(timestamp) AS last_timestamp,
                       COUNT(*) AS bar_count, MAX(updated_at) AS updated_at
                FROM bars
                GROUP BY symbol, k_type
                ORDER BY symbol, k_type
                """
            ).fetchall()

    def _connect(self):
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        return connection

    @staticmethod
    def _timestamp_key(time):
        return f"{time.year:04}-{time.month:02}-{time.day:02} {time.hour:02}:{time.minute:02}"

    @staticmethod
    def _now():
        return datetime.now(ZoneInfo("Asia/Shanghai")).strftime("%Y-%m-%d %H:%M:%S")

    @staticmethod
    def _range_start(value):
        return value if len(value) > 10 else f"{value[:10]} 00:00"

    @staticmethod
    def _range_end(value):
        return value if len(value) > 10 else f"{value[:10]} 23:59"

    @staticmethod
    def _row_to_bar(row):
        timestamp = datetime.strptime(row["timestamp"], "%Y-%m-%d %H:%M")
        return CKLine_Unit(
            {
                DATA_FIELD.FIELD_TIME: CTime(
                    timestamp.year, timestamp.month, timestamp.day, timestamp.hour, timestamp.minute, auto=False
                ),
                DATA_FIELD.FIELD_OPEN: row["open"],
                DATA_FIELD.FIELD_HIGH: row["high"],
                DATA_FIELD.FIELD_LOW: row["low"],
                DATA_FIELD.FIELD_CLOSE: row["close"],
                DATA_FIELD.FIELD_VOLUME: row["volume"],
                DATA_FIELD.FIELD_TURNOVER: row["turnover"],
            }
        )
