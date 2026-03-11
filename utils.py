# ─── utils.py ────────────────────────────────────────────────────────────────
# Helper functions: formatting, file I/O, receipt handling, tax calculation.

import os
import shutil
import platform
import subprocess
from datetime import datetime
from tkinter import messagebox

from config import RECEIPTS_DIR, TAX_BANDS

try:
    from PIL import Image, ImageTk
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


# ── Number formatting ─────────────────────────────────────────────────────────

def fmt_rm(value):
    """Format a number as Malaysian Ringgit string."""
    return f"RM {value:,.2f}"


# ── Receipt file handling ─────────────────────────────────────────────────────

def save_receipt(src_path):
    """
    Copy a receipt file into the app's receipts directory.
    Returns the stored path, or empty string if src_path is empty.
    """
    if not src_path:
        return ""
    ext = os.path.splitext(src_path)[1].lower()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    dest = os.path.join(RECEIPTS_DIR, f"receipt_{timestamp}{ext}")
    shutil.copy2(src_path, dest)
    return dest


def open_file(path):
    """Open a file using the OS default application."""
    if not path or not os.path.exists(path):
        messagebox.showwarning("File Not Found", "The receipt file could not be found.")
        return
    system = platform.system()
    try:
        if system == "Windows":
            os.startfile(path)
        elif system == "Darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])
    except Exception as exc:
        messagebox.showerror("Error", f"Cannot open file:\n{exc}")


def make_thumb(path, size=(48, 48)):
    """
    Return a PIL ImageTk thumbnail for image files.
    Returns None if Pillow is unavailable, path is invalid, or file is not an image.
    """
    if not PIL_AVAILABLE or not path or not os.path.exists(path):
        return None
    ext = os.path.splitext(path)[1].lower()
    if ext not in (".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp"):
        return None
    try:
        img = Image.open(path)
        img.thumbnail(size, Image.LANCZOS)
        return ImageTk.PhotoImage(img)
    except Exception:
        return None


# ── Malaysia income tax calculation ──────────────────────────────────────────

def calc_malaysia_tax(chargeable_income):
    """
    Calculate Malaysia income tax for YA 2025 using progressive tax bands.
    Bands and rates are defined in config.TAX_BANDS.
    """
    tax = 0.0
    remaining = max(0.0, chargeable_income)

    for band_size, rate, _ in TAX_BANDS:
        if remaining <= 0:
            break
        if band_size == float("inf"):
            chunk = remaining
        else:
            chunk = min(remaining, band_size)
        tax += chunk * rate
        remaining -= chunk

    return tax


def get_tax_rebate(chargeable_income):
    """
    Return the individual tax rebate.
    RM 400 rebate applies when chargeable income is RM 35,000 or below.
    """
    return 400.0 if chargeable_income <= 35_000 else 0.0


def compute_full_tax(gross_income, total_reliefs):
    """
    Given gross income and total reliefs, return a dict with full tax computation.
    """
    chargeable = max(0.0, gross_income - total_reliefs)
    tax_before  = calc_malaysia_tax(chargeable)
    rebate      = get_tax_rebate(chargeable)
    net_tax     = max(0.0, tax_before - rebate)
    eff_rate    = (net_tax / gross_income * 100) if gross_income > 0 else 0.0

    return {
        "gross":        gross_income,
        "reliefs":      total_reliefs,
        "chargeable":   chargeable,
        "tax_before":   tax_before,
        "rebate":       rebate,
        "net_tax":      net_tax,
        "eff_rate":     eff_rate,
    }


def build_bracket_rows(chargeable_income):
    """
    Return a list of (label, rate_str, taxable_amount, tax_amount) tuples
    showing how chargeable income is split across tax bands.
    """
    rows = []
    remaining = chargeable_income
    for band_size, rate, label in TAX_BANDS:
        if remaining <= 0:
            break
        chunk = remaining if band_size == float("inf") else min(remaining, band_size)
        rows.append((label, f"{rate * 100:.1f}%", chunk, chunk * rate))
        remaining -= chunk
    return rows
