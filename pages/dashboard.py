# pages/dashboard.py
# Dashboard: period-filtered summary cards, bar chart, monthly pie chart, recent tables.

import sys, os as _os
_PROJECT_DIR = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
if _PROJECT_DIR not in sys.path:
    sys.path.insert(0, _PROJECT_DIR)

import tkinter as tk
from tkinter import ttk
from datetime import date, datetime
from collections import defaultdict

from config  import (C_BG, C_CARD, C_TEXT, C_TEXT_MED, C_TEXT_LT,
                     C_SUCCESS, C_DANGER, C_PRIMARY, C_PRIMARY_LT,
                     C_WARNING, C_BORDER, EXPENSE_CATS)
from utils   import fmt_rm, calc_malaysia_tax
from widgets import Card, ScrollFrame
from export  import export_to_excel

try:
    import matplotlib
    matplotlib.use("TkAgg")
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    import matplotlib.pyplot as plt
    import matplotlib.ticker
    MPL = True
except ImportError:
    MPL = False

MONTHS = ["January","February","March","April","May","June",
          "July","August","September","October","November","December"]

# Period toggle options
PERIODS = ["This Month", "This Year", "All Time"]


class DashboardPage(ScrollFrame):
    """
    Overview page:
      • Period toggle (This Month / This Year / All Time) on summary cards
      • Bar chart — monthly income vs expenses (last 6 months)
      • Donut chart — expense breakdown for a selectable month/year
      • Recent income and expense tables
      • Export to Excel button
    """

    def __init__(self, parent, db):
        super().__init__(parent)
        self.db = db
        self._mpl_canvases = []

        today = date.today()
        self._pie_month = today.month
        self._pie_year  = today.year
        self._period    = tk.StringVar(value="This Month")

        self._build()

    # ── Build ─────────────────────────────────────────────────────────────────

    def _build(self):
        inner = self.inner

        # Title row
        title_row = tk.Frame(inner, bg=C_BG)
        title_row.pack(fill="x", padx=28, pady=(24, 2))
        tk.Label(title_row, text="Dashboard",
                 font=("Segoe UI", 20, "bold"), bg=C_BG, fg=C_TEXT
                 ).pack(side="left")

        # Export button
        from widgets import make_button
        make_button(title_row, "📥  Export to Excel",
                    command=lambda: export_to_excel(self.db, self),
                    bg="#f0fdf4", fg=C_SUCCESS,
                    font=("Segoe UI", 9, "bold"), pady=5, padx=10
                    ).pack(side="right")

        tk.Label(inner,
                 text=f"Financial Overview  •  {date.today().strftime('%B %Y')}",
                 font=("Segoe UI", 10), bg=C_BG, fg=C_TEXT_MED
                 ).pack(anchor="w", padx=28, pady=(0, 8))

        # ── Period toggle ──────────────────────────────
        tog_row = tk.Frame(inner, bg=C_BG)
        tog_row.pack(anchor="w", padx=28, pady=(0, 12))
        tk.Label(tog_row, text="Show totals for:",
                 font=("Segoe UI", 9), bg=C_BG, fg=C_TEXT_MED
                 ).pack(side="left", padx=(0, 8))
        for p in PERIODS:
            tk.Radiobutton(
                tog_row, text=p, variable=self._period, value=p,
                bg=C_BG, fg=C_TEXT, selectcolor=C_PRIMARY_LT,
                activebackground=C_BG,
                font=("Segoe UI", 9),
                command=self._on_period_change
            ).pack(side="left", padx=4)

        # Summary cards
        self._cards_frame = tk.Frame(inner, bg=C_BG)
        self._cards_frame.pack(fill="x", padx=24, pady=(0, 20))
        self._card_labels = {}
        self._build_summary_cards()

        # Charts
        if MPL:
            self._charts_frame = tk.Frame(inner, bg=C_BG)
            self._charts_frame.pack(fill="x", padx=24, pady=(0, 20))
            self._charts_frame.columnconfigure(0, weight=3)
            self._charts_frame.columnconfigure(1, weight=2)

            self._bar_card = Card(self._charts_frame, padx=16, pady=14,
                                  highlightbackground=C_BORDER, highlightthickness=1)
            self._bar_card.grid(row=0, column=0, sticky="nsew", padx=(0, 8))

            self._pie_card = Card(self._charts_frame, padx=16, pady=14,
                                  highlightbackground=C_BORDER, highlightthickness=1)
            self._pie_card.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
            self._build_pie_header(self._pie_card)
            self._pie_chart_area = tk.Frame(self._pie_card, bg=C_CARD)
            self._pie_chart_area.pack(fill="both", expand=True)
        else:
            tk.Label(inner,
                     text="  Install matplotlib for charts:  "
                          "python -m pip install matplotlib",
                     font=("Segoe UI", 9, "italic"),
                     bg="#fefce8", fg="#92400e", pady=8
                     ).pack(fill="x", padx=28, pady=(0, 12))

        # Recent tables
        cols = tk.Frame(inner, bg=C_BG)
        cols.pack(fill="both", expand=True, padx=24, pady=(0, 24))
        cols.columnconfigure(0, weight=1)
        cols.columnconfigure(1, weight=1)

        inc_card = Card(cols, padx=16, pady=14)
        inc_card.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        tk.Label(inc_card, text="Recent Income",
                 font=("Segoe UI", 11, "bold"), bg=C_CARD, fg=C_TEXT
                 ).pack(anchor="w", pady=(0, 8))
        self._inc_tree = self._mini_tree(inc_card, ["Name","Category","Amount"])
        self._inc_tree.pack(fill="both", expand=True)

        exp_card = Card(cols, padx=16, pady=14)
        exp_card.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        tk.Label(exp_card, text="Recent Expenses",
                 font=("Segoe UI", 11, "bold"), bg=C_CARD, fg=C_TEXT
                 ).pack(anchor="w", pady=(0, 8))
        self._exp_tree = self._mini_tree(exp_card, ["Name","Category","Amount"])
        self._exp_tree.pack(fill="both", expand=True)

        self.refresh()

    # ── Period toggle ─────────────────────────────────────────────────────────

    def _on_period_change(self):
        self._update_cards()

    def _period_args(self):
        """Return (year, month) kwargs for total_*_period calls."""
        p = self._period.get()
        today = date.today()
        if p == "This Month":
            return {"year": today.year, "month": today.month}
        if p == "This Year":
            return {"year": today.year}
        return {}   # All Time

    # ── Summary cards ─────────────────────────────────────────────────────────

    def _build_summary_cards(self):
        defs = [
            ("Total Income",   "💵", C_SUCCESS, "income"),
            ("Total Expenses", "🧾", C_DANGER,  "expenses"),
            ("Net Balance",    "⚖️",  C_PRIMARY, "balance"),
            ("Est. Tax",       "📋", C_WARNING, "tax"),
        ]
        for i, (title, icon, color, key) in enumerate(defs):
            card = Card(self._cards_frame, padx=18, pady=16,
                        highlightbackground=C_BORDER, highlightthickness=1)
            card.grid(row=0, column=i, padx=6, pady=4, sticky="ew")
            self._cards_frame.columnconfigure(i, weight=1)
            tk.Label(card, text=f"{icon}  {title}",
                     font=("Segoe UI", 9), bg=C_CARD, fg=C_TEXT_MED).pack(anchor="w")
            lbl = tk.Label(card, text="RM –",
                           font=("Segoe UI", 16, "bold"), bg=C_CARD, fg=color)
            lbl.pack(anchor="w", pady=(4, 0))
            self._card_labels[key] = lbl

    def _update_cards(self):
        kwargs = self._period_args()
        try:
            inc  = self.db.total_income_period(**kwargs)
            exp  = self.db.total_expenses_period(**kwargs)
            bal  = inc - exp
            # Est. tax always uses all-time salary (YTD) for accuracy
            sal  = self.db.total_income("salary")
            tax  = calc_malaysia_tax(max(0.0, sal - 9_000))
        except Exception:
            return
        self._card_labels["income"].config(text=fmt_rm(inc))
        self._card_labels["expenses"].config(text=fmt_rm(exp))
        self._card_labels["balance"].config(text=fmt_rm(bal))
        self._card_labels["tax"].config(text=fmt_rm(tax))

    # ── Pie chart header (month/year dropdowns) ───────────────────────────────

    def _build_pie_header(self, parent):
        hdr = tk.Frame(parent, bg=C_CARD)
        hdr.pack(fill="x", pady=(0, 6))

        tk.Label(hdr, text="Expense Breakdown",
                 font=("Segoe UI", 11, "bold"), bg=C_CARD, fg=C_TEXT
                 ).pack(side="left")

        nav = tk.Frame(hdr, bg=C_CARD)
        nav.pack(side="right")

        today = date.today()
        years = [str(y) for y in range(today.year - 3, today.year + 4)]
        self._pie_year_var = tk.StringVar(value=str(self._pie_year))
        yr_cb = ttk.Combobox(nav, textvariable=self._pie_year_var,
                             values=years, state="readonly",
                             width=6, font=("Segoe UI", 9))
        yr_cb.pack(side="right", padx=(4, 0))
        yr_cb.bind("<<ComboboxSelected>>", self._on_pie_select)
        tk.Label(nav, text="Year:", font=("Segoe UI", 9),
                 bg=C_CARD, fg=C_TEXT_MED).pack(side="right", padx=(8, 2))

        self._pie_month_var = tk.StringVar(value=MONTHS[self._pie_month - 1])
        mo_cb = ttk.Combobox(nav, textvariable=self._pie_month_var,
                             values=MONTHS, state="readonly",
                             width=10, font=("Segoe UI", 9))
        mo_cb.pack(side="right", padx=(4, 0))
        mo_cb.bind("<<ComboboxSelected>>", self._on_pie_select)
        tk.Label(nav, text="Month:", font=("Segoe UI", 9),
                 bg=C_CARD, fg=C_TEXT_MED).pack(side="right", padx=(0, 2))

    def _on_pie_select(self, _e=None):
        try:
            self._pie_month = MONTHS.index(self._pie_month_var.get()) + 1
            self._pie_year  = int(self._pie_year_var.get())
        except (ValueError, IndexError):
            return
        self._redraw_pie()

    def _redraw_pie(self):
        if not MPL:
            return
        for w in self._pie_chart_area.winfo_children():
            w.destroy()
        self._mpl_canvases = [c for c in self._mpl_canvases
                               if c.get_tk_widget().winfo_exists()]
        self._draw_pie_chart()

    # ── Charts ────────────────────────────────────────────────────────────────

    def _draw_charts(self):
        if not MPL:
            return
        for w in self._bar_card.winfo_children():
            w.destroy()
        self._mpl_canvases.clear()
        self._draw_bar_chart()
        self._redraw_pie()

    def _draw_bar_chart(self):
        today = date.today()
        months = []
        for i in range(5, -1, -1):
            m = today.month - i
            y = today.year
            while m <= 0:
                m += 12; y -= 1
            months.append((y, m))

        all_inc = self.db.get_income()
        all_exp = self.db.get_expenses()
        inc_totals, exp_totals, labels = [], [], []
        for y, m in months:
            prefix = f"{y}-{m:02d}"
            inc_totals.append(sum(r["amount"] for r in all_inc if r["date"].startswith(prefix)))
            exp_totals.append(sum(r["amount"] for r in all_exp if r["date"].startswith(prefix)))
            labels.append(datetime(y, m, 1).strftime("%b %y"))

        fig = Figure(figsize=(5.5, 3.2), dpi=96, facecolor="white")
        ax  = fig.add_subplot(111)
        fig.subplots_adjust(left=0.12, right=0.97, top=0.88, bottom=0.15)

        x, w = range(len(labels)), 0.35
        ax.bar([v - w/2 for v in x], inc_totals, w, label="Income",
               color="#10b981", alpha=0.85)
        ax.bar([v + w/2 for v in x], exp_totals, w, label="Expenses",
               color="#ef4444", alpha=0.85)
        ax.set_title("Monthly Income vs Expenses", fontsize=11,
                     fontweight="bold", color="#1e293b", pad=8)
        ax.set_xticks(list(x))
        ax.set_xticklabels(labels, fontsize=8)
        ax.tick_params(axis="y", labelsize=8)
        ax.yaxis.set_major_formatter(
            matplotlib.ticker.FuncFormatter(lambda v, _: f"RM {v:,.0f}"))
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
        period_str = f"{MONTHS[self._pie_month - 1]} {self._pie_year}"
        prefix = f"{self._pie_year}-{self._pie_month:02d}"
        totals = defaultdict(float)
        for r in self.db.get_expenses():
            if r["date"].startswith(prefix):
                totals[r["category"]] += r["amount"]
        data = {k: v for k, v in totals.items() if v > 0}
        area = self._pie_chart_area

        if not data:
            tk.Label(area,
                     text=f"No expenses for {period_str}.",
                     font=("Segoe UI", 9, "italic"),
                     bg=C_CARD, fg=C_TEXT_MED
                     ).pack(expand=True, pady=40)
            return

        palette = ["#4f46e5","#10b981","#ef4444","#f59e0b","#06b6d4",
                   "#8b5cf6","#ec4899","#14b8a6","#f97316","#64748b",
                   "#84cc16","#e11d48"]
        cat_labels = [EXPENSE_CATS.get(k, (k,))[0][:18] for k in data]
        values     = list(data.values())
        colors     = [palette[i % len(palette)] for i in range(len(values))]
        total      = sum(values)

        fig = Figure(figsize=(3.8, 3.4), dpi=96, facecolor="white")
        ax  = fig.add_subplot(111)
        fig.subplots_adjust(left=0.02, right=0.98, top=0.92, bottom=0.08)

        wedges, _, autotexts = ax.pie(
            values, labels=None, colors=colors,
            autopct=lambda p: f"{p:.1f}%" if p >= 5 else "",
            startangle=140,
            wedgeprops={"linewidth": 1.5, "edgecolor": "white"},
            pctdistance=0.75)
        for at in autotexts:
            at.set_fontsize(7)
            at.set_color("white")
            at.set_fontweight("bold")

        centre = plt.Circle((0, 0), 0.5, fc="white")
        ax.add_patch(centre)
        ax.text(0, 0, f"RM\n{total:,.0f}",
                ha="center", va="center",
                fontsize=7, fontweight="bold", color="#1e293b")

        ax.legend(wedges, cat_labels,
                  loc="lower center", bbox_to_anchor=(0.5, -0.18),
                  ncol=2, fontsize=7, framealpha=0,
                  handlelength=1.2, handleheight=1.0)

        canvas = FigureCanvasTkAgg(fig, master=area)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)
        self._mpl_canvases.append(canvas)
        plt.close(fig)

    # ── Mini treeview ─────────────────────────────────────────────────────────

    @staticmethod
    def _mini_tree(parent, columns):
        tree = ttk.Treeview(parent, columns=columns,
                            show="headings", height=8)
        for col in columns:
            w      = 100 if col == "Amount" else 160
            anchor = "e" if col == "Amount" else "w"
            tree.heading(col, text=col)
            tree.column(col, width=w, anchor=anchor)
        return tree

    # ── Refresh ───────────────────────────────────────────────────────────────

    def refresh(self):
        self._update_cards()
        self._draw_charts()

        for item in self._inc_tree.get_children():
            self._inc_tree.delete(item)
        for row in self.db.get_income()[:8]:
            self._inc_tree.insert("", "end", values=(
                row["name"], row["category"].capitalize(), fmt_rm(row["amount"])))

        for item in self._exp_tree.get_children():
            self._exp_tree.delete(item)
        for row in self.db.get_expenses()[:8]:
            cat = EXPENSE_CATS.get(row["category"], ("Others",))[0][:22]
            self._exp_tree.insert("", "end", values=(
                row["name"], cat, fmt_rm(row["amount"])))