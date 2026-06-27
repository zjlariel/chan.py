import sqlite3
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


INITIAL_POSITIONS = [
    ("688008", "澜起科技", 200, 200, 253.044),
    ("002837", "英维克", 300, 300, 71.940),
    ("002536", "飞龙股份", 400, 400, 41.343),
    ("002460", "赣锋锂业", 200, 200, 71.695),
    ("600549", "厦门钨业", 100, 100, 44.691),
]


class PortfolioStore:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def initialize(self):
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS tracked_stocks (
                    symbol TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    quantity INTEGER NOT NULL DEFAULT 0 CHECK (quantity >= 0),
                    available_quantity INTEGER NOT NULL DEFAULT 0 CHECK (available_quantity >= 0),
                    cost_price REAL,
                    group_name TEXT,
                    note TEXT,
                    active INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0, 1)),
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            now = self._now()
            connection.executemany(
                """
                INSERT OR IGNORE INTO tracked_stocks
                (symbol, name, quantity, available_quantity, cost_price, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                [position + (now, now) for position in INITIAL_POSITIONS],
            )

    def set_position(self, symbol, name, quantity, available_quantity=None, cost_price=None, group_name=None, note=None, active=True):
        self.initialize()
        symbol = self._normalize_symbol(symbol)
        if quantity < 0:
            raise ValueError("持仓数量不能为负数")
        if available_quantity is None:
            available_quantity = quantity
        if available_quantity < 0 or available_quantity > quantity:
            raise ValueError("可用数量必须介于 0 和持仓数量之间")
        if quantity == 0:
            cost_price = None
        elif cost_price is None or cost_price <= 0:
            raise ValueError("持仓股票必须提供大于 0 的成本价")

        now = self._now()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO tracked_stocks
                (symbol, name, quantity, available_quantity, cost_price, group_name, note, active, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(symbol) DO UPDATE SET
                    name = excluded.name,
                    quantity = excluded.quantity,
                    available_quantity = excluded.available_quantity,
                    cost_price = excluded.cost_price,
                    group_name = excluded.group_name,
                    note = excluded.note,
                    active = excluded.active,
                    updated_at = excluded.updated_at
                """,
                (symbol, name, quantity, available_quantity, cost_price, group_name, note, int(active), now, now),
            )

    def list_positions(self, active_only=True):
        self.initialize()
        query = "SELECT * FROM tracked_stocks"
        if active_only:
            query += " WHERE active = 1"
        query += " ORDER BY quantity > 0 DESC, symbol"
        with self._connect() as connection:
            rows = connection.execute(query).fetchall()
        return [self._row_to_position(row) for row in rows]

    def delete_position(self, symbol):
        self.initialize()
        symbol = self._normalize_symbol(symbol)
        now = self._now()
        with self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE tracked_stocks
                SET active = 0, updated_at = ?
                WHERE symbol = ? AND active = 1
                """,
                (now, symbol),
            )
        return cursor.rowcount > 0

    def _connect(self):
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        return connection

    @staticmethod
    def _normalize_symbol(symbol):
        symbol = str(symbol).lower().replace(".", "")
        if symbol[:2] in {"sh", "sz"}:
            symbol = symbol[2:]
        if len(symbol) != 6 or not symbol.isdigit() or symbol[0] not in {"0", "3", "6"}:
            raise ValueError(f"不支持的 A 股代码：{symbol}")
        return symbol

    @staticmethod
    def _now():
        return datetime.now(ZoneInfo("Asia/Shanghai")).strftime("%Y-%m-%d %H:%M:%S")

    @staticmethod
    def _row_to_position(row):
        position = dict(row)
        position["status"] = "holding" if position["quantity"] > 0 else "watching"
        return position
