import sqlite3
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


class EtfStore:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def initialize(self):
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS tracked_etfs (
                    symbol TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    quantity INTEGER NOT NULL DEFAULT 0 CHECK (quantity >= 0),
                    available_quantity INTEGER NOT NULL DEFAULT 0 CHECK (available_quantity >= 0),
                    cost_price REAL,
                    category TEXT,
                    tracking_index TEXT,
                    note TEXT,
                    active INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0, 1)),
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )

    def set_position(
        self,
        symbol,
        name,
        quantity,
        available_quantity=None,
        cost_price=None,
        category=None,
        tracking_index=None,
        note=None,
        active=True,
    ):
        self.initialize()
        symbol = self._normalize_symbol(symbol)
        if quantity < 0:
            raise ValueError("持仓份额不能为负数")
        if available_quantity is None:
            available_quantity = quantity
        if available_quantity < 0 or available_quantity > quantity:
            raise ValueError("可用份额必须介于 0 和持仓份额之间")
        if quantity == 0:
            cost_price = None
        elif cost_price is None or cost_price <= 0:
            raise ValueError("持仓 ETF 必须提供大于 0 的成本价")

        now = self._now()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO tracked_etfs
                (symbol, name, quantity, available_quantity, cost_price, category, tracking_index, note, active, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(symbol) DO UPDATE SET
                    name = excluded.name,
                    quantity = excluded.quantity,
                    available_quantity = excluded.available_quantity,
                    cost_price = excluded.cost_price,
                    category = excluded.category,
                    tracking_index = excluded.tracking_index,
                    note = excluded.note,
                    active = excluded.active,
                    updated_at = excluded.updated_at
                """,
                (
                    symbol,
                    name,
                    quantity,
                    available_quantity,
                    cost_price,
                    category,
                    tracking_index,
                    note,
                    int(active),
                    now,
                    now,
                ),
            )

    def list_positions(self, active_only=True):
        self.initialize()
        query = "SELECT * FROM tracked_etfs"
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
                UPDATE tracked_etfs
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
        if len(symbol) != 6 or not symbol.isdigit() or not symbol.startswith(("15", "51", "56", "58")):
            raise ValueError(f"不支持的 ETF 代码：{symbol}")
        return symbol

    @staticmethod
    def _now():
        return datetime.now(ZoneInfo("Asia/Shanghai")).strftime("%Y-%m-%d %H:%M:%S")

    @staticmethod
    def _row_to_position(row):
        position = dict(row)
        position["status"] = "holding" if position["quantity"] > 0 else "watching"
        return position
