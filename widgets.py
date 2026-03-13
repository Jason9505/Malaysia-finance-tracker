# widgets.py
# Shared reusable Tkinter widgets and dialogs used across all pages.

import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from datetime import date, datetime

from config import (C_BG, C_CARD, C_PRIMARY, C_PRIMARY_LT,
                    C_SUCCESS, C_DANGER, C_TEXT, C_TEXT_MED, C_TEXT_LT, C_BORDER)
from utils import save_receipt, open_file, PIL_AVAILABLE

try:
    from PIL import Image, ImageTk
except ImportError:
    pass

_MONTHS = ["Jan","Feb","Mar","Apr","May","Jun",
           "Jul","Aug","Sep","Oct","Nov","Dec"]


# ── Layout primitives ─────────────────────────────────────────────────────────

class Card(tk.Frame):
    """Plain white card frame."""
    def __init__(self, parent, **kw):
        kw.setdefault("bg", C_CARD)
        kw.setdefault("relief", "flat")
        kw.setdefault("bd", 0)
        super().__init__(parent, **kw)


class ScrollFrame(tk.Frame):
    """Vertically-scrollable container. Place children inside self.inner."""
    def __init__(self, parent, **kw):
        kw.setdefault("bg", C_BG)
        super().__init__(parent, **kw)
        self.canvas  = tk.Canvas(self, bg=C_BG, bd=0, highlightthickness=0)
        self.vscroll = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.inner   = tk.Frame(self.canvas, bg=C_BG)
        self.inner.bind("<Configure>", self._on_inner_configure)
        self.canvas.create_window((0, 0), window=self.inner, anchor="nw", tags="inner")
        self.canvas.configure(yscrollcommand=self.vscroll.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.vscroll.pack(side="right", fill="y")
        self.canvas.bind("<Configure>", self._on_canvas_resize)
        for seq in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
            self.canvas.bind(seq, self._scroll)

    def _on_inner_configure(self, _e):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_canvas_resize(self, event):
        self.canvas.itemconfig("inner", width=event.width)

    def _scroll(self, event):
        if event.num == 4 or event.delta > 0:
            self.canvas.yview_scroll(-1, "units")
        else:
            self.canvas.yview_scroll(1, "units")


# ── Button helper ─────────────────────────────────────────────────────────────

def make_button(parent, text, command, bg=C_PRIMARY, fg="white",
                font=("Segoe UI", 9, "bold"), padx=10, pady=4, **kw):
    return tk.Button(parent, text=text, command=command, bg=bg, fg=fg,
                     relief="flat", font=font, cursor="hand2",
                     padx=padx, pady=pady, **kw)


# ── Date picker ───────────────────────────────────────────────────────────────

class DatePickerFrame(tk.Frame):
    """
    Inline Day / Month / Year picker — no free-typing required.
    Call get_date() to retrieve 'YYYY-MM-DD', or None if the
    combination is impossible (e.g. Feb 30).
    """
    def __init__(self, parent, initial_date=None, **kw):
        kw.setdefault("bg", C_CARD)
        super().__init__(parent, **kw)

        try:
            dt = (datetime.strptime(initial_date, "%Y-%m-%d").date()
                  if initial_date else date.today())
        except (ValueError, TypeError):
            dt = date.today()

        today_yr = date.today().year

        self._day_var = tk.StringVar(value=f"{dt.day:02d}")
        tk.Spinbox(self, from_=1, to=31, width=3,
                   textvariable=self._day_var,
                   font=("Segoe UI", 10), justify="center",
                   relief="solid", bd=1).pack(side="left")

        tk.Label(self, text=" / ", bg=C_CARD,
                 font=("Segoe UI", 10), fg=C_TEXT_MED).pack(side="left")

        self._month_var = tk.StringVar(value=_MONTHS[dt.month - 1])
        ttk.Combobox(self, textvariable=self._month_var,
                     values=_MONTHS, state="readonly",
                     width=5, font=("Segoe UI", 10)).pack(side="left")

        tk.Label(self, text=" / ", bg=C_CARD,
                 font=("Segoe UI", 10), fg=C_TEXT_MED).pack(side="left")

        self._year_var = tk.StringVar(value=str(dt.year))
        tk.Spinbox(self, from_=today_yr - 10, to=today_yr + 5, width=5,
                   textvariable=self._year_var,
                   font=("Segoe UI", 10), justify="center",
                   relief="solid", bd=1).pack(side="left")

    def get_date(self):
        """Return 'YYYY-MM-DD', or None if the date is impossible."""
        try:
            day   = int(self._day_var.get())
            month = _MONTHS.index(self._month_var.get()) + 1
            year  = int(self._year_var.get())
            return date(year, month, day).strftime("%Y-%m-%d")
        except (ValueError, IndexError):
            return None

    def set_date(self, date_str):
        try:
            dt = datetime.strptime(date_str, "%Y-%m-%d").date()
            self._day_var.set(f"{dt.day:02d}")
            self._month_var.set(_MONTHS[dt.month - 1])
            self._year_var.set(str(dt.year))
        except (ValueError, TypeError):
            pass


# ── Column sorting helper ─────────────────────────────────────────────────────

def add_column_sorting(tree, numeric_cols=None, skip_cols=None):
    """
    Attach click-to-sort to every heading in `tree`.

    numeric_cols : column ids to compare numerically (strips 'RM', commas).
    skip_cols    : column ids to leave unsortable (hidden _id / _key cols).
    Headings show a ↑ or ↓ arrow to indicate the current sort direction.
    """
    numeric_cols = set(numeric_cols or [])
    skip_cols    = set(skip_cols or ["_id", "_key"])
    _asc = {}

    def _sort(col):
        asc = not _asc.get(col, False)
        _asc[col] = asc
        items = [(tree.set(ch, col), ch) for ch in tree.get_children("")]

        if col in numeric_cols:
            def _num(pair):
                try:
                    return float(pair[0].replace("RM","").replace(",","").strip())
                except ValueError:
                    return 0.0
            items.sort(key=_num, reverse=not asc)
        else:
            items.sort(key=lambda p: p[0].lower(), reverse=not asc)

        for i, (_, ch) in enumerate(items):
            tree.move(ch, "", i)

        for c in tree["columns"]:
            if c in skip_cols:
                continue
            raw   = tree.heading(c)["text"].rstrip(" ↑↓")
            arrow = " ↑" if (c == col and asc) else (" ↓" if c == col else "")
            tree.heading(c, text=raw + arrow)

    for col in tree["columns"]:
        if col not in skip_cols:
            tree.heading(col, command=lambda c=col: _sort(c))


# ── Add / Edit entry dialog ───────────────────────────────────────────────────

class AddEntryDialog(tk.Toplevel):
    """
    Modal dialog to add or edit income / expense entries.

    Pass a `prefill` dict with keys name / amount / date / notes / receipt
    to open in edit mode. on_save receives (name, amount, date_str, notes, receipt).
    """

    def __init__(self, parent, title, on_save, prefill=None):
        super().__init__(parent)
        self.title(title)
        self.configure(bg=C_CARD)
        self.resizable(False, False)
        self.grab_set()
        self.transient(parent)

        self._on_save          = on_save
        self._prefill          = prefill or {}
        self._receipt_src      = ""
        self._existing_receipt = self._prefill.get("receipt", "")

        self._build_ui(title)
        self._center(parent)

    def _build_ui(self, title):
        hdr = tk.Frame(self, bg=C_PRIMARY, padx=20, pady=14)
        hdr.pack(fill="x")
        tk.Label(hdr, text=title, font=("Segoe UI", 13, "bold"),
                 bg=C_PRIMARY, fg="white").pack(side="left")
        tk.Button(hdr, text="✕", bg=C_PRIMARY, fg="white", relief="flat",
                  font=("Segoe UI", 11), cursor="hand2",
                  command=self.destroy).pack(side="right")

        body = tk.Frame(self, bg=C_CARD, padx=24, pady=20)
        body.pack(fill="both", expand=True)
        self._add_fields(body)

        btn_lbl = "💾  Save Changes" if self._prefill else "💾  Save Entry"
        make_button(body, btn_lbl, self._on_click_save,
                    font=("Segoe UI", 11, "bold"), pady=10
                    ).pack(fill="x", pady=(14, 0))

    def _add_fields(self, body):
        self._lbl(body, "Name / Description")
        self.name_var = tk.StringVar(value=self._prefill.get("name", ""))
        self._ent(body, self.name_var)

        self._lbl(body, "Amount (RM)")
        amt_val = str(self._prefill["amount"]) if self._prefill.get("amount") else ""
        self.amt_var = tk.StringVar(value=amt_val)
        self._ent(body, self.amt_var)

        self._lbl(body, "Date")
        self._date_picker = DatePickerFrame(
            body, initial_date=self._prefill.get("date"))
        self._date_picker.pack(anchor="w", pady=(2, 0))

        self._lbl(body, "Notes (optional)")
        self.notes_var = tk.StringVar(value=self._prefill.get("notes", ""))
        self._ent(body, self.notes_var)

        self._add_receipt_row(body)

    def _lbl(self, p, text):
        tk.Label(p, text=text, font=("Segoe UI", 9, "bold"),
                 bg=C_CARD, fg=C_TEXT_MED).pack(anchor="w", pady=(8, 1))

    def _ent(self, p, var):
        tk.Entry(p, textvariable=var, font=("Segoe UI", 10),
                 relief="solid", bd=1, bg="white",
                 highlightthickness=1, highlightcolor=C_PRIMARY
                 ).pack(fill="x", ipady=5)

    def _add_receipt_row(self, parent):
        self._lbl(parent, "Receipt / Invoice (image or PDF)")
        row = tk.Frame(parent, bg=C_CARD)
        row.pack(fill="x", pady=(0, 4))

        self._rec_lbl = tk.Label(row, text="No file selected",
                                 font=("Segoe UI", 9), bg=C_CARD, fg=C_TEXT_LT)
        self._rec_lbl.pack(side="left", fill="x", expand=True)
        make_button(row, "Browse", self._browse,
                    bg=C_BG, fg=C_TEXT, font=("Segoe UI", 9),
                    pady=3, padx=8).pack(side="right")

        if self._existing_receipt:
            if os.path.exists(self._existing_receipt):
                name = os.path.basename(self._existing_receipt)
                disp = name if len(name) <= 32 else "..." + name[-29:]
                self._rec_lbl.config(text=f"Attached: {disp}", fg=C_SUCCESS)
            else:
                self._rec_lbl.config(
                    text="⚠  Receipt file missing — will be cleared on save",
                    fg=C_DANGER)

    def _browse(self):
        path = filedialog.askopenfilename(
            title="Select Receipt / Invoice",
            filetypes=[
                ("All Supported", "*.png *.jpg *.jpeg *.bmp *.gif *.pdf *.webp"),
                ("Images",        "*.png *.jpg *.jpeg *.bmp *.gif *.webp"),
                ("PDF Files",     "*.pdf"),
                ("All Files",     "*.*"),
            ])
        if path:
            self._receipt_src = path
            name = os.path.basename(path)
            disp = name if len(name) <= 32 else "..." + name[-29:]
            self._rec_lbl.config(text=disp, fg=C_SUCCESS)

    def _on_click_save(self):
        name    = self.name_var.get().strip()
        amt_str = self.amt_var.get().strip()
        notes   = self.notes_var.get().strip()
        dt_str  = self._date_picker.get_date()

        if not name:
            messagebox.showwarning("Required", "Please enter a name.", parent=self)
            return

        try:
            amount = float(amt_str.replace(",", ""))
            if amount <= 0:
                raise ValueError
        except ValueError:
            messagebox.showwarning("Invalid Amount",
                                   "Please enter a valid positive amount.",
                                   parent=self)
            return

        if dt_str is None:
            messagebox.showwarning(
                "Invalid Date",
                "The date is not valid.\n\n"
                "Check that the day exists for that month\n"
                "(e.g. Feb 30 and Apr 31 do not exist).",
                parent=self)
            return

        if self._receipt_src:
            receipt = save_receipt(self._receipt_src)
        elif self._existing_receipt and os.path.exists(self._existing_receipt):
            receipt = self._existing_receipt
        else:
            receipt = ""   # missing file is silently cleared

        self._on_save(name, amount, dt_str, notes, receipt)
        self.destroy()

    def _center(self, parent):
        self.update_idletasks()
        pw = parent.winfo_width();  ph = parent.winfo_height()
        px = parent.winfo_rootx(); py = parent.winfo_rooty()
        dw = self.winfo_width();   dh = self.winfo_height()
        self.geometry(f"+{px + (pw - dw) // 2}+{py + (ph - dh) // 2}")


# ── Receipt viewer ────────────────────────────────────────────────────────────

class ViewReceiptDialog(tk.Toplevel):
    """Show an image receipt inline, or open a PDF in the system viewer."""

    def __init__(self, parent, path, title="Receipt"):
        super().__init__(parent)
        self.title(title)
        self.configure(bg=C_CARD)
        self.resizable(True, True)
        self.grab_set()
        self.transient(parent)

        frame = tk.Frame(self, bg=C_CARD, padx=16, pady=16)
        frame.pack(fill="both", expand=True)

        ext = os.path.splitext(path)[1].lower()
        if ext == ".pdf":
            self._show_pdf(frame, path)
        elif PIL_AVAILABLE:
            self._show_image(frame, path)
        else:
            self._show_fallback(frame, path)

    def _show_pdf(self, f, path):
        tk.Label(f, text="PDF Receipt",
                 font=("Segoe UI", 12, "bold"), bg=C_CARD, fg=C_TEXT).pack()
        tk.Label(f, text=os.path.basename(path),
                 font=("Segoe UI", 9), bg=C_CARD, fg=C_TEXT_MED).pack(pady=4)
        make_button(f, "Open PDF in Viewer", lambda: open_file(path),
                    font=("Segoe UI", 10, "bold"), pady=8, padx=12).pack(pady=8)

    def _show_image(self, f, path):
        try:
            img = Image.open(path)
            img.thumbnail((640, 480), Image.LANCZOS)
            photo = ImageTk.PhotoImage(img)
            lbl = tk.Label(f, image=photo, bg=C_CARD)
            lbl.image = photo
            lbl.pack()
        except Exception:
            tk.Label(f, text="Cannot display image.",
                     bg=C_CARD, fg=C_DANGER).pack()

    def _show_fallback(self, f, path):
        tk.Label(f, text="Install Pillow to preview images.",
                 bg=C_CARD, fg=C_TEXT_MED).pack()
        make_button(f, "Open File", lambda: open_file(path),
                    font=("Segoe UI", 10), pady=6, padx=12).pack(pady=8)