# database.py
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
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            category   TEXT    NOT NULL,
            name       TEXT    NOT NULL,
            amount     REAL    NOT NULL,
            date       TEXT    NOT NULL,
            notes      TEXT    DEFAULT '',
            receipt    TEXT    DEFAULT '',
            created_at TEXT    DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS expenses (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            category   TEXT    NOT NULL,
            name       TEXT    NOT NULL,
            amount     REAL    NOT NULL,
            date       TEXT    NOT NULL,
            notes      TEXT    DEFAULT '',
            receipt    TEXT    DEFAULT '',
            tax_relief TEXT    DEFAULT '',
            created_at TEXT    DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS relief_entries (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            relief_key TEXT    NOT NULL,
            name       TEXT    NOT NULL,
            amount     REAL    NOT NULL,
            date       TEXT    NOT NULL,
            notes      TEXT    DEFAULT '',
            receipt    TEXT    DEFAULT '',
            created_at TEXT    DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS settings (
            key   TEXT PRIMARY KEY,
            value TEXT
        );
        """)

        # FIX (Perf): Add indexes on columns used in WHERE/ORDER BY clauses.
        # CREATE INDEX IF NOT EXISTS is idempotent — safe to call every startup.
        self.conn.executescript("""
        CREATE INDEX IF NOT EXISTS idx_income_date     ON income (date);
        CREATE INDEX IF NOT EXISTS idx_income_category ON income (category);
        CREATE INDEX IF NOT EXISTS idx_expenses_date       ON expenses (date);
        CREATE INDEX IF NOT EXISTS idx_expenses_category   ON expenses (category);
        CREATE INDEX IF NOT EXISTS idx_expenses_tax_relief ON expenses (tax_relief);
        CREATE INDEX IF NOT EXISTS idx_relief_key  ON relief_entries (relief_key);
        CREATE INDEX IF NOT EXISTS idx_relief_date ON relief_entries (date);
        """)
        self.conn.commit()

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _where(self, conditions, params):
        if conditions:
            return "WHERE " + " AND ".join(conditions), params
        return "", params

    # ── Income ────────────────────────────────────────────────────────────────

    def add_income(self, category, name, amount, date, notes="", receipt=""):
        cur = self.conn.execute(
            "INSERT INTO income (category,name,amount,date,notes,receipt) "
            "VALUES (?,?,?,?,?,?)",
            (category, name, amount, date, notes, receipt))
        self.conn.commit()
        return cur.lastrowid

    def update_income(self, row_id, name, amount, date, notes="", receipt=""):
        self.conn.execute(
            "UPDATE income SET name=?,amount=?,date=?,notes=?,receipt=? WHERE id=?",
            (name, amount, date, notes, receipt, row_id))
        self.conn.commit()

    def get_income(self, category=None):
        if category:
            return self.conn.execute(
                "SELECT * FROM income WHERE category=? ORDER BY date DESC",
                (category,)).fetchall()
        return self.conn.execute(
            "SELECT * FROM income ORDER BY date DESC").fetchall()

    def get_income_by_id(self, row_id):
        return self.conn.execute(
            "SELECT * FROM income WHERE id=?", (row_id,)).fetchone()

    def delete_income(self, row_id):
        row = self.get_income_by_id(row_id)
        if row and row["receipt"] and os.path.exists(row["receipt"]):
            try:
                os.remove(row["receipt"])
            except OSError:
                pass
        self.conn.execute("DELETE FROM income WHERE id=?", (row_id,))
        self.conn.commit()

    def total_income(self, category=None):
        if category:
            val = self.conn.execute(
                "SELECT COALESCE(SUM(amount),0) FROM income WHERE category=?",
                (category,)).fetchone()[0]
        else:
            val = self.conn.execute(
                "SELECT COALESCE(SUM(amount),0) FROM income").fetchone()[0]
        return float(val)

    def total_income_period(self, category=None, year=None, month=None):
        conds, params = [], []
        if category:
            conds.append("category=?");   params.append(category)
        if year and month:
            conds.append("date LIKE ?");  params.append(f"{year}-{month:02d}-%")
        elif year:
            conds.append("date LIKE ?");  params.append(f"{year}-%")
        where, params = self._where(conds, params)
        val = self.conn.execute(
            f"SELECT COALESCE(SUM(amount),0) FROM income {where}",
            params).fetchone()[0]
        return float(val)

    # FIX (Perf): SQL-filtered income for a date prefix — used by dashboard charts.
    def get_income_month(self, year, month):
        """Return all income rows for the given year+month via SQL filtering."""
        prefix = f"{year}-{month:02d}-%"
        return self.conn.execute(
            "SELECT * FROM income WHERE date LIKE ? ORDER BY date DESC",
            (prefix,)).fetchall()

    # FIX (Bug): Wrapped method so pages never call db.conn directly.
    def get_distinct_years(self):
        """Return sorted list (newest first) of years with any data."""
        years = set()
        for table in ("income", "expenses", "relief_entries"):
            rows = self.conn.execute(
                f"SELECT DISTINCT substr(date,1,4) AS yr "
                f"FROM {table} WHERE date != ''"
            ).fetchall()
            for row in rows:
                try:
                    years.add(int(row[0]))
                except (ValueError, TypeError):
                    pass
        if not years:
            from datetime import date
            years.add(date.today().year)
        return sorted(years, reverse=True)

    # FIX (Bug): Wrapped method for expense month-year combos used by dashboard.
    def get_expense_month_years(self):
        """Return list of 'YYYY-MM' strings (newest first) that have expenses."""
        rows = self.conn.execute(
            "SELECT DISTINCT substr(date,1,7) AS ym FROM expenses "
            "WHERE date != '' ORDER BY ym DESC"
        ).fetchall()
        return [row[0] for row in rows if row[0]]

    # ── Expenses ──────────────────────────────────────────────────────────────

    def add_expense(self, category, name, amount, date,
                    notes="", receipt="", tax_relief=""):
        cur = self.conn.execute(
            "INSERT INTO expenses (category,name,amount,date,notes,receipt,tax_relief) "
            "VALUES (?,?,?,?,?,?,?)",
            (category, name, amount, date, notes, receipt, tax_relief))
        self.conn.commit()
        return cur.lastrowid

    def update_expense(self, row_id, name, amount, date,
                       notes="", receipt="", tax_relief=""):
        self.conn.execute(
            "UPDATE expenses SET name=?,amount=?,date=?,notes=?,receipt=?,tax_relief=? "
            "WHERE id=?",
            (name, amount, date, notes, receipt, tax_relief, row_id))
        self.conn.commit()

    def get_expenses(self, category=None):
        if category:
            return self.conn.execute(
                "SELECT * FROM expenses WHERE category=? ORDER BY date DESC",
                (category,)).fetchall()
        return self.conn.execute(
            "SELECT * FROM expenses ORDER BY date DESC").fetchall()

    def get_expense_by_id(self, row_id):
        return self.conn.execute(
            "SELECT * FROM expenses WHERE id=?", (row_id,)).fetchone()

    def delete_expense(self, row_id):
        row = self.get_expense_by_id(row_id)
        if row and row["receipt"] and os.path.exists(row["receipt"]):
            try:
                os.remove(row["receipt"])
            except OSError:
                pass
        self.conn.execute("DELETE FROM expenses WHERE id=?", (row_id,))
        self.conn.commit()

    def total_expenses(self, category=None):
        if category:
            val = self.conn.execute(
                "SELECT COALESCE(SUM(amount),0) FROM expenses WHERE category=?",
                (category,)).fetchone()[0]
        else:
            val = self.conn.execute(
                "SELECT COALESCE(SUM(amount),0) FROM expenses").fetchone()[0]
        return float(val)

    def total_expenses_period(self, category=None, year=None, month=None):
        conds, params = [], []
        if category:
            conds.append("category=?");   params.append(category)
        if year and month:
            conds.append("date LIKE ?");  params.append(f"{year}-{month:02d}-%")
        elif year:
            conds.append("date LIKE ?");  params.append(f"{year}-%")
        where, params = self._where(conds, params)
        val = self.conn.execute(
            f"SELECT COALESCE(SUM(amount),0) FROM expenses {where}",
            params).fetchone()[0]
        return float(val)

    # FIX (Perf): SQL-filtered expenses for a date prefix — used by dashboard charts.
    def get_expenses_month(self, year, month):
        """Return all expense rows for the given year+month via SQL filtering."""
        prefix = f"{year}-{month:02d}-%"
        return self.conn.execute(
            "SELECT * FROM expenses WHERE date LIKE ? ORDER BY date DESC",
            (prefix,)).fetchall()

    def tax_deductible_by_relief(self):
        rows = self.conn.execute(
            "SELECT tax_relief, COALESCE(SUM(amount),0) AS s "
            "FROM expenses WHERE tax_relief != '' GROUP BY tax_relief"
        ).fetchall()
        return {r["tax_relief"]: float(r["s"]) for r in rows}

    def tax_deductible_by_relief_year(self, year=None):
        if year:
            rows = self.conn.execute(
                "SELECT tax_relief, COALESCE(SUM(amount),0) AS s FROM expenses "
                "WHERE tax_relief != '' AND date LIKE ? GROUP BY tax_relief",
                (f"{year}-%",)).fetchall()
        else:
            rows = self.conn.execute(
                "SELECT tax_relief, COALESCE(SUM(amount),0) AS s "
                "FROM expenses WHERE tax_relief != '' GROUP BY tax_relief"
            ).fetchall()
        return {r["tax_relief"]: float(r["s"]) for r in rows}

    # ── Relief entries ────────────────────────────────────────────────────────

    def add_relief(self, relief_key, name, amount, date, notes="", receipt=""):
        cur = self.conn.execute(
            "INSERT INTO relief_entries (relief_key,name,amount,date,notes,receipt) "
            "VALUES (?,?,?,?,?,?)",
            (relief_key, name, amount, date, notes, receipt))
        self.conn.commit()
        return cur.lastrowid

    def update_relief(self, row_id, name, amount, date, notes="", receipt=""):
        self.conn.execute(
            "UPDATE relief_entries SET name=?,amount=?,date=?,notes=?,receipt=? "
            "WHERE id=?",
            (name, amount, date, notes, receipt, row_id))
        self.conn.commit()

    def get_reliefs(self, relief_key=None):
        if relief_key:
            return self.conn.execute(
                "SELECT * FROM relief_entries WHERE relief_key=? ORDER BY date DESC",
                (relief_key,)).fetchall()
        return self.conn.execute(
            "SELECT * FROM relief_entries ORDER BY date DESC").fetchall()

    def get_reliefs_year(self, relief_key=None, year=None):
        conds, params = [], []
        if relief_key:
            conds.append("relief_key=?"); params.append(relief_key)
        if year:
            conds.append("date LIKE ?");  params.append(f"{year}-%")
        where, params = self._where(conds, params)
        return self.conn.execute(
            f"SELECT * FROM relief_entries {where} ORDER BY date DESC",
            params).fetchall()

    def get_relief_by_id(self, row_id):
        return self.conn.execute(
            "SELECT * FROM relief_entries WHERE id=?", (row_id,)).fetchone()

    def delete_relief(self, row_id):
        row = self.get_relief_by_id(row_id)
        if row and row["receipt"] and os.path.exists(row["receipt"]):
            try:
                os.remove(row["receipt"])
            except OSError:
                pass
        self.conn.execute("DELETE FROM relief_entries WHERE id=?", (row_id,))
        self.conn.commit()

    def total_relief(self, relief_key):
        val = self.conn.execute(
            "SELECT COALESCE(SUM(amount),0) FROM relief_entries WHERE relief_key=?",
            (relief_key,)).fetchone()[0]
        return float(val)

    # FIX (Bug): Compute total reliefs for a year via SQL — used by dashboard.
    def total_reliefs_year(self, year=None):
        """
        Sum all claimed reliefs (auto + manual) for the given year, capped per
        relief category.  Returns a single float ready for tax computation.
        """
        from config import ALL_RELIEFS
        auto_map = self.tax_deductible_by_relief_year(year=year)
        manual_rows = self.get_reliefs_year(year=year)
        manual_by_key = {}
        for row in manual_rows:
            manual_by_key.setdefault(row["relief_key"], []).append(row)
        total = 0.0
        for key, _name, max_rm in ALL_RELIEFS:
            auto_amt   = auto_map.get(key, 0.0)
            manual_amt = sum(r["amount"] for r in manual_by_key.get(key, []))
            total += min(auto_amt + manual_amt, max_rm)
        return total

    def clear_receipt(self, table, row_id):
        """Wipe a broken receipt path without deleting the entry."""
        if table in ("income", "expenses", "relief_entries"):
            self.conn.execute(
                f"UPDATE {table} SET receipt='' WHERE id=?", (row_id,))
            self.conn.commit()

    # ── Settings ──────────────────────────────────────────────────────────────

    def get_setting(self, key, default=""):
        row = self.conn.execute(
            "SELECT value FROM settings WHERE key=?", (key,)).fetchone()
        return row["value"] if row else default

    def set_setting(self, key, value):
        self.conn.execute(
            "INSERT OR REPLACE INTO settings (key,value) VALUES (?,?)",
            (key, str(value)))
        self.conn.commit()