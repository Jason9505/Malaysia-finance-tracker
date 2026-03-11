# ─── pages/tax.py ────────────────────────────────────────────────────────────
# Income Tax page: pulls income & expense data, applies YA 2025 reliefs,
# shows full tax computation and bracket breakdown. Supports manual relief entries.

import sys, os as _os
_PROJECT_DIR = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
if _PROJECT_DIR not in sys.path:
    sys.path.insert(0, _PROJECT_DIR)


import os
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import date

from config  import (C_BG, C_CARD, C_TEXT, C_TEXT_MED, C_TEXT_LT,
                     C_SUCCESS, C_DANGER, C_WARNING, C_BORDER,
                     C_PRIMARY, C_PRIMARY_LT, ALL_RELIEFS)
from utils   import fmt_rm, compute_full_tax, build_bracket_rows, save_receipt
from widgets import Card, ScrollFrame, ViewReceiptDialog, make_button


class TaxPage(ScrollFrame):
    """
    Income Tax Calculator page (Malaysia YA 2025).

    Data flow:
      1. Salary + Allowance totals pulled from DB → Gross Income
      2. Tax-deductible expenses are mapped to relief keys automatically
      3. User can add extra manual relief entries with optional receipt
      4. Progressive tax computed → shows chargeable income, net tax, bracket table
    """

    def __init__(self, parent, db):
        super().__init__(parent)
        self.db = db
        self._build()

    # ── Build ─────────────────────────────────────────────────────────────────

    def _build(self):
        inner = self.inner

        # Page title
        tk.Label(inner, text="Income Tax Calculator",
                 font=("Segoe UI", 20, "bold"), bg=C_BG, fg=C_TEXT
                 ).pack(anchor="w", padx=28, pady=(24, 2))
        tk.Label(inner, text="Malaysia – Assessment Year 2025 (YA 2025)",
                 font=("Segoe UI", 10), bg=C_BG, fg=C_TEXT_MED
                 ).pack(anchor="w", padx=28, pady=(0, 12))

        self._build_income_summary(inner)
        self._build_relief_section(inner)
        self._build_computation_card(inner)
        self._build_bracket_table(inner)

        self.refresh()

    # ── Income summary ────────────────────────────────────────────────────────

    def _build_income_summary(self, parent):
        card = Card(parent, padx=20, pady=16,
                    highlightbackground=C_BORDER, highlightthickness=1)
        card.pack(fill="x", padx=28, pady=(4, 8))

        tk.Label(card, text="💵  Income Sources",
                 font=("Segoe UI", 12, "bold"), bg=C_CARD, fg=C_TEXT
                 ).pack(anchor="w", pady=(0, 8))

        grid = tk.Frame(card, bg=C_CARD)
        grid.pack(fill="x")
        grid.columnconfigure(1, weight=1)

        self._inc_labels = {}
        rows = [
            ("Salary",             "salary",    C_TEXT,    ""),
            ("Allowances",         "allowance", C_TEXT,    ""),
            ("Total Gross Income", "total",     C_SUCCESS, "bold"),
        ]
        for i, (display, key, color, weight) in enumerate(rows):
            tk.Label(grid, text=display, font=("Segoe UI", 10),
                     bg=C_CARD, fg=C_TEXT).grid(row=i, column=0, sticky="w", pady=3)
            lbl = tk.Label(grid, text="RM 0.00",
                           font=("Segoe UI", 10, weight), bg=C_CARD, fg=color)
            lbl.grid(row=i, column=1, sticky="e", pady=3)
            self._inc_labels[key] = lbl

    # ── Relief section ────────────────────────────────────────────────────────

    def _build_relief_section(self, parent):
        tk.Label(parent, text="📉  Tax Reliefs & Deductions",
                 font=("Segoe UI", 13, "bold"), bg=C_BG, fg=C_TEXT
                 ).pack(anchor="w", padx=28, pady=(12, 2))
        tk.Label(parent,
                 text="  Auto-reliefs are derived from your expense entries. "
                      "Add manual entries for reliefs not linked to an expense.",
                 font=("Segoe UI", 9, "italic"), bg=C_BG, fg=C_TEXT_MED,
                 wraplength=800, justify="left"
                 ).pack(anchor="w", padx=28, pady=(0, 6))

        card = Card(parent, padx=0, pady=0,
                    highlightbackground=C_BORDER, highlightthickness=1)
        card.pack(fill="x", padx=28, pady=(0, 4))

        # Relief treeview
        r_cols = [
            ("category",   "Relief Category",  280, "w",      True),
            ("max_rm",     "Max (RM)",          110, "e",      False),
            ("auto_rm",    "Auto (RM)",         110, "e",      False),
            ("manual_rm",  "Manual (RM)",       110, "e",      False),
            ("claimed_rm", "Claimed (RM)",      120, "e",      False),
        ]
        all_cols = [c[0] for c in r_cols] + ["_key"]
        self._relief_tree = ttk.Treeview(card, columns=all_cols,
                                          show="headings", height=14,
                                          selectmode="browse")
        for col_id, display, width, anchor, stretch in r_cols:
            self._relief_tree.heading(col_id, text=display)
            self._relief_tree.column(col_id, width=width, anchor=anchor,
                                      stretch=stretch, minwidth=60)
        self._relief_tree.heading("_key", text="")
        self._relief_tree.column("_key", width=0, stretch=False, minwidth=0)

        rsb = ttk.Scrollbar(card, orient="vertical",
                            command=self._relief_tree.yview)
        self._relief_tree.configure(yscrollcommand=rsb.set)
        self._relief_tree.pack(side="left", fill="both", expand=True)
        rsb.pack(side="right", fill="y")

        # Row colour tags
        self._relief_tree.tag_configure("auto",   background=C_CARD)
        self._relief_tree.tag_configure("mixed",  background="#f0fdf4")
        self._relief_tree.tag_configure("manual", background="#eff6ff",
                                         foreground=C_PRIMARY)

        # Action buttons
        bar = tk.Frame(parent, bg=C_BG)
        bar.pack(fill="x", padx=28, pady=(4, 4))

        make_button(bar, "➕  Add Manual Relief",
                    self._open_add_relief_dialog,
                    font=("Segoe UI", 9, "bold"), pady=5, padx=12
                    ).pack(side="left")
        make_button(bar, "🗑  Delete Selected",
                    self._delete_manual_relief,
                    bg="#fff1f2", fg=C_DANGER,
                    font=("Segoe UI", 9), pady=5, padx=10
                    ).pack(side="left", padx=6)
        make_button(bar, "📎  View Receipt",
                    self._view_relief_receipt,
                    bg=C_BG, fg=C_TEXT,
                    font=("Segoe UI", 9), pady=5, padx=10
                    ).pack(side="left")

    # ── Tax computation card ──────────────────────────────────────────────────

    def _build_computation_card(self, parent):
        tk.Label(parent, text="🧮  Tax Computation",
                 font=("Segoe UI", 13, "bold"), bg=C_BG, fg=C_TEXT
                 ).pack(anchor="w", padx=28, pady=(14, 6))

        card = Card(parent, padx=20, pady=16,
                    highlightbackground=C_BORDER, highlightthickness=1)
        card.pack(fill="x", padx=28, pady=(0, 4))

        grid = tk.Frame(card, bg=C_CARD)
        grid.pack(fill="x")
        grid.columnconfigure(1, weight=1)

        self._calc_labels = {}
        row_defs = [
            ("Gross Income",              "gross",       C_TEXT,     "bold"),
            ("Total Tax Reliefs",          "reliefs",     C_SUCCESS,  ""),
            ("Chargeable Income",          "chargeable",  C_TEXT,     "bold"),
            ("─────────────────────",     None,          C_TEXT_LT,  ""),
            ("Income Tax (Before Rebate)", "tax_before",  C_WARNING,  ""),
            ("Tax Rebate  (≤ RM 35,000)",  "rebate",      C_SUCCESS,  ""),
            ("Net Tax Payable",            "net_tax",     C_DANGER,   "bold"),
            ("Effective Tax Rate",         "eff_rate",    C_TEXT_MED, ""),
        ]
        for i, (display, key, color, weight) in enumerate(row_defs):
            is_divider = display.startswith("─")
            tk.Label(grid, text=display,
                     font=("Segoe UI", 10, weight),
                     bg=C_CARD,
                     fg=C_TEXT_LT if is_divider else C_TEXT
                     ).grid(row=i, column=0, sticky="w", pady=2, padx=(0, 20))
            if key:
                lbl = tk.Label(grid, text="RM 0.00",
                               font=("Segoe UI", 11, weight),
                               bg=C_CARD, fg=color)
                lbl.grid(row=i, column=1, sticky="e", pady=2)
                self._calc_labels[key] = lbl

    # ── Bracket table ─────────────────────────────────────────────────────────

    def _build_bracket_table(self, parent):
        tk.Label(parent, text="📊  Tax Bracket Breakdown",
                 font=("Segoe UI", 13, "bold"), bg=C_BG, fg=C_TEXT
                 ).pack(anchor="w", padx=28, pady=(14, 6))

        card = Card(parent, padx=0, pady=0,
                    highlightbackground=C_BORDER, highlightthickness=1)
        card.pack(fill="x", padx=28, pady=(0, 28))

        brk_cols = [
            ("bracket",    "Income Band",     280, "w",      True),
            ("rate",       "Rate",            100, "center",  False),
            ("taxable",    "Taxable Amount",  160, "e",      False),
            ("tax_amount", "Tax",             160, "e",      False),
        ]
        self._brk_tree = ttk.Treeview(
            card,
            columns=[c[0] for c in brk_cols],
            show="headings", height=12, selectmode="none"
        )
        for col_id, display, width, anchor, stretch in brk_cols:
            self._brk_tree.heading(col_id, text=display)
            self._brk_tree.column(col_id, width=width, anchor=anchor, stretch=stretch)
        self._brk_tree.pack(fill="x")

    # ── Add manual relief dialog ──────────────────────────────────────────────

    def _open_add_relief_dialog(self):
        dialog = tk.Toplevel(self)
        dialog.title("Add Manual Relief Entry")
        dialog.configure(bg=C_CARD)
        dialog.resizable(False, False)
        dialog.grab_set()
        dialog.transient(self)

        # Header
        hdr = tk.Frame(dialog, bg=C_PRIMARY, padx=20, pady=14)
        hdr.pack(fill="x")
        tk.Label(hdr, text="Add Manual Relief Entry",
                 font=("Segoe UI", 12, "bold"), bg=C_PRIMARY, fg="white").pack(side="left")
        tk.Button(hdr, text="✕", bg=C_PRIMARY, fg="white", relief="flat",
                  cursor="hand2", command=dialog.destroy).pack(side="right")

        body = tk.Frame(dialog, bg=C_CARD, padx=24, pady=20)
        body.pack(fill="both")

        def lbl_row(text):
            tk.Label(body, text=text, font=("Segoe UI", 9, "bold"),
                     bg=C_CARD, fg=C_TEXT_MED).pack(anchor="w", pady=(8, 1))

        # Relief category combo
        lbl_row("Relief Category")
        keys  = [r[0] for r in ALL_RELIEFS]
        names = [f"{r[1]}  (max RM {r[2]:,.0f})" for r in ALL_RELIEFS]
        idx_var = tk.IntVar(value=0)
        combo = ttk.Combobox(body, values=names, state="readonly",
                             font=("Segoe UI", 9), width=52)
        combo.current(0)
        combo.pack(fill="x")

        lbl_row("Description")
        name_var = tk.StringVar()
        tk.Entry(body, textvariable=name_var, font=("Segoe UI", 10),
                 relief="solid", bd=1, bg="white").pack(fill="x", ipady=5)

        lbl_row("Amount (RM)")
        amt_var = tk.StringVar()
        tk.Entry(body, textvariable=amt_var, font=("Segoe UI", 10),
                 relief="solid", bd=1, bg="white").pack(fill="x", ipady=5)

        lbl_row("Date (YYYY-MM-DD)")
        dt_var = tk.StringVar(value=date.today().strftime("%Y-%m-%d"))
        tk.Entry(body, textvariable=dt_var, font=("Segoe UI", 10),
                 relief="solid", bd=1, bg="white").pack(fill="x", ipady=5)

        lbl_row("Notes (optional)")
        notes_var = tk.StringVar()
        tk.Entry(body, textvariable=notes_var, font=("Segoe UI", 10),
                 relief="solid", bd=1, bg="white").pack(fill="x", ipady=5)

        # Receipt browse
        lbl_row("Receipt / Invoice")
        receipt_path = [""]
        rec_row = tk.Frame(body, bg=C_CARD)
        rec_row.pack(fill="x", pady=(0, 4))
        rec_lbl = tk.Label(rec_row, text="No file", font=("Segoe UI", 9),
                           bg=C_CARD, fg=C_TEXT_LT)
        rec_lbl.pack(side="left", fill="x", expand=True)

        def browse():
            p = filedialog.askopenfilename(
                filetypes=[("All Supported", "*.png *.jpg *.jpeg *.pdf"),
                           ("All Files", "*.*")])
            if p:
                receipt_path[0] = p
                rec_lbl.config(text=os.path.basename(p)[:32], fg=C_SUCCESS)

        make_button(rec_row, "📎 Browse", browse,
                    bg=C_BG, fg=C_TEXT, font=("Segoe UI", 9),
                    pady=3, padx=8).pack(side="right")

        # Save
        def save():
            selected_idx = combo.current()
            if selected_idx < 0:
                selected_idx = 0
            actual_key = keys[selected_idx]
            name = name_var.get().strip() or ALL_RELIEFS[selected_idx][1]
            try:
                amt = float(amt_var.get().replace(",", ""))
                if amt <= 0:
                    raise ValueError
            except ValueError:
                messagebox.showwarning("Invalid", "Enter a valid positive amount.", parent=dialog)
                return
            stored = save_receipt(receipt_path[0]) if receipt_path[0] else ""
            self.db.add_relief(actual_key, name, amt, dt_var.get(),
                               notes_var.get().strip(), stored)
            self.refresh()
            dialog.destroy()

        make_button(body, "💾  Save Relief", save,
                    font=("Segoe UI", 11, "bold"), pady=10
                    ).pack(fill="x", pady=(14, 0))

        # Center dialog
        dialog.update_idletasks()
        root = self.winfo_toplevel()
        pw, ph = root.winfo_width(), root.winfo_height()
        px, py = root.winfo_rootx(), root.winfo_rooty()
        dw, dh = dialog.winfo_width(), dialog.winfo_height()
        dialog.geometry(f"+{px + (pw - dw) // 2}+{py + (ph - dh) // 2}")

    # ── Delete / view manual relief ───────────────────────────────────────────

    def _delete_manual_relief(self):
        sel = self._relief_tree.focus()
        if not sel:
            messagebox.showinfo("Select Row", "Select a row first.", parent=self)
            return
        key_col = self._relief_tree.item(sel, "values")[-1]
        if not key_col.startswith("M_"):
            messagebox.showinfo(
                "Auto Relief",
                "Auto-computed reliefs are derived from expense entries.\n"
                "Remove the linked expense to change this value.",
                parent=self
            )
            return
        row_id = int(key_col[2:])
        name   = self._relief_tree.item(sel, "values")[0]
        if messagebox.askyesno("Confirm Delete", f"Delete '{name}'?", parent=self):
            self.db.delete_relief(row_id)
            self.refresh()

    def _view_relief_receipt(self):
        sel = self._relief_tree.focus()
        if not sel:
            return
        key_col = self._relief_tree.item(sel, "values")[-1]
        if not key_col.startswith("M_"):
            messagebox.showinfo("Auto Relief", "No receipt for auto-computed entries.", parent=self)
            return
        row_id = int(key_col[2:])
        row = self.db.get_relief_by_id(row_id)
        if row and row["receipt"] and os.path.exists(row["receipt"]):
            ViewReceiptDialog(self, row["receipt"])
        else:
            messagebox.showinfo("No Receipt", "No receipt attached.", parent=self)

    # ── Refresh ───────────────────────────────────────────────────────────────

    def refresh(self):
        # ── Income figures ─────────────────────────────
        sal = self.db.total_income("salary")
        alw = self.db.total_income("allowance")
        gross = sal + alw

        self._inc_labels["salary"].config(text=fmt_rm(sal))
        self._inc_labels["allowance"].config(text=fmt_rm(alw))
        self._inc_labels["total"].config(text=fmt_rm(gross))

        # ── Relief computation ─────────────────────────
        auto_by_relief   = self.db.tax_deductible_by_relief()
        manual_rows      = self.db.get_reliefs()

        # Group manual entries by key
        manual_by_key: dict[str, list] = {}
        for row in manual_rows:
            manual_by_key.setdefault(row["relief_key"], []).append(row)

        # Clear relief tree
        for item in self._relief_tree.get_children():
            self._relief_tree.delete(item)

        total_relief = 0.0
        for key, name, max_rm in ALL_RELIEFS:
            auto_amt   = auto_by_relief.get(key, 0.0)
            manual_amt = sum(r["amount"] for r in manual_by_key.get(key, []))
            claimed    = min(auto_amt + manual_amt, max_rm)
            total_relief += claimed

            tag = "mixed" if manual_amt > 0 else "auto"
            parent_id = self._relief_tree.insert("", "end",
                values=(name, fmt_rm(max_rm), fmt_rm(auto_amt),
                        fmt_rm(manual_amt), fmt_rm(claimed), f"P_{key}"),
                tags=(tag,))

            # Sub-rows for manual entries
            for row in manual_by_key.get(key, []):
                self._relief_tree.insert(parent_id, "end",
                    values=(f"  ↳  {row['name']}", "", "",
                            fmt_rm(row["amount"]), "", f"M_{row['id']}"),
                    tags=("manual",))

        # ── Tax computation ────────────────────────────
        result = compute_full_tax(gross, total_relief)

        self._calc_labels["gross"].config(text=fmt_rm(result["gross"]))
        self._calc_labels["reliefs"].config(text=f"– {fmt_rm(result['reliefs'])}")
        self._calc_labels["chargeable"].config(text=fmt_rm(result["chargeable"]))
        self._calc_labels["tax_before"].config(text=fmt_rm(result["tax_before"]))
        self._calc_labels["rebate"].config(text=f"– {fmt_rm(result['rebate'])}")
        self._calc_labels["net_tax"].config(text=fmt_rm(result["net_tax"]))
        self._calc_labels["eff_rate"].config(text=f"{result['eff_rate']:.2f}%")

        # ── Bracket breakdown ──────────────────────────
        for item in self._brk_tree.get_children():
            self._brk_tree.delete(item)
        for label, rate_str, taxable, tax_amt in build_bracket_rows(result["chargeable"]):
            self._brk_tree.insert("", "end",
                values=(label, rate_str, fmt_rm(taxable), fmt_rm(tax_amt)))
