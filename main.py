#!/usr/bin/env python3
# ─── main.py ─────────────────────────────────────────────────────────────────
# Entry point for MyKad Financial Tracker.
# Builds the root window, sidebar navigation, and hosts all page frames.
#
# Run:
#   python3 main.py
#
# Requirements:
#   Python 3.8+, tkinter (stdlib)
#   Optional: pip install pillow   (for receipt image previews)

import sys
import os

# ── Path fix ──────────────────────────────────────────────────────────────────
# Add the folder that contains main.py to sys.path so that database.py,
# config.py, utils.py, widgets.py and the pages/ package can all be found,
# no matter which working directory Python was launched from.
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
if _THIS_DIR not in sys.path:
    sys.path.insert(0, _THIS_DIR)

# Uncomment the next two lines if you still get ModuleNotFoundError,
# to see exactly where Python is looking for files:
# print("Script folder:", _THIS_DIR)
# print("Files found:", os.listdir(_THIS_DIR))

import tkinter as tk
from tkinter import ttk
from datetime import date

from config   import (C_BG, C_CARD, C_SIDEBAR, C_SIDEBAR_H, C_SIDEBAR_ACT,
                      C_PRIMARY, NAV_ITEMS, apply_theme)
from database import DB
from pages    import DashboardPage, IncomePage, ExpensesPage, TaxPage, SettingsPage


class App(tk.Tk):
    """
    Root application window.

    Layout
    ──────
    column 0  │  Sidebar (fixed 220 px)
    column 1  │  Content area (expands to fill window)
    """

    def __init__(self):
        super().__init__()
        self.title("MyKad Financial Tracker – Malaysia")
        self.db = DB()

        # ── Apply saved theme BEFORE any page widgets are built ───────────────
        saved_theme = self.db.get_setting("theme", "light")
        apply_theme(saved_theme)

        # Propagate updated C_* colours to every already-imported module so
        # pages (which do `from config import C_BG, ...`) see the right palette
        # when they build their widgets for the first time (pages are lazy).
        import sys as _sys, config as _cfg
        _colour_keys = [k for k in vars(_cfg) if k.startswith("C_")]
        for _mod in list(_sys.modules.values()):
            if _mod is None or _mod is _cfg:
                continue
            for _k in _colour_keys:
                if hasattr(_mod, _k):
                    try:
                        setattr(_mod, _k, getattr(_cfg, _k))
                    except (AttributeError, TypeError):
                        pass

        self._set_geometry()
        import config as _cfg
        self.configure(bg=_cfg.C_BG)
        self._apply_styles()
        self._build_layout()

        # Page registry: key -> page widget (built lazily)
        self._pages: dict[str, tk.Widget] = {}
        self._current_page = ""

        self.show_page("dashboard")

    # ── Window setup ──────────────────────────────────────────────────────────

    def _set_geometry(self):
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        w  = min(1280, sw - 80)
        h  = min(820,  sh - 80)
        x  = (sw - w) // 2
        y  = (sh - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")
        self.minsize(720, 520)

    def _apply_styles(self):
        import config as _cfg
        s = ttk.Style(self)
        s.theme_use("clam")
        s.configure("Treeview",
                    background=_cfg.C_CARD,
                    foreground=_cfg.C_TEXT,
                    rowheight=38,
                    fieldbackground=_cfg.C_CARD,
                    borderwidth=0,
                    font=("Segoe UI", 9))
        s.configure("Treeview.Heading",
                    background=_cfg.C_BG,
                    foreground=_cfg.C_TEXT,
                    font=("Segoe UI", 9, "bold"),
                    relief="flat")
        s.map("Treeview",
              background=[("selected", _cfg.C_PRIMARY_LT)],
              foreground=[("selected", _cfg.C_PRIMARY)])
        s.configure("TScrollbar",
                    background=_cfg.C_BG,
                    troughcolor=_cfg.C_BG,
                    bordercolor=_cfg.C_BG,
                    arrowcolor=_cfg.C_TEXT_LT)
        s.configure("TCombobox",
                    fieldbackground=_cfg.C_CARD,
                    background=_cfg.C_CARD,
                    foreground=_cfg.C_TEXT,
                    arrowcolor=_cfg.C_TEXT_MED,
                    selectbackground=_cfg.C_PRIMARY_LT,
                    selectforeground=_cfg.C_TEXT)
        s.map("TCombobox",
              fieldbackground=[("readonly", _cfg.C_CARD)],
              foreground=[("readonly", _cfg.C_TEXT)])

    # ── Layout ────────────────────────────────────────────────────────────────

    def _build_layout(self):
        import config as _cfg
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        self._sidebar = tk.Frame(self, bg=_cfg.C_SIDEBAR, width=220)
        self._sidebar.grid(row=0, column=0, sticky="nsw")
        self._sidebar.grid_propagate(False)
        self._build_sidebar()

        self._content = tk.Frame(self, bg=_cfg.C_BG)
        self._content.grid(row=0, column=1, sticky="nsew")
        self._content.columnconfigure(0, weight=1)
        self._content.rowconfigure(0, weight=1)

    # ── Sidebar ───────────────────────────────────────────────────────────────

    def _build_sidebar(self):
        import config as _cfg
        sb = self._sidebar

        logo_frame = tk.Frame(sb, bg=_cfg.C_SIDEBAR, pady=20, padx=16)
        logo_frame.pack(fill="x")
        tk.Label(logo_frame, text="💰", font=("Segoe UI", 22),
                 bg=_cfg.C_SIDEBAR, fg="white").pack(side="left")
        brand = tk.Frame(logo_frame, bg=_cfg.C_SIDEBAR)
        brand.pack(side="left", padx=8)
        tk.Label(brand, text="Finance Tracker",
                 font=("Segoe UI", 11, "bold"),
                 bg=_cfg.C_SIDEBAR, fg="white").pack(anchor="w")
        tk.Label(brand, text="Malaysia Edition",
                 font=("Segoe UI", 8),
                 bg=_cfg.C_SIDEBAR, fg="#a5b4fc").pack(anchor="w")

        tk.Frame(sb, bg=_cfg.C_SIDEBAR_H, height=1).pack(fill="x", padx=16, pady=4)

        self._nav_buttons: dict[str, tk.Label] = {}
        for label, icon, page_key in NAV_ITEMS:
            btn = self._make_nav_button(sb, icon, label, page_key)
            self._nav_buttons[page_key] = btn

        tk.Label(sb, text=f"YA {date.today().year}",
                 font=("Segoe UI", 8), bg=_cfg.C_SIDEBAR, fg="#6366f1",
                 pady=12).pack(side="bottom")

    def _make_nav_button(self, parent, icon, label, page_key):
        import config as _cfg
        btn = tk.Label(
            parent,
            text=f"  {icon}  {label}",
            font=("Segoe UI", 10),
            bg=_cfg.C_SIDEBAR, fg="#c7d2fe",
            anchor="w", padx=16, pady=12, cursor="hand2"
        )
        btn.pack(fill="x")
        btn.bind("<Button-1>", lambda _e, k=page_key: self.show_page(k))
        btn.bind("<Enter>",    lambda _e, b=btn, k=page_key: self._nav_hover(b, k, True))
        btn.bind("<Leave>",    lambda _e, b=btn, k=page_key: self._nav_hover(b, k, False))
        return btn

    def _nav_hover(self, btn, page_key, entering):
        import config as _cfg
        if page_key == self._current_page:
            return
        btn.config(
            bg=_cfg.C_SIDEBAR_H if entering else _cfg.C_SIDEBAR,
            fg="white"          if entering else "#c7d2fe"
        )

    def _set_nav_active(self, active_key):
        import config as _cfg
        for key, btn in self._nav_buttons.items():
            if key == active_key:
                btn.config(bg=_cfg.C_SIDEBAR_ACT, fg="white",
                           font=("Segoe UI", 10, "bold"))
            else:
                btn.config(bg=_cfg.C_SIDEBAR, fg="#c7d2fe",
                           font=("Segoe UI", 10))

    # ── Page management ───────────────────────────────────────────────────────

    # Map page keys to their classes
    _PAGE_CLASSES = {
        "dashboard": DashboardPage,
        "income":    IncomePage,
        "expenses":  ExpensesPage,
        "tax":       TaxPage,
        "settings":  SettingsPage,
    }

    def show_page(self, key: str):
        """Switch to the given page, building it if necessary."""
        self._current_page = key
        self._set_nav_active(key)

        # Hide all currently visible pages
        for page in self._pages.values():
            page.grid_remove()

        # Build page on first visit
        if key not in self._pages:
            cls = self._PAGE_CLASSES[key]
            page = cls(self._content, self.db)
            page.grid(row=0, column=0, sticky="nsew")
            self._pages[key] = page
        else:
            # Refresh data before showing
            self.refresh_page(key)
            self._pages[key].grid()

    def refresh_page(self, key: str):
        """Refresh a page's data if it has already been built."""
        page = self._pages.get(key)
        if page and hasattr(page, "refresh"):
            page.refresh()


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    try:
        from PIL import Image  # noqa: F401
    except ImportError:
        print("Tip: Install Pillow for receipt image previews → pip install pillow")

    app = App()
    app.mainloop()