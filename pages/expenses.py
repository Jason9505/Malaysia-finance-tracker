# pages/expenses.py
# Expenses page: per-category sections — add, edit, delete, receipt, sort.

import sys, os
_PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_DIR not in sys.path:
    sys.path.insert(0, _PROJECT_DIR)

import tkinter as tk
from tkinter import ttk, messagebox

from config  import (C_BG, C_CARD, C_TEXT, C_TEXT_MED, C_TEXT_LT,
                     C_SUCCESS, C_DANGER, C_WARNING, C_BORDER,
                     C_PRIMARY, C_PRIMARY_LT, EXPENSE_CATS)
from utils   import fmt_rm
from widgets import (Card, ScrollFrame, AddEntryDialog,
                     ViewReceiptDialog, make_button, add_column_sorting)


class ExpensesPage(ScrollFrame):

    def __init__(self, parent, db):
        super().__init__(parent)
        self.db = db
        self._trees  = {}
        self._totals = {}
        self._build()

    # ── Build ─────────────────────────────────────────────────────────────────

    def _build(self):
        inner = self.inner
        tk.Label(inner, text="My Expenses",
                 font=("Segoe UI", 20, "bold"), bg=C_BG, fg=C_TEXT
                 ).pack(anchor="w", padx=28, pady=(24, 0))

        self._summary_lbl = tk.Label(
            inner, text="", font=("Segoe UI", 11),
            bg="#fff7ed", fg=C_WARNING, pady=8)
        self._summary_lbl.pack(fill="x", padx=28, pady=(8, 0))

        for cat_key, (cat_label, tax_ded, _rk) in EXPENSE_CATS.items():
            self._build_section(inner, cat_key, cat_label, tax_ded)

        self.refresh()

    def _build_section(self, parent, cat_key, cat_label, tax_deductible):
        hdr = tk.Frame(parent, bg=C_BG)
        hdr.pack(fill="x", padx=28, pady=(20, 6))

        tk.Label(hdr, text=cat_label,
                 font=("Segoe UI", 12, "bold"), bg=C_BG, fg=C_TEXT).pack(side="left")
        if tax_deductible:
            tk.Label(hdr, text="  🟢 Tax Deductible",
                     font=("Segoe UI", 8), bg=C_BG, fg=C_SUCCESS).pack(side="left", padx=4)

        total_lbl = tk.Label(hdr, text="RM 0.00",
                             font=("Segoe UI", 11, "bold"), bg=C_BG, fg=C_DANGER)
        total_lbl.pack(side="right", padx=(0, 8))
        self._totals[cat_key] = total_lbl

        make_button(hdr, "＋ Add",
                    command=lambda k=cat_key, l=cat_label, td=tax_deductible:
                        self._open_add(k, l, td),
                    font=("Segoe UI", 9, "bold"), pady=4, padx=10
                    ).pack(side="right")

        card = Card(parent, padx=0, pady=0,
                    highlightbackground=C_BORDER, highlightthickness=1)
        card.pack(fill="x", padx=28, pady=(0, 4))

        tree = self._make_tree(card)
        tree.pack(fill="x")
        self._trees[cat_key] = tree

        add_column_sorting(tree, numeric_cols=["amount"])

        bar = tk.Frame(card, bg=C_CARD, pady=6, padx=12)
        bar.pack(fill="x")

        make_button(bar, "✏  Edit Selected",
                    command=lambda t=tree, k=cat_key, td=tax_deductible:
                        self._open_edit(t, k, td),
                    bg=C_PRIMARY_LT, fg=C_PRIMARY,
                    font=("Segoe UI", 9), pady=3, padx=8
                    ).pack(side="left")

        make_button(bar, "🗑  Delete",
                    command=lambda t=tree: self._delete(t),
                    bg="#fff1f2", fg=C_DANGER,
                    font=("Segoe UI", 9), pady=3, padx=8
                    ).pack(side="left", padx=4)

        make_button(bar, "📎  View Receipt",
                    command=lambda t=tree: self._view_receipt(t),
                    bg=C_BG, fg=C_TEXT,
                    font=("Segoe UI", 9), pady=3, padx=8
                    ).pack(side="left")

    @staticmethod
    def _make_tree(parent):
        cols = [
            ("name",    "Name",    240, "w",      True),
            ("amount",  "Amount",  130, "e",      False),
            ("date",    "Date",    110, "center", False),
            ("notes",   "Notes",   200, "w",      True),
            ("receipt", "Receipt",  80, "center", False),
        ]
        tree = ttk.Treeview(parent,
                            columns=[c[0] for c in cols] + ["_id"],
                            show="headings", height=4, selectmode="browse")
        for col_id, display, width, anchor, stretch in cols:
            tree.heading(col_id, text=display)
            tree.column(col_id, width=width, anchor=anchor,
                        stretch=stretch, minwidth=60)
        tree.heading("_id", text="")
        tree.column("_id", width=0, stretch=False, minwidth=0)
        tree.tag_configure("broken", foreground=C_WARNING)
        return tree

    # ── Add ───────────────────────────────────────────────────────────────────

    def _open_add(self, cat_key, cat_label, tax_deductible):
        _, _, relief_key = EXPENSE_CATS[cat_key]

        def on_save(name, amount, dt, notes, receipt):
            self.db.add_expense(cat_key, name, amount, dt, notes, receipt,
                                tax_relief=relief_key if tax_deductible else "")
            self.refresh()
            self._notify()

        AddEntryDialog(self, f"Add {cat_label} Expense", on_save=on_save)

    # ── Edit ──────────────────────────────────────────────────────────────────

    def _open_edit(self, tree, cat_key, tax_deductible):
        sel = tree.focus()
        if not sel:
            messagebox.showinfo("Select Row",
                                "Please select an entry to edit.", parent=self)
            return
        row_id = int(tree.item(sel, "values")[-1])
        row    = self.db.get_expense_by_id(row_id)
        if not row:
            return

        _, _, relief_key = EXPENSE_CATS[cat_key]
        prefill = {
            "name":    row["name"],
            "amount":  row["amount"],
            "date":    row["date"],
            "notes":   row["notes"] or "",
            "receipt": row["receipt"] or "",
        }

        def on_save(name, amount, dt, notes, receipt):
            self.db.update_expense(row_id, name, amount, dt, notes, receipt,
                                   tax_relief=relief_key if tax_deductible else "")
            self.refresh()
            self._notify()

        cat_label = EXPENSE_CATS[cat_key][0]
        AddEntryDialog(self, f"Edit {cat_label}", on_save=on_save, prefill=prefill)

    # ── Delete ────────────────────────────────────────────────────────────────

    def _delete(self, tree):
        sel = tree.focus()
        if not sel:
            messagebox.showinfo("Select Row",
                                "Please select an entry to delete.", parent=self)
            return
        vals   = tree.item(sel, "values")
        row_id = int(vals[-1])
        if messagebox.askyesno("Confirm Delete", f"Delete '{vals[0]}'?", parent=self):
            self.db.delete_expense(row_id)
            self.refresh()
            self._notify()

    # ── View receipt ──────────────────────────────────────────────────────────

    def _view_receipt(self, tree):
        sel = tree.focus()
        if not sel:
            return
        row_id = int(tree.item(sel, "values")[-1])
        row    = self.db.get_expense_by_id(row_id)
        if not row or not row["receipt"]:
            messagebox.showinfo("No Receipt",
                                "No receipt attached to this entry.", parent=self)
            return
        if not os.path.exists(row["receipt"]):
            if messagebox.askyesno(
                    "Receipt Missing",
                    "The receipt file no longer exists on disk.\n\n"
                    "Remove the broken link from this entry?",
                    parent=self):
                self.db.clear_receipt("expenses", row_id)
                self.refresh()
            return
        ViewReceiptDialog(self, row["receipt"], f"Receipt – {row['name']}")

    # ── Refresh ───────────────────────────────────────────────────────────────

    def refresh(self):
        total_all        = 0.0
        total_deductible = 0.0

        for cat_key, tree in self._trees.items():
            for item in tree.get_children():
                tree.delete(item)

            for row in self.db.get_expenses(cat_key):
                receipt_path = row["receipt"] or ""
                if receipt_path and os.path.exists(receipt_path):
                    badge = "📎"
                    tag   = ""
                elif receipt_path:
                    badge = "⚠ missing"
                    tag   = "broken"
                else:
                    badge = ""
                    tag   = ""

                tree.insert("", "end", tags=(tag,), values=(
                    row["name"],
                    fmt_rm(row["amount"]),
                    row["date"],
                    row["notes"] or "",
                    badge,
                    row["id"],
                ))

            total = self.db.total_expenses(cat_key)
            total_all += total
            if EXPENSE_CATS[cat_key][1]:
                total_deductible += total
            self._totals[cat_key].config(text=fmt_rm(total))

        self._summary_lbl.config(
            text=f"  Total Expenses: {fmt_rm(total_all)}"
                 f"   |   Tax Deductible: {fmt_rm(total_deductible)}")

    # ── Notify ────────────────────────────────────────────────────────────────

    def _notify(self):
        root = self.winfo_toplevel()
        if hasattr(root, "refresh_page"):
            for key in ("dashboard", "tax"):
                root.refresh_page(key)