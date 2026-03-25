# pages/dashboard.py
# Dashboard: period toggle cards, line chart, image-2-style donut + category list.

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

try:
    import matplotlib
    matplotlib.use("TkAgg")
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    import matplotlib.pyplot as plt
    import matplotlib.ticker
    from matplotlib.patches import FancyArrowPatch
    MPL = True
except ImportError:
    MPL = False

MONTHS = ["January","February","March","April","May","June",
          "July","August","September","October","November","December"]
PERIODS = ["This Month", "This Year", "All Time"]

# Colour palette for donut segments + category rows
_PALETTE = ["#06b6d4","#4f46e5","#f97316","#f59e0b","#10b981",
            "#8b5cf6","#ec4899","#ef4444","#14b8a6","#64748b",
            "#84cc16","#e11d48"]


class DashboardPage(ScrollFrame):

    def __init__(self, parent, db):
        super().__init__(parent)
        self.db = db
        self._mpl_canvases = []
        self._pie_period_cb = None  # reference for later updates

        today = date.today()
        self._pie_month = today.month
        self._pie_year  = today.year
        self._period    = tk.StringVar(value="This Month")

        self._build()

    # ── Build ─────────────────────────────────────────────────────────────────

    def _build(self):
        inner = self.inner

        # Title
        title_row = tk.Frame(inner, bg=C_BG)
        title_row.pack(fill="x", padx=28, pady=(24, 2))
        tk.Label(title_row, text="Dashboard",
                 font=("Segoe UI", 20, "bold"), bg=C_BG, fg=C_TEXT
                 ).pack(side="left")

        tk.Label(inner,
                 text=f"Financial Overview  •  {date.today().strftime('%B %Y')}",
                 font=("Segoe UI", 10), bg=C_BG, fg=C_TEXT_MED
                 ).pack(anchor="w", padx=28, pady=(0, 8))

        # Period toggle
        tog = tk.Frame(inner, bg=C_BG)
        tog.pack(anchor="w", padx=28, pady=(0, 12))
        tk.Label(tog, text="Show totals for:",
                 font=("Segoe UI", 9), bg=C_BG, fg=C_TEXT_MED
                 ).pack(side="left", padx=(0, 8))
        for p in PERIODS:
            tk.Radiobutton(tog, text=p, variable=self._period, value=p,
                           bg=C_BG, fg=C_TEXT, selectcolor=C_PRIMARY_LT,
                           activebackground=C_BG, font=("Segoe UI", 9),
                           command=self._on_period_change
                           ).pack(side="left", padx=4)

        # Summary cards
        self._cards_frame = tk.Frame(inner, bg=C_BG)
        self._cards_frame.pack(fill="x", padx=24, pady=(0, 20))
        self._card_labels = {}
        self._build_summary_cards()

        # Charts row
        if MPL:
            cf = tk.Frame(inner, bg=C_BG)
            cf.pack(fill="x", padx=24, pady=(0, 20))
            cf.columnconfigure(0, weight=55)
            cf.columnconfigure(1, weight=45)

            # Left: line chart card
            self._line_card = Card(cf, padx=16, pady=14,
                                   highlightbackground=C_BORDER, highlightthickness=1)
            self._line_card.grid(row=0, column=0, sticky="nsew", padx=(0, 8))

            # Right: donut card
            self._pie_card = Card(cf, padx=16, pady=14,
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
        p     = self._period.get()
        today = date.today()
        if p == "This Month":
            return {"year": today.year, "month": today.month}
        if p == "This Year":
            return {"year": today.year}
        return {}

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
            inc = self.db.total_income_period(**kwargs)
            exp = self.db.total_expenses_period(**kwargs)
            bal = inc - exp
            sal = self.db.total_income("salary")
            tax = calc_malaysia_tax(max(0.0, sal - 9_000))
        except Exception:
            return
        self._card_labels["income"].config(text=fmt_rm(inc))
        self._card_labels["expenses"].config(text=fmt_rm(exp))
        self._card_labels["balance"].config(text=fmt_rm(bal))
        self._card_labels["tax"].config(text=fmt_rm(tax))

    # ── Pie header (month / year dropdowns) ──────────────────────────────────

    # ── Expense month-year options from DB ────────────────────────────────────

    def _get_expense_month_years(self):
        """
        Query the DB for distinct year-month combos that have expense data.
        Returns a list like ['March 2025', 'February 2025', ...] sorted newest first.
        Falls back to the current month/year if no expense data exists at all.
        """
        try:
            rows = self.db.conn.execute(
                "SELECT DISTINCT substr(date,1,7) AS ym FROM expenses "
                "WHERE date != '' ORDER BY ym DESC"
            ).fetchall()
        except Exception:
            rows = []
        result = []
        for row in rows:
            ym = row[0] if row[0] else ""
            try:
                y, m = int(ym[:4]), int(ym[5:7])
                result.append(f"{MONTHS[m - 1]} {y}")
            except (ValueError, IndexError):
                pass
        if not result:
            today = date.today()
            result = [f"{MONTHS[today.month - 1]} {today.year}"]
        return result

    def _build_pie_header(self, parent):
        hdr = tk.Frame(parent, bg=C_CARD)
        hdr.pack(fill="x", pady=(0, 6))

        tk.Label(hdr, text="Expense Breakdown",
                 font=("Segoe UI", 11, "bold"), bg=C_CARD, fg=C_TEXT
                 ).pack(side="left")

        nav = tk.Frame(hdr, bg=C_CARD)
        nav.pack(side="right")

        tk.Label(nav, text="Period:", font=("Segoe UI", 9),
                 bg=C_CARD, fg=C_TEXT_MED).pack(side="left", padx=(0, 4))

        options     = self._get_expense_month_years()
        default_val = f"{MONTHS[self._pie_month - 1]} {self._pie_year}"
        if default_val not in options:
            default_val = options[0]
            try:
                parts = default_val.rsplit(" ", 1)
                self._pie_month = MONTHS.index(parts[0]) + 1
                self._pie_year  = int(parts[1])
            except (ValueError, IndexError):
                pass

        self._pie_period_var = tk.StringVar(value=default_val)
        self._pie_period_cb  = ttk.Combobox(
            nav, textvariable=self._pie_period_var,
            values=options, state="readonly",
            width=14, font=("Segoe UI", 9))
        self._pie_period_cb.pack(side="left")
        self._pie_period_cb.bind("<<ComboboxSelected>>", self._on_pie_select)

    def _on_pie_select(self, _e=None):
        val = self._pie_period_var.get()
        try:
            parts = val.rsplit(" ", 1)
            self._pie_month = MONTHS.index(parts[0]) + 1
            self._pie_year  = int(parts[1])
        except (ValueError, IndexError):
            return
        self._redraw_pie()

    def _refresh_pie_period_options(self):
        """Update the period combobox values to reflect current DB contents."""
        if self._pie_period_cb is None:
            return
        options = self._get_expense_month_years()
        self._pie_period_cb["values"] = options
        current = self._pie_period_var.get()
        if current not in options:
            new_val = options[0]
            self._pie_period_var.set(new_val)
            try:
                parts = new_val.rsplit(" ", 1)
                self._pie_month = MONTHS.index(parts[0]) + 1
                self._pie_year  = int(parts[1])
            except (ValueError, IndexError):
                pass

    def _redraw_pie(self):
        if not MPL:
            return
        for w in self._pie_chart_area.winfo_children():
            w.destroy()
        self._mpl_canvases = [c for c in self._mpl_canvases
                               if c.get_tk_widget().winfo_exists()]
        self._draw_donut_chart()

    # ── Draw charts ───────────────────────────────────────────────────────────

    def _draw_charts(self):
        if not MPL:
            return
        for w in self._line_card.winfo_children():
            w.destroy()
        self._mpl_canvases.clear()
        self._draw_line_chart()
        self._redraw_pie()

    # ── Line chart (replaces bar chart) ───────────────────────────────────────

    def _draw_line_chart(self):
        """Income vs Expenses as smooth area lines over the last 6 months."""
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
        inc_vals, exp_vals, labels = [], [], []
        for y, m in months:
            prefix = f"{y}-{m:02d}"
            inc_vals.append(sum(r["amount"] for r in all_inc
                                if r["date"].startswith(prefix)))
            exp_vals.append(sum(r["amount"] for r in all_exp
                                if r["date"].startswith(prefix)))
            labels.append(datetime(y, m, 1).strftime("%b %y"))

        fig = Figure(figsize=(5.6, 3.2), dpi=96, facecolor="white")
        ax  = fig.add_subplot(111)
        fig.subplots_adjust(left=0.12, right=0.97, top=0.88, bottom=0.15)

        x = list(range(len(labels)))

        # Income line — indigo with filled area
        ax.plot(x, inc_vals, color="#4f46e5", linewidth=2.2,
                marker="o", markersize=5, zorder=3, label="Income")
        ax.fill_between(x, inc_vals, alpha=0.12, color="#4f46e5")

        # Expenses line — teal/cyan with filled area
        ax.plot(x, exp_vals, color="#06b6d4", linewidth=2.2,
                marker="o", markersize=5, zorder=3, label="Expenses")
        ax.fill_between(x, exp_vals, alpha=0.12, color="#06b6d4")

        # Dot labels at each point
        for xi, (iv, ev) in enumerate(zip(inc_vals, exp_vals)):
            if iv > 0:
                ax.annotate(f"{iv:,.0f}", (xi, iv),
                            textcoords="offset points", xytext=(0, 7),
                            ha="center", fontsize=6.5, color="#4f46e5")
            if ev > 0:
                ax.annotate(f"{ev:,.0f}", (xi, ev),
                            textcoords="offset points", xytext=(0, -12),
                            ha="center", fontsize=6.5, color="#06b6d4")

        ax.set_title("Income vs Expenses (6 months)", fontsize=11,
                     fontweight="bold", color="#1e293b", pad=8)
        ax.set_xticks(x)
        ax.set_xticklabels(labels, fontsize=8)
        ax.tick_params(axis="y", labelsize=8)
        ax.yaxis.set_major_formatter(
            matplotlib.ticker.FuncFormatter(lambda v, _: f"RM {v:,.0f}"))
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.set_facecolor("#f8fafc")
        ax.grid(axis="y", color="#e2e8f0", linewidth=0.7, linestyle="--")
        ax.legend(fontsize=8, framealpha=0, loc="upper right")

        canvas = FigureCanvasTkAgg(fig, master=self._line_card)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)
        self._mpl_canvases.append(canvas)
        plt.close(fig)

    # ── Donut chart (image-2 style) ────────────────────────────────────────────

    def _draw_donut_chart(self):
        """
        Donut with 'Total RM X' in centre + a category breakdown list below,
        matching the GOfinance cash-flow style (image 2).
        """
        period_str = f"{MONTHS[self._pie_month - 1]} {self._pie_year}"
        prefix     = f"{self._pie_year}-{self._pie_month:02d}"

        # Build totals + transaction counts
        totals = defaultdict(float)
        counts = defaultdict(int)
        for r in self.db.get_expenses():
            if r["date"].startswith(prefix):
                totals[r["category"]] += r["amount"]
                counts[r["category"]] += 1

        data = {k: v for k, v in totals.items() if v > 0}
        area = self._pie_chart_area

        if not data:
            tk.Label(area,
                     text=f"No expenses for {period_str}.",
                     font=("Segoe UI", 9, "italic"),
                     bg=C_CARD, fg=C_TEXT_MED
                     ).pack(expand=True, pady=30)
            return

        # Sort by amount descending
        sorted_cats = sorted(data.items(), key=lambda x: x[1], reverse=True)
        total       = sum(v for _, v in sorted_cats)
        cat_keys    = [k for k, _ in sorted_cats]
        values      = [v for _, v in sorted_cats]
        colors      = [_PALETTE[i % len(_PALETTE)] for i in range(len(values))]

        # ── Donut chart (matplotlib) ──────────────────
        fig = Figure(figsize=(3.6, 2.6), dpi=96, facecolor="white")
        ax  = fig.add_subplot(111)
        fig.subplots_adjust(left=0.05, right=0.95, top=0.95, bottom=0.05)

        wedges, _ = ax.pie(
            values,
            colors=colors,
            startangle=90,
            wedgeprops={"linewidth": 2, "edgecolor": "white"},
            labels=None,
        )

        # White centre hole
        centre = plt.Circle((0, 0), 0.58, fc="white")
        ax.add_patch(centre)

        # Centre text: "Total\nRM X"
        ax.text(0, 0.08, "Total",
                ha="center", va="center",
                fontsize=8, color="#64748b")
        ax.text(0, -0.18, f"RM {total:,.2f}",
                ha="center", va="center",
                fontsize=9, fontweight="bold", color="#1e293b")

        # Small category labels outside top wedges only (top 3)
        for i, (wedge, key, val) in enumerate(
                zip(wedges, cat_keys, values)):
            if i >= 3:
                break
            ang   = (wedge.theta1 + wedge.theta2) / 2
            import math
            x_tip = 0.85 * math.cos(math.radians(ang))
            y_tip = 0.85 * math.sin(math.radians(ang))
            x_lbl = 1.18 * math.cos(math.radians(ang))
            y_lbl = 1.18 * math.sin(math.radians(ang))
            label = EXPENSE_CATS.get(key, (key,))[0]
            label = label if len(label) <= 12 else label[:11] + "…"
            ax.annotate(
                label,
                xy=(x_tip, y_tip),
                xytext=(x_lbl, y_lbl),
                fontsize=6.5,
                color="#334155",
                ha="center",
                va="center",
                arrowprops=dict(arrowstyle="-", color="#94a3b8",
                                lw=0.8, shrinkA=0, shrinkB=2),
            )

        canvas = FigureCanvasTkAgg(fig, master=area)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="x")
        self._mpl_canvases.append(canvas)
        plt.close(fig)

        # ── Category breakdown list (tkinter) ─────────
        list_frame = tk.Frame(area, bg=C_CARD)
        list_frame.pack(fill="x", padx=4, pady=(4, 6))

        for i, (cat_key, amount) in enumerate(sorted_cats):
            color      = _PALETTE[i % len(_PALETTE)]
            cat_label  = EXPENSE_CATS.get(cat_key, (cat_key,))[0]
            pct        = (amount / total * 100) if total > 0 else 0
            tx_count   = counts[cat_key]

            row = tk.Frame(list_frame, bg=C_CARD)
            row.pack(fill="x", pady=(0, 6))

            # Top line: coloured dot  +  name  +  RM amount
            top = tk.Frame(row, bg=C_CARD)
            top.pack(fill="x")

            # Coloured circle dot
            dot_canvas = tk.Canvas(top, width=10, height=10,
                                   bg=C_CARD, highlightthickness=0)
            dot_canvas.create_oval(1, 1, 9, 9, fill=color, outline="")
            dot_canvas.pack(side="left", padx=(0, 6), pady=2)

            tk.Label(top, text=cat_label,
                     font=("Segoe UI", 9, "bold"),
                     bg=C_CARD, fg=C_TEXT).pack(side="left")

            tk.Label(top, text=f"RM {amount:,.2f}",
                     font=("Segoe UI", 9, "bold"),
                     bg=C_CARD, fg=C_TEXT).pack(side="right")

            # Second line: percentage + transaction count
            sub = tk.Frame(row, bg=C_CARD)
            sub.pack(fill="x", pady=(1, 0))
            tk.Label(sub,
                     text=f"{pct:.0f}%  ({tx_count} transaction{'s' if tx_count != 1 else ''})",
                     font=("Segoe UI", 8),
                     bg=C_CARD, fg=C_TEXT_MED).pack(side="left", padx=(16, 0))

            # Progress bar
            bar_bg = tk.Frame(row, bg="#e2e8f0", height=5)
            bar_bg.pack(fill="x", padx=(16, 0), pady=(3, 0))
            bar_bg.pack_propagate(False)

            # Draw fill after bar_bg is rendered (use after to get width)
            def _draw_fill(frame=bar_bg, pct_val=pct, c=color):
                frame.update_idletasks()
                total_w = frame.winfo_width()
                fill_w  = max(4, int(total_w * pct_val / 100))
                fill    = tk.Frame(frame, bg=c, height=5)
                fill.place(x=0, y=0, width=fill_w, height=5)

            bar_bg.after(50, _draw_fill)

            # Divider line (except after last item)
            if i < len(sorted_cats) - 1:
                tk.Frame(list_frame, bg=C_BORDER, height=1
                         ).pack(fill="x", pady=(2, 0))

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
        self._refresh_pie_period_options()
        self._draw_charts()

        for item in self._inc_tree.get_children():
            self._inc_tree.delete(item)
        for row in self.db.get_income()[:8]:
            self._inc_tree.insert("", "end", values=(
                row["name"], row["category"].capitalize(),
                fmt_rm(row["amount"])))

        for item in self._exp_tree.get_children():
            self._exp_tree.delete(item)
        for row in self.db.get_expenses()[:8]:
            cat = EXPENSE_CATS.get(row["category"], ("Others",))[0][:22]
            self._exp_tree.insert("", "end", values=(
                row["name"], cat, fmt_rm(row["amount"])))