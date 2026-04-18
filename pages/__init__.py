# pages/__init__.py
# FIX (Code): sys.path manipulation lives HERE only — not duplicated in every page file.
import sys
import os

_PAGES_DIR   = os.path.dirname(os.path.abspath(__file__))
_PROJECT_DIR = os.path.dirname(_PAGES_DIR)
for _p in (_PROJECT_DIR, _PAGES_DIR):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from pages.dashboard import DashboardPage
from pages.income    import IncomePage
from pages.expenses  import ExpensesPage
from pages.tax       import TaxPage
from pages.settings  import SettingsPage

__all__ = ["DashboardPage", "IncomePage", "ExpensesPage", "TaxPage", "SettingsPage"]