# --- pages/dashboard.py ------------------------------------------------------
# Dashboard page: summary cards, charts, recent income / expense tables.

import sys, os as _os
_PROJECT_DIR = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
if _PROJECT_DIR not in sys.path:
    sys.path.insert(0, _PROJECT_DIR)

import tkinter as tk
from tkinter import ttk
from datetime import date, datetime
from collections import defaultdict

from config  import (C_BG, C_CARD, C_TEXT, C_TEXT_MED, C_SUCCESS,
                     C_DANGER, C_PRIMARY, C_WARNING, C_BORDER, EXPENSE_CATS)
from utils   import fmt_rm, calc_malaysia_tax
from widgets import Card, ScrollFrame

# --- matplotlib setup --------------------------------------------------------
try:
    import matplotlib
    matplotlib.use("TkAgg")
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    import matplotlib.pyplot as plt
    MPL = True
except ImportError:
    MPL = False


class DashboardPage(ScrollFrame):
    """
    Overview page:
      • 4 summary cards
      • Bar chart  – monthly income vs expenses (last 6 months)
      • Pie chart  – expense breakdown by category
      • Recent income table
      • Recent expenses table
    """

    def __init__(self, parent, db):
        super().__init__(parent)
        self.db = db
        self._mpl_canvases = []   # keep references so GC doesn't destroy them
        self._build()

    # ── Build -----------------------------------------------------------------

    def _build(self):
        inner = self.inner

        # Title
        tk.Label(inner, text="Dashboard",
                 font=("Segoe UI", 20, "bold"), bg=C_BG, fg=C_TEXT
                 ).pack(anchor="w", padx=28, pady=(24, 2))
        tk.Label(inner,
                 text=f"Financial Overview  \u2022  {date.today().strftime('%B %Y')}",
                 font=("Segoe UI", 10), bg=C_BG, fg=C_TEXT_MED
                 ).pack(anchor="w", padx=28, pady=(0, 16))

        # Summary cards
        self._cards_frame = tk.Frame(inner, bg=C_BG)
        self._cards_frame.pack(fill="x", padx=24, pady=(0, 20))
        self._card_labels = {}
        self._build_summary_cards()

        # Charts row
        if MPL:
            self._charts_frame = tk.Frame(inner, bg=C_BG)
            self._charts_frame.pack(fill="x", padx=24, pady=(0, 20))
            self._charts_frame.columnconfigure(0, weight=3)
            self._charts_frame.columnconfigure(1, weight=2)
            self._bar_card  = Card(self._charts_frame, padx=16, pady=14,
                                   highlightbackground=C_BORDER, highlightthickness=1)
            self._bar_card.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
            self._pie_card  = Card(self._charts_frame, padx=16, pady=14,
                                   highlightbackground=C_BORDER, highlightthickness=1)
            self._pie_card.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        else:
            tk.Label(inner,
                     text="  Install matplotlib for charts:  python -m pip install matplotlib",
                     font=("Segoe UI", 9, "italic"), bg="#fefce8", fg="#92400e",
                     pady=8
                     ).pack(fill="x", padx=28, pady=(0, 12))

        # Recent tables row
        cols = tk.Frame(inner, bg=C_BG)
        cols.pack(fill="both", expand=True, padx=24, pady=(0, 24))
        cols.columnconfigure(0, weight=1)
        cols.columnconfigure(1, weight=1)

        inc_card = Card(cols, padx=16, pady=14)
        inc_card.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        tk.Label(inc_card, text="Recent Income",
                 font=("Segoe UI", 11, "bold"), bg=C_CARD, fg=C_TEXT
                 ).pack(anchor="w", pady=(0, 8))
        self._inc_tree = self._mini_tree(inc_card, ["Name", "Category", "Amount"])
        self._inc_tree.pack(fill="both", expand=True)

        exp_card = Card(cols, padx=16, pady=14)
        exp_card.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        tk.Label(exp_card, text="Recent Expenses",
                 font=("Segoe UI", 11, "bold"), bg=C_CARD, fg=C_TEXT
                 ).pack(anchor="w", pady=(0, 8))
        self._exp_tree = self._mini_tree(exp_card, ["Name", "Category", "Amount"])
        self._exp_tree.pack(fill="both", expand=True)

        self.refresh()

    # ── Summary cards ---------------------------------------------------------

    def _build_summary_cards(self):
        defs = [
            ("Total Income",   "💵", C_SUCCESS, self._get_income),
            ("Total Expenses", "🧾", C_DANGER,  self._get_expenses),
            ("Net Balance",    "⚖️",  C_PRIMARY, self._get_balance),
            ("Est. Tax",       "📋", C_WARNING, self._get_est_tax),
        ]
        for i, (title, icon, color, getter) in enumerate(defs):
            card = Card(self._cards_frame, padx=18, pady=16,
                        highlightbackground=C_BORDER, highlightthickness=1)
            card.grid(row=0, column=i, padx=6, pady=4, sticky="ew")
            self._cards_frame.columnconfigure(i, weight=1)
            tk.Label(card, text=f"{icon}  {title}",
                     font=("Segoe UI", 9), bg=C_CARD, fg=C_TEXT_MED).pack(anchor="w")
            lbl = tk.Label(card, text="RM \u2013",
                           font=("Segoe UI", 16, "bold"), bg=C_CARD, fg=color)
            lbl.pack(anchor="w", pady=(4, 0))
            self._card_labels[title] = (lbl, getter)

    # ── Matplotlib charts -----------------------------------------------------

    def _draw_charts(self):
        if not MPL:
            return

        # Clear previous chart widgets
        for w in self._bar_card.winfo_children():
            w.destroy()
        for w in self._pie_card.winfo_children():
            w.destroy()
        self._mpl_canvases.clear()

        self._draw_bar_chart()
        self._draw_pie_chart()

    def _draw_bar_chart(self):
        """Monthly income vs expenses for the last 6 months."""
        # Build month buckets
        today = date.today()
        months = []
        for i in range(5, -1, -1):
            m = today.month - i
            y = today.year
            while m <= 0:
                m += 12
                y -= 1
            months.append((y, m))

        inc_totals  = []
        exp_totals  = []
        labels      = []
        for y, m in months:
            prefix = f"{y}-{m:02d}"
            inc = sum(
                r["amount"] for r in self.db.get_income()
                if r["date"].startswith(prefix)
            )
            exp = sum(
                r["amount"] for r in self.db.get_expenses()
                if r["date"].startswith(prefix)
            )
            inc_totals.append(inc)
            exp_totals.append(exp)
            labels.append(datetime(y, m, 1).strftime("%b %y"))

        fig = Figure(figsize=(5.5, 3.2), dpi=96, facecolor="white")
        ax  = fig.add_subplot(111)
        fig.subplots_adjust(left=0.12, right=0.97, top=0.88, bottom=0.15)

        x      = range(len(labels))
        width  = 0.35
        bars_i = ax.bar([v - width/2 for v in x], inc_totals,
                        width, label="Income",   color="#10b981", alpha=0.85)
        bars_e = ax.bar([v + width/2 for v in x], exp_totals,
                        width, label="Expenses", color="#ef4444", alpha=0.85)

        ax.set_title("Monthly Income vs Expenses", fontsize=11,
                     fontweight="bold", color="#1e293b", pad=8)
        ax.set_xticks(list(x))
        ax.set_xticklabels(labels, fontsize=8)
        ax.tick_params(axis="y", labelsize=8)
        ax.yaxis.set_major_formatter(
            matplotlib.ticker.FuncFormatter(lambda v, _: f"RM {v:,.0f}")
        )
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.set_facecolor("#f8fafc")
        ax.grid(axis="y", color="#e2e8f0", linewidth=0.7)
        ax.legend(fontsize=8, framealpha=0)

        tk.Label(self._bar_card, text="Income vs Expenses (6 months)",
                 font=("Segoe UI", 11, "bold"), bg=C_CARD, fg=C_TEXT
                 ).pack(anchor="w", pady=(0, 6))

        canvas = FigureCanvasTkAgg(fig, master=self._bar_card)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)
        self._mpl_canvases.append(canvas)
        plt.close(fig)

    def _draw_pie_chart(self):
        """Expense breakdown by category (non-zero only)."""
        rows    = self.db.get_expenses()
        totals  = defaultdict(float)
        for r in rows:
            totals[r["category"]] += r["amount"]

        # Filter zero categories
        data   = {k: v for k, v in totals.items() if v > 0}

        tk.Label(self._pie_card, text="Expense Breakdown",
                 font=("Segoe UI", 11, "bold"), bg=C_CARD, fg=C_TEXT
                 ).pack(anchor="w", pady=(0, 6))

        if not data:
            tk.Label(self._pie_card,
                     text="No expense data yet.",
                     font=("Segoe UI", 9, "italic"),
                     bg=C_CARD, fg=C_TEXT_MED
                     ).pack(expand=True)
            return

        palette = [
            "#4f46e5","#10b981","#ef4444","#f59e0b","#06b6d4",
            "#8b5cf6","#ec4899","#14b8a6","#f97316","#64748b",
            "#84cc16","#e11d48",
        ]
        cat_labels  = [EXPENSE_CATS.get(k, (k,))[0][:18] for k in data]
        values      = list(data.values())
        colors      = [palette[i % len(palette)] for i in range(len(values))]

        fig = Figure(figsize=(3.8, 3.2), dpi=96, facecolor="white")
        ax  = fig.add_subplot(111)
        fig.subplots_adjust(left=0.02, right=0.98, top=0.95, bottom=0.05)

        wedges, texts, autotexts = ax.pie(
            values,
            labels=None,
            colors=colors,
            autopct=lambda p: f"{p:.1f}%" if p >= 5 else "",
            startangle=140,
            wedgeprops={"linewidth": 1.5, "edgecolor": "white"},
            pctdistance=0.75,
        )
        for at in autotexts:
            at.set_fontsize(7)
            at.set_color("white")
            at.set_fontweight("bold")

        # Draw a white circle in the middle to make it a donut
        centre = plt.Circle((0, 0), 0.5, fc="white")
        ax.add_patch(centre)

        # Legend outside the pie
        ax.legend(wedges, cat_labels,
                  loc="lower center",
                  bbox_to_anchor=(0.5, -0.22),
                  ncol=2,
                  fontsize=7,
                  framealpha=0,
                  handlelength=1.2,
                  handleheight=1.0)

        canvas = FigureCanvasTkAgg(fig, master=self._pie_card)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)
        self._mpl_canvases.append(canvas)
        plt.close(fig)

    # ── Mini treeview ---------------------------------------------------------

    @staticmethod
    def _mini_tree(parent, columns):
        tree = ttk.Treeview(parent, columns=columns, show="headings", height=8)
        for col in columns:
            w      = 100 if col == "Amount" else 160
            anchor = "e" if col == "Amount" else "w"
            tree.heading(col, text=col)
            tree.column(col, width=w, anchor=anchor)
        return tree

    # ── Data getters ----------------------------------------------------------

    def _get_income(self):   return self.db.total_income()
    def _get_expenses(self): return self.db.total_expenses()
    def _get_balance(self):  return self.db.total_income() - self.db.total_expenses()

    def _get_est_tax(self):
        income = self.db.total_income()
        return calc_malaysia_tax(max(0.0, income - 9_000))

    # ── Refresh ---------------------------------------------------------------

    def refresh(self):
        # Summary cards
        for title, (lbl, getter) in self._card_labels.items():
            try:
                lbl.config(text=fmt_rm(getter()))
            except Exception:
                pass

        # Charts
        self._draw_charts()

        # Recent income
        for item in self._inc_tree.get_children():
            self._inc_tree.delete(item)
        for row in self.db.get_income()[:8]:
            self._inc_tree.insert("", "end", values=(
                row["name"],
                row["category"].capitalize(),
                fmt_rm(row["amount"]),
            ))

        # Recent expenses
        for item in self._exp_tree.get_children():
            self._exp_tree.delete(item)
        for row in self.db.get_expenses()[:8]:
            cat_label = EXPENSE_CATS.get(row["category"], ("Others",))[0][:22]
            self._exp_tree.insert("", "end", values=(
                row["name"],
                cat_label,
                fmt_rm(row["amount"]),
            ))