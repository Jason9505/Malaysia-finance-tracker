import os
import sys
import tempfile

import pytest

_SRC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _SRC)

@pytest.fixture
def db():
    """Create an in-memory database for testing."""
    import config as _cfg
    from database import DB

    orig_path = _cfg.DB_PATH
    _cfg.DB_PATH = ":memory:"

    instance = DB()

    yield instance

    instance.conn.close()
    _cfg.DB_PATH = orig_path


@pytest.fixture
def sample_income(db):
    """Add sample income rows and return their IDs."""
    ids = []
    ids.append(db.add_income("salary", "Monthly Salary Jan", 5000, "2025-01-15"))
    ids.append(db.add_income("salary", "Monthly Salary Feb", 5200, "2025-02-15"))
    ids.append(db.add_income("allowance", "Travel Allowance", 800, "2025-01-20"))
    ids.append(db.add_income("salary", "Monthly Salary Mar", 5100, "2025-03-15"))
    return ids


@pytest.fixture
def sample_expenses(db):
    """Add sample expense rows and return their IDs."""
    ids = []
    ids.append(db.add_expense("food", "Groceries", 350, "2025-01-10",
                              tax_relief=""))
    ids.append(db.add_expense("medical", "Doctor Visit", 200, "2025-01-12",
                              tax_relief="medical"))
    ids.append(db.add_expense("epf", "EPF Contribution", 500, "2025-01-15",
                              tax_relief="epf"))
    ids.append(db.add_expense("housing", "Monthly Rent", 1500, "2025-01-05",
                              tax_relief="housing_interest"))
    return ids


@pytest.fixture
def sample_reliefs(db):
    """Add sample manual relief entries and return their IDs."""
    ids = []
    ids.append(db.add_relief("medical", "Medical Checkup", 800,
                             "2025-02-01", "Annual checkup"))
    ids.append(db.add_relief("lifestyle", "Books", 300,
                             "2025-02-10", "Programming books"))
    ids.append(db.add_relief("sspn", "SSPN Deposit", 2000,
                             "2025-03-01", "Child education savings"))
    return ids
