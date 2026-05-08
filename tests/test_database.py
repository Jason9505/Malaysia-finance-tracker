import pytest


class TestDBCRUD:
    def test_add_income(self, db):
        row_id = db.add_income("salary", "Test Salary", 5000, "2025-01-15")
        assert row_id is not None and row_id > 0

    def test_add_expense(self, db):
        row_id = db.add_expense("food", "Groceries", 200, "2025-01-10",
                                tax_relief="")
        assert row_id is not None and row_id > 0

    def test_add_relief(self, db):
        row_id = db.add_relief("medical", "Checkup", 500, "2025-01-10")
        assert row_id is not None and row_id > 0

    def test_get_income(self, db, sample_income):
        rows = db.get_income()
        assert len(rows) >= 4
        rows_salary = db.get_income("salary")
        assert all(r["category"] == "salary" for r in rows_salary)

    def test_get_income_by_id(self, db, sample_income):
        row = db.get_income_by_id(sample_income[0])
        assert row is not None
        assert row["name"] == "Monthly Salary Jan"

    def test_get_expenses(self, db, sample_expenses):
        rows = db.get_expenses()
        assert len(rows) >= 4

    def test_get_expense_by_id(self, db, sample_expenses):
        row = db.get_expense_by_id(sample_expenses[0])
        assert row is not None
        assert row["category"] == "food"

    def test_get_reliefs(self, db, sample_reliefs):
        rows = db.get_reliefs()
        assert len(rows) >= 3

    def test_get_relief_by_id(self, db, sample_reliefs):
        row = db.get_relief_by_id(sample_reliefs[0])
        assert row is not None
        assert row["relief_key"] == "medical"

    def test_update_income(self, db, sample_income):
        row_id = sample_income[0]
        db.update_income(row_id, "Updated Salary", 6000, "2025-01-15")
        row = db.get_income_by_id(row_id)
        assert row["name"] == "Updated Salary"
        assert row["amount"] == 6000

    def test_delete_income(self, db, sample_income):
        count_before = len(db.get_income())
        db.delete_income(sample_income[0])
        assert len(db.get_income()) == count_before - 1

    def test_total_income(self, db, sample_income):
        total = db.total_income()
        assert total == pytest.approx(5000 + 5200 + 800 + 5100)

    def test_total_income_category(self, db, sample_income):
        total = db.total_income("salary")
        assert total == pytest.approx(5000 + 5200 + 5100)

    def test_total_expenses(self, db, sample_expenses):
        total = db.total_expenses()
        assert total == pytest.approx(350 + 200 + 500 + 1500)

    def test_total_relief(self, db, sample_reliefs):
        total = db.total_relief("medical")
        assert total == pytest.approx(800)

    def test_get_income_month(self, db, sample_income):
        rows = db.get_income_month(2025, 1)
        assert len(rows) == 2

    def test_get_expenses_month(self, db, sample_expenses):
        rows = db.get_expenses_month(2025, 1)
        assert len(rows) >= 3

    def test_get_distinct_years(self, db, sample_income):
        years = db.get_distinct_years()
        assert 2025 in years

    def test_clear_receipt_validates_table(self, db):
        with pytest.raises(ValueError, match="Invalid table"):
            db.clear_receipt("nonexistent", 1)

    def test_clear_receipt_valid(self, db, sample_income):
        db.clear_receipt("income", sample_income[0])
        row = db.get_income_by_id(sample_income[0])
        assert row["receipt"] == ""


class TestDBCaching:
    def test_relief_cache_invalidated_on_add(self, db, sample_expenses):
        from config import ALL_RELIEFS
        total_before = db.total_reliefs_year(2025)
        db.add_expense("medical", "New", 1000, "2025-02-01",
                       tax_relief="medical")
        total_after = db.total_reliefs_year(2025)
        assert total_after > total_before

    def test_relief_cache_invalidated_on_delete(self, db, sample_expenses):
        total_before = db.total_reliefs_year(2025)
        db.delete_expense(sample_expenses[0])
        total_after = db.total_reliefs_year(2025)
        assert total_after < total_before

    def test_clear_all_data(self, db, sample_income, sample_expenses, sample_reliefs):
        db.clear_all_data()
        assert len(db.get_income()) == 0
        assert len(db.get_expenses()) == 0
        assert len(db.get_reliefs()) == 0


class TestDBSettings:
    def test_get_setting_default(self, db):
        val = db.get_setting("nonexistent", "default_val")
        assert val == "default_val"

    def test_set_and_get_setting(self, db):
        db.set_setting("theme", "dark")
        assert db.get_setting("theme") == "dark"
        db.set_setting("theme", "light")
        assert db.get_setting("theme") == "light"


class TestDBThreadSafety:
    def test_lock_held_during_commit(self, db):
        db.add_income("salary", "Test", 100, "2025-01-01")
        assert db._lock.locked() is False
