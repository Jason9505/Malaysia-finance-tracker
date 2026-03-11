# ─── widgets.py ──────────────────────────────────────────────────────────────
# Shared, reusable Tkinter widgets and dialogs used across all pages.

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
from datetime import date

from config import (
    C_BG, C_CARD, C_PRIMARY, C_SUCCESS, C_DANGER,
    C_TEXT, C_TEXT_MED, C_TEXT_LT, C_BORDER,
)
from utils import save_receipt, open_file, PIL_AVAILABLE

try:
    from PIL import Image, ImageTk
except ImportError:
    pass


# ── Layout primitives ─────────────────────────────────────────────────────────

class Card(tk.Frame):
    """White card with a subtle border."""
    def __init__(self, parent, **kw):
        kw.setdefault("bg", C_CARD)
        kw.setdefault("relief", "flat")
        kw.setdefault("bd", 0)
        super().__init__(parent, **kw)


class ScrollFrame(tk.Frame):
    """
    A vertically-scrollable container.
    Place child widgets inside ``self.inner``.
    """
    def __init__(self, parent, **kw):
        kw.setdefault("bg", C_BG)
        super().__init__(parent, **kw)

        self.canvas  = tk.Canvas(self, bg=C_BG, bd=0, highlightthickness=0)
        self.vscroll = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.inner   = tk.Frame(self.canvas, bg=C_BG)

        self.inner.bind("<Configure>", self._on_inner_configure)
        self._win_id = self.canvas.create_window((0, 0), window=self.inner,
                                                  anchor="nw", tags="inner")
        self.canvas.configure(yscrollcommand=self.vscroll.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.vscroll.pack(side="right", fill="y")

        self.canvas.bind("<Configure>", self._on_canvas_resize)
        self._bind_mousewheel(self.canvas)

    def _on_inner_configure(self, _event):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_canvas_resize(self, event):
        self.canvas.itemconfig("inner", width=event.width)

    def _bind_mousewheel(self, widget):
        widget.bind("<MouseWheel>", self._scroll)
        widget.bind("<Button-4>",   self._scroll)
        widget.bind("<Button-5>",   self._scroll)

    def _scroll(self, event):
        if event.num == 4 or event.delta > 0:
            self.canvas.yview_scroll(-1, "units")
        else:
            self.canvas.yview_scroll(1, "units")


# ── Styled button helper ──────────────────────────────────────────────────────

def make_button(parent, text, command, bg=C_PRIMARY, fg="white",
                font=("Segoe UI", 9, "bold"), padx=10, pady=4, **kw):
    """Create a flat, cursor-hand styled button."""
    btn = tk.Button(parent, text=text, command=command,
                    bg=bg, fg=fg, relief="flat", font=font,
                    cursor="hand2", padx=padx, pady=pady, **kw)
    return btn


# ── Treeview factory ──────────────────────────────────────────────────────────

def make_tree(parent, columns, heights=5):
    """
    Build a ttk.Treeview with standard column definitions.

    ``columns`` is a list of (col_id, display_name, width, anchor, stretch) tuples.
    The hidden 'id' column is appended automatically.
    """
    col_ids = [c[0] for c in columns] + ["_id"]
    tree = ttk.Treeview(parent, columns=col_ids, show="headings",
                        height=heights, selectmode="browse")
    for col_id, display, width, anchor, stretch in columns:
        tree.heading(col_id, text=display)
        tree.column(col_id, width=width, anchor=anchor, stretch=stretch, minwidth=60)
    # Hidden ID column
    tree.heading("_id", text="")
    tree.column("_id", width=0, stretch=False, minwidth=0)
    return tree


# ── Dialogs ───────────────────────────────────────────────────────────────────

class AddEntryDialog(tk.Toplevel):
    """
    Generic modal dialog for adding income or expense entries.

    Parameters
    ----------
    parent      : parent Tk window
    title       : dialog title string
    on_save     : callback(category, name, amount, date_str, notes, receipt_path)
    default_cat : pre-selected category key (optional)
    """

    def __init__(self, parent, title, on_save, default_cat=None):
        super().__init__(parent)
        self.title(title)
        self.configure(bg=C_CARD)
        self.resizable(False, False)
        self.grab_set()
        self.transient(parent)

        self._on_save = on_save
        self._receipt_src = ""

        self._build_ui(title)
        self._center(parent)

    # ── UI construction ───────────────────────────────

    def _build_ui(self, title):
        # Header bar
        hdr = tk.Frame(self, bg=C_PRIMARY, padx=20, pady=14)
        hdr.pack(fill="x")
        tk.Label(hdr, text=title, font=("Segoe UI", 13, "bold"),
                 bg=C_PRIMARY, fg="white").pack(side="left")
        tk.Button(hdr, text="✕", bg=C_PRIMARY, fg="white", relief="flat",
                  font=("Segoe UI", 11), cursor="hand2",
                  command=self.destroy).pack(side="right")

        # Body
        body = tk.Frame(self, bg=C_CARD, padx=24, pady=20)
        body.pack(fill="both", expand=True)
        self._body = body
        self._add_fields(body)

        # Save button
        make_button(body, "💾  Save Entry", self._on_click_save,
                    font=("Segoe UI", 11, "bold"), pady=10
                    ).pack(fill="x", pady=(14, 0))

    def _add_fields(self, body):
        """Override in subclasses to add extra fields above the standard ones."""
        self._field_label(body, "Name / Description")
        self.name_var = tk.StringVar()
        self._entry(body, self.name_var)

        self._field_label(body, "Amount (RM)")
        self.amt_var = tk.StringVar()
        self._entry(body, self.amt_var)

        self._field_label(body, "Date (YYYY-MM-DD)")
        self.date_var = tk.StringVar(value=date.today().strftime("%Y-%m-%d"))
        self._entry(body, self.date_var)

        self._field_label(body, "Notes (optional)")
        self.notes_var = tk.StringVar()
        self._entry(body, self.notes_var)

        self._add_receipt_row(body)

    def _field_label(self, parent, text):
        tk.Label(parent, text=text, font=("Segoe UI", 9, "bold"),
                 bg=C_CARD, fg=C_TEXT_MED).pack(anchor="w", pady=(8, 1))

    def _entry(self, parent, variable):
        tk.Entry(parent, textvariable=variable, font=("Segoe UI", 10),
                 relief="solid", bd=1, bg="white",
                 highlightthickness=1, highlightcolor=C_PRIMARY
                 ).pack(fill="x", ipady=5)

    def _add_receipt_row(self, parent):
        self._field_label(parent, "Receipt / Invoice (Image or PDF)")
        row = tk.Frame(parent, bg=C_CARD)
        row.pack(fill="x", pady=(0, 4))
        self._receipt_lbl = tk.Label(row, text="No file selected",
                                     font=("Segoe UI", 9), bg=C_CARD, fg=C_TEXT_LT)
        self._receipt_lbl.pack(side="left", fill="x", expand=True)
        make_button(row, "📎 Browse", self._browse_receipt,
                    bg=C_BG, fg=C_TEXT, font=("Segoe UI", 9),
                    pady=3, padx=8).pack(side="right")

    # ── Actions ───────────────────────────────────────

    def _browse_receipt(self):
        path = filedialog.askopenfilename(
            title="Select Receipt / Invoice",
            filetypes=[
                ("All Supported", "*.png *.jpg *.jpeg *.bmp *.gif *.pdf *.webp"),
                ("Images", "*.png *.jpg *.jpeg *.bmp *.gif *.webp"),
                ("PDF Files", "*.pdf"),
                ("All Files", "*.*"),
            ]
        )
        if path:
            self._receipt_src = path
            name = os.path.basename(path)
            display = name if len(name) <= 32 else "…" + name[-29:]
            self._receipt_lbl.config(text=display, fg=C_SUCCESS)

    def _on_click_save(self):
        name    = self.name_var.get().strip()
        amt_str = self.amt_var.get().strip()
        dt_str  = self.date_var.get().strip()
        notes   = self.notes_var.get().strip()

        if not name:
            messagebox.showwarning("Required", "Please enter a name.", parent=self)
            return
        try:
            amount = float(amt_str.replace(",", ""))
            if amount <= 0:
                raise ValueError
        except ValueError:
            messagebox.showwarning("Invalid Amount",
                                   "Please enter a valid positive amount.", parent=self)
            return
        try:
            from datetime import datetime
            datetime.strptime(dt_str, "%Y-%m-%d")
        except ValueError:
            messagebox.showwarning("Invalid Date",
                                   "Date must be in YYYY-MM-DD format.", parent=self)
            return

        stored_receipt = save_receipt(self._receipt_src) if self._receipt_src else ""
        self._on_save(name, amount, dt_str, notes, stored_receipt)
        self.destroy()

    # ── Positioning ───────────────────────────────────

    def _center(self, parent):
        self.update_idletasks()
        pw = parent.winfo_width()
        ph = parent.winfo_height()
        px = parent.winfo_rootx()
        py = parent.winfo_rooty()
        dw = self.winfo_width()
        dh = self.winfo_height()
        self.geometry(f"+{px + (pw - dw) // 2}+{py + (ph - dh) // 2}")


class ViewReceiptDialog(tk.Toplevel):
    """Display an image receipt inline, or provide an 'Open' button for PDFs."""

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

    def _show_pdf(self, frame, path):
        tk.Label(frame, text="📄 PDF Receipt",
                 font=("Segoe UI", 12, "bold"), bg=C_CARD, fg=C_TEXT).pack()
        tk.Label(frame, text=os.path.basename(path),
                 font=("Segoe UI", 9), bg=C_CARD, fg=C_TEXT_MED).pack(pady=4)
        make_button(frame, "Open PDF in Viewer", lambda: open_file(path),
                    font=("Segoe UI", 10, "bold"), pady=8, padx=12
                    ).pack(pady=8)

    def _show_image(self, frame, path):
        try:
            img = Image.open(path)
            img.thumbnail((640, 480), Image.LANCZOS)
            photo = ImageTk.PhotoImage(img)
            lbl = tk.Label(frame, image=photo, bg=C_CARD)
            lbl.image = photo   # keep reference alive
            lbl.pack()
        except Exception:
            tk.Label(frame, text="Cannot display image.",
                     bg=C_CARD, fg=C_DANGER).pack()

    def _show_fallback(self, frame, path):
        tk.Label(frame, text="Install Pillow to preview images.",
                 bg=C_CARD, fg=C_TEXT_MED).pack()
        make_button(frame, "Open File", lambda: open_file(path),
                    font=("Segoe UI", 10), pady=6, padx=12).pack(pady=8)
