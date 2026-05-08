import io
import os
import zipfile
import tempfile

import pytest

openpyxl = pytest.importorskip("openpyxl")


class TestExportStructure:
    def test_income_sheet_created(self, db, sample_income):
        from export import _income_sheet
        wb = openpyxl.Workbook()
        wb.remove(wb.active)
        _income_sheet(wb, db)
        assert "Income" in wb.sheetnames
        ws = wb["Income"]
        assert ws.cell(row=1, column=1).value == "#"
        assert ws.cell(row=2, column=3).value == "Monthly Salary Jan"

    def test_expenses_sheet_created(self, db, sample_expenses):
        from export import _expenses_sheet
        wb = openpyxl.Workbook()
        wb.remove(wb.active)
        _expenses_sheet(wb, db)
        assert "Expenses" in wb.sheetnames

    def test_reliefs_sheet_created(self, db, sample_reliefs):
        from export import _reliefs_sheet
        wb = openpyxl.Workbook()
        wb.remove(wb.active)
        _reliefs_sheet(wb, db)
        assert "Tax Reliefs" in wb.sheetnames

    def test_tax_summary_sheet_created(self, db, sample_income, sample_expenses, sample_reliefs):
        from export import _tax_summary_sheet
        wb = openpyxl.Workbook()
        wb.remove(wb.active)
        _tax_summary_sheet(wb, db, total_relief=10000)
        assert "Tax Summary" in wb.sheetnames

    def test_income_summary_row_has_marker(self, db, sample_income):
        from export import _income_sheet
        wb = openpyxl.Workbook()
        wb.remove(wb.active)
        _income_sheet(wb, db)
        ws = wb["Income"]
        last_row = ws.max_row
        assert ws.cell(row=last_row, column=1).value == "__SUMMARY__"

    def test_expenses_summary_row_has_marker(self, db, sample_expenses):
        from export import _expenses_sheet
        wb = openpyxl.Workbook()
        wb.remove(wb.active)
        _expenses_sheet(wb, db)
        ws = wb["Expenses"]
        last_row = ws.max_row
        assert ws.cell(row=last_row, column=1).value == "__SUMMARY__"

    def test_zip_export_creates_valid_archive(self, db, sample_income):
        from export import export_to_zip
        with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as f:
            zip_path = f.name
        try:
            import tkinter as tk
            root = tk.Tk()
            root.withdraw()
            with pytest.MonkeyPatch().context() as mp:
                mp.setattr("tkinter.filedialog.asksaveasfilename",
                           lambda **kw: zip_path)
                export_to_zip(db)
            assert os.path.exists(zip_path)
            with zipfile.ZipFile(zip_path, "r") as zf:
                names = zf.namelist()
                assert any(n.endswith(".xlsx") for n in names)
            root.destroy()
        finally:
            try:
                os.unlink(zip_path)
            except OSError:
                pass


class TestExportWithReceipts:
    def test_income_sheet_with_receipt_column(self, db, sample_income):
        from export import _income_sheet
        wb = openpyxl.Workbook()
        wb.remove(wb.active)
        _income_sheet(wb, db, with_receipts=True)
        ws = wb["Income"]
        headers = [ws.cell(row=1, column=c).value for c in range(1, 8)]
        assert "Receipt File" in headers
