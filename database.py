# ─── database.py ─────────────────────────────────────────────────────────────
# All SQLite operations for income, expenses, relief entries and settings.

import sqlite3
import os
from config import DB_PATH


class DB:
    def __init__(self):
        self.conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init_tables()

    def _init_tables(self):
        self.conn.executescript("""
        CREATE TABLE IF NOT EXISTS income (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            category    TEXT    NOT NULL,
            name        TEXT    NOT NULL,
            amount      REAL    NOT NULL,
            date        TEXT    NOT NULL,
            notes       TEXT    DEFAULT '',
            receipt     TEXT    DEFAULT '',
            created_at  TEXT    DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS expenses (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            category     TEXT    NOT NULL,
            name         TEXT    NOT NULL,
            amount       REAL    NOT NULL,
            date         TEXT    NOT NULL,
            notes        TEXT    DEFAULT '',
            receipt      TEXT    DEFAULT '',
            tax_relief   TEXT    DEFAULT '',
            created_at   TEXT    DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS relief_entries (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            relief_key   TEXT    NOT NULL,
            name         TEXT    NOT NULL,
            amount       REAL    NOT NULL,
            date         TEXT    NOT NULL,
            notes        TEXT    DEFAULT '',
            receipt      TEXT    DEFAULT '',
            created_at   TEXT    DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS settings (
            key   TEXT PRIMARY KEY,
            value TEXT
        );
        """)
        self.conn.commit()

    # ── Income ────────────────────────────────────────────────────────────────

    def add_income(self, category, name, amount, date, notes="", receipt=""):
        cur = self.conn.execute(
            "INSERT INTO income (category, name, amount, date, notes, receipt) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (category, name, amount, date, notes, receipt)
        )
        self.conn.commit()
        return cur.lastrowid

    def get_income(self, category=None):
        if category:
            return self.conn.execute(
                "SELECT * FROM income WHERE category = ? ORDER BY date DESC", (category,)
            ).fetchall()
        return self.conn.execute(
            "SELECT * FROM income ORDER BY date DESC"
        ).fetchall()

    def get_income_by_id(self, row_id):
        return self.conn.execute(
            "SELECT * FROM income WHERE id = ?", (row_id,)
        ).fetchone()

    def delete_income(self, row_id):
        row = self.get_income_by_id(row_id)
        if row and row["receipt"] and os.path.exists(row["receipt"]):
            try:
                os.remove(row["receipt"])
            except OSError:
                pass
        self.conn.execute("DELETE FROM income WHERE id = ?", (row_id,))
        self.conn.commit()

    def total_income(self, category=None):
        if category:
            val = self.conn.execute(
                "SELECT COALESCE(SUM(amount), 0) FROM income WHERE category = ?", (category,)
            ).fetchone()[0]
        else:
            val = self.conn.execute(
                "SELECT COALESCE(SUM(amount), 0) FROM income"
            ).fetchone()[0]
        return float(val)

    # ── Expenses ──────────────────────────────────────────────────────────────

    def add_expense(self, category, name, amount, date, notes="", receipt="", tax_relief=""):
        cur = self.conn.execute(
            "INSERT INTO expenses (category, name, amount, date, notes, receipt, tax_relief) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (category, name, amount, date, notes, receipt, tax_relief)
        )
        self.conn.commit()
        return cur.lastrowid

    def get_expenses(self, category=None):
        if category:
            return self.conn.execute(
                "SELECT * FROM expenses WHERE category = ? ORDER BY date DESC", (category,)
            ).fetchall()
        return self.conn.execute(
            "SELECT * FROM expenses ORDER BY date DESC"
        ).fetchall()

    def get_expense_by_id(self, row_id):
        return self.conn.execute(
            "SELECT * FROM expenses WHERE id = ?", (row_id,)
        ).fetchone()

    def delete_expense(self, row_id):
        row = self.get_expense_by_id(row_id)
        if row and row["receipt"] and os.path.exists(row["receipt"]):
            try:
                os.remove(row["receipt"])
            except OSError:
                pass
        self.conn.execute("DELETE FROM expenses WHERE id = ?", (row_id,))
        self.conn.commit()

    def total_expenses(self, category=None):
        if category:
            val = self.conn.execute(
                "SELECT COALESCE(SUM(amount), 0) FROM expenses WHERE category = ?", (category,)
            ).fetchone()[0]
        else:
            val = self.conn.execute(
                "SELECT COALESCE(SUM(amount), 0) FROM expenses"
            ).fetchone()[0]
        return float(val)

    def tax_deductible_by_relief(self):
        """Return {relief_key: total_amount} for all expenses with a tax_relief tag."""
        rows = self.conn.execute(
            "SELECT tax_relief, COALESCE(SUM(amount), 0) AS s "
            "FROM expenses WHERE tax_relief != '' GROUP BY tax_relief"
        ).fetchall()
        return {r["tax_relief"]: float(r["s"]) for r in rows}

    # ── Manual relief entries ─────────────────────────────────────────────────

    def add_relief(self, relief_key, name, amount, date, notes="", receipt=""):
        cur = self.conn.execute(
            "INSERT INTO relief_entries (relief_key, name, amount, date, notes, receipt) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (relief_key, name, amount, date, notes, receipt)
        )
        self.conn.commit()
        return cur.lastrowid

    def get_reliefs(self, relief_key=None):
        if relief_key:
            return self.conn.execute(
                "SELECT * FROM relief_entries WHERE relief_key = ? ORDER BY date DESC",
                (relief_key,)
            ).fetchall()
        return self.conn.execute(
            "SELECT * FROM relief_entries ORDER BY date DESC"
        ).fetchall()

    def get_relief_by_id(self, row_id):
        return self.conn.execute(
            "SELECT * FROM relief_entries WHERE id = ?", (row_id,)
        ).fetchone()

    def delete_relief(self, row_id):
        row = self.get_relief_by_id(row_id)
        if row and row["receipt"] and os.path.exists(row["receipt"]):
            try:
                os.remove(row["receipt"])
            except OSError:
                pass
        self.conn.execute("DELETE FROM relief_entries WHERE id = ?", (row_id,))
        self.conn.commit()

    def total_relief(self, relief_key):
        val = self.conn.execute(
            "SELECT COALESCE(SUM(amount), 0) FROM relief_entries WHERE relief_key = ?",
            (relief_key,)
        ).fetchone()[0]
        return float(val)

    # ── App settings ──────────────────────────────────────────────────────────

    def get_setting(self, key, default=""):
        row = self.conn.execute(
            "SELECT value FROM settings WHERE key = ?", (key,)
        ).fetchone()
        return row["value"] if row else default

    def set_setting(self, key, value):
        self.conn.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
            (key, str(value))
        )
        self.conn.commit()
