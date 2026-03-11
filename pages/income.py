# ─── pages/income.py ─────────────────────────────────────────────────────────
# Income page: Salary and Allowances sections with add / delete / view receipt.

import sys, os as _os
_PROJECT_DIR = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
if _PROJECT_DIR not in sys.path:
    sys.path.insert(0, _PROJECT_DIR)


import tkinter as tk
from tkinter import ttk, messagebox

from config  import C_BG, C_CARD, C_TEXT, C_TEXT_MED, C_TEXT_LT, C_SUCCESS, C_DANGER, C_BORDER, C_PRIMARY, C_PRIMARY_LT
from utils   import fmt_rm
from widgets import Card, ScrollFrame, AddEntryDialog, ViewReceiptDialog, make_button

# Income categories displayed as separate sections
INCOME_SECTIONS = [
    ("salary",    "Salary",      "💵"),
    ("allowance", "Allowances",  "🎁"),
]


class IncomePage(ScrollFrame):
    """
    Income tracking page with two sections:
      • Salary  – regular employment income
      • Allowances  – bonuses, claims, other allowances
    """

    def __init__(self, parent, db):
        super().__init__(parent)
        self.db = db
        self._trees  = {}   # cat_key -> Treeview
        self._totals = {}   # cat_key -> Label
        self._build()

    # ── Build ─────────────────────────────────────────────────────────────────

    def _build(self):
        inner = self.inner

        # Page title
        tk.Label(inner, text="My Income",
                 font=("Segoe UI", 20, "bold"), bg=C_BG, fg=C_TEXT
                 ).pack(anchor="w", padx=28, pady=(24, 0))

        # Summary banner
        self._summary_lbl = tk.Label(
            inner, text="", font=("Segoe UI", 11),
            bg=C_PRIMARY_LT, fg=C_PRIMARY, pady=8
        )
        self._summary_lbl.pack(fill="x", padx=28, pady=(8, 0))

        # One section per income category
        for cat_key, label, icon in INCOME_SECTIONS:
            self._build_section(inner, cat_key, label, icon)

        self.refresh()

    def _build_section(self, parent, cat_key, label, icon):
        # ── Section header row ─────────────────────────
        hdr = tk.Frame(parent, bg=C_BG)
        hdr.pack(fill="x", padx=28, pady=(20, 6))

        tk.Label(hdr, text=f"{icon}  {label}",
                 font=("Segoe UI", 13, "bold"), bg=C_BG, fg=C_TEXT).pack(side="left")

        total_lbl = tk.Label(hdr, text="RM 0.00",
                             font=("Segoe UI", 11, "bold"), bg=C_BG, fg=C_SUCCESS)
        total_lbl.pack(side="right", padx=(0, 8))
        self._totals[cat_key] = total_lbl

        make_button(
            hdr, "＋ Add",
            command=lambda k=cat_key, l=label: self._open_add_dialog(k, l),
            font=("Segoe UI", 9, "bold"), pady=4, padx=10
        ).pack(side="right")

        # ── Card with treeview ─────────────────────────
        card = Card(parent, padx=0, pady=0,
                    highlightbackground=C_BORDER, highlightthickness=1)
        card.pack(fill="x", padx=28, pady=(0, 4))

        tree = self._make_tree(card)
        tree.pack(fill="x")
        self._trees[cat_key] = tree

        # ── Action bar ────────────────────────────────
        bar = tk.Frame(card, bg=C_CARD, pady=6, padx=12)
        bar.pack(fill="x")

        make_button(
            bar, "🗑  Delete Selected",
            command=lambda t=tree, k=cat_key: self._delete_entry(t, k),
            bg="#fff1f2", fg=C_DANGER, font=("Segoe UI", 9), pady=3, padx=8
        ).pack(side="left")

        make_button(
            bar, "📎  View Receipt",
            command=lambda t=tree: self._view_receipt(t),
            bg=C_BG, fg=C_TEXT, font=("Segoe UI", 9), pady=3, padx=8
        ).pack(side="left", padx=4)

    @staticmethod
    def _make_tree(parent):
        cols = [
            ("name",    "Name",    240, "w",      True),
            ("amount",  "Amount",  130, "e",      False),
            ("date",    "Date",    110, "center",  False),
            ("notes",   "Notes",   200, "w",      True),
            ("receipt", "Receipt",  80, "center",  False),
        ]
        tree = ttk.Treeview(
            parent,
            columns=[c[0] for c in cols] + ["_id"],
            show="headings", height=5, selectmode="browse"
        )
        for col_id, display, width, anchor, stretch in cols:
            tree.heading(col_id, text=display)
            tree.column(col_id, width=width, anchor=anchor,
                        stretch=stretch, minwidth=60)
        tree.heading("_id", text="")
        tree.column("_id", width=0, stretch=False, minwidth=0)
        return tree

    # ── Dialogs ───────────────────────────────────────────────────────────────

    def _open_add_dialog(self, cat_key, label):
        def on_save(name, amount, dt, notes, receipt):
            self.db.add_income(cat_key, name, amount, dt, notes, receipt)
            self.refresh()
            self._notify_other_pages()

        AddEntryDialog(self, f"Add {label}", on_save=on_save)

    def _delete_entry(self, tree, cat_key):
        sel = tree.focus()
        if not sel:
            messagebox.showinfo("Select Row", "Please select an entry to delete.", parent=self)
            return
        vals = tree.item(sel, "values")
        row_id = int(vals[-1])
        if messagebox.askyesno("Confirm Delete", f"Delete '{vals[0]}'?", parent=self):
            self.db.delete_income(row_id)
            self.refresh()
            self._notify_other_pages()

    def _view_receipt(self, tree):
        sel = tree.focus()
        if not sel:
            return
        row_id = int(tree.item(sel, "values")[-1])
        row = self.db.get_income_by_id(row_id)
        import os
        if row and row["receipt"] and os.path.exists(row["receipt"]):
            ViewReceiptDialog(self, row["receipt"], f"Receipt – {row['name']}")
        else:
            messagebox.showinfo("No Receipt", "No receipt attached to this entry.", parent=self)

    # ── Refresh ───────────────────────────────────────────────────────────────

    def refresh(self):
        import os
        for cat_key, tree in self._trees.items():
            # Clear
            for item in tree.get_children():
                tree.delete(item)
            # Populate
            for row in self.db.get_income(cat_key):
                has_receipt = "📎" if row["receipt"] and os.path.exists(row["receipt"]) else ""
                tree.insert("", "end", values=(
                    row["name"],
                    fmt_rm(row["amount"]),
                    row["date"],
                    row["notes"] or "",
                    has_receipt,
                    row["id"],
                ))
            # Update section total
            total = self.db.total_income(cat_key)
            self._totals[cat_key].config(text=fmt_rm(total))

        # Update summary banner
        sal = self.db.total_income("salary")
        alw = self.db.total_income("allowance")
        tot = sal + alw
        self._summary_lbl.config(
            text=f"  Total Income: {fmt_rm(tot)}   |   Salary: {fmt_rm(sal)}"
                 f"   |   Allowances: {fmt_rm(alw)}"
        )

    # ── Cross-page notification ───────────────────────────────────────────────

    def _notify_other_pages(self):
        """Ask the root app to refresh pages that depend on income data."""
        root = self.winfo_toplevel()
        if hasattr(root, "refresh_page"):
            for key in ("dashboard", "tax"):
                root.refresh_page(key)
