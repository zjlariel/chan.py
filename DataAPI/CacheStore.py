import sqlite3
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from Common.CEnum import DATA_FIELD
from Common.CTime import CTime
from KLine.KLine_Unit import CKLine_Unit


class CacheStore:
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
            return
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

    def prune_before(self, symbol, k_type, start_date):
        with self._connect() as connection:
            result = connection.execute(
                "DELETE FROM bars WHERE symbol = ? AND k_type = ? AND timestamp < ?",
                (symbol, k_type.name, self._range_start(start_date)),
            )
        return result.rowcount

    def covers(self, symbol, k_type, begin_date, end_date):
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT 1 FROM coverage
                WHERE symbol = ? AND k_type = ? AND start_date <= ? AND end_date >= ?
                LIMIT 1
                """,
                (symbol, k_type.name, begin_date[:10], end_date[:10]),
            ).fetchone()
        return row is not None

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
