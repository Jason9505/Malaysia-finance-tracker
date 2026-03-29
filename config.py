# ─── config.py ───────────────────────────────────────────────────────────────
# App-wide constants: colors, paths, tax data, expense categories.

import os

# ── App paths (Windows-safe) ──────────────────────────────────────────────────
# Stored inside Documents\mykad_tracker — always writable on Windows
# Data folder sits inside the project directory:
#   ...\personal coding project\finance tracker app\data\
_BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
APP_DIR      = os.path.join(_BASE_DIR, "data")
DB_PATH      = os.path.join(APP_DIR, "tracker.db")
RECEIPTS_DIR = os.path.join(APP_DIR, "receipts")
os.makedirs(APP_DIR,      exist_ok=True)
os.makedirs(RECEIPTS_DIR, exist_ok=True)

# ── Color palette ─────────────────────────────────────────────────────────────
C_SIDEBAR     = "#1e1b4b"
C_SIDEBAR_H   = "#312e81"
C_SIDEBAR_ACT = "#4f46e5"
C_BG          = "#f1f5f9"
C_CARD        = "#ffffff"
C_PRIMARY     = "#4f46e5"
C_PRIMARY_LT  = "#e0e7ff"
C_SUCCESS     = "#10b981"
C_DANGER      = "#ef4444"
C_WARNING     = "#f59e0b"
C_TEXT        = "#1e293b"
C_TEXT_MED    = "#64748b"
C_TEXT_LT     = "#94a3b8"
C_BORDER      = "#e2e8f0"
C_ACCENT      = "#7c3aed"

# ── Malaysia tax reliefs YA 2025 ──────────────────────────────────────────────
# Each entry: (key, display_name, max_relief_rm)
ALL_RELIEFS = [
    ("individual",        "Individual & Dependent Relatives",                9000),
    ("disabled_self",     "Disabled Individual (extra)",                     7000),
    ("spouse",            "Spouse (no income / joint assessment)",            4000),
    ("disabled_spouse",   "Disabled Spouse (extra)",                         6000),
    ("alimony",           "Alimony to Former Wife",                          4000),
    ("parent_medical",    "Medical / Special Needs / Carer for Parents",     8000),
    ("parent_care",       "Parental Care Relief",                            3000),
    ("disabled_equip",    "Basic Supporting Equipment (Disabled)",           6000),
    ("disabled_child",    "Disabled Child",                                  8000),
    ("education_self",    "Education Fees (Self)",                           7000),
    ("sspn",              "SSPN Education Savings (net deposit)",            8000),
    ("medical",           "Serious Disease / Fertility Treatment",          10000),
    ("medical_checkup",   "Medical Check-up",                                1000),
    ("vaccination",       "Vaccination",                                     1000),
    ("dental",            "Dental Treatment",                                1000),
    ("mental_health",     "Mental Health Treatment",                         1000),
    ("child_learning",    "Child Learning Disability Treatment",             6000),
    ("child_under18",     "Child Under 18 (per child x RM2,000)",           2000),
    ("child_higher",      "Child 18+ Higher Education (per child x RM8,000)", 8000),
    ("childcare",         "Childcare Fees",                                  3000),
    ("breastfeeding",     "Breastfeeding Equipment",                         1000),
    ("lifestyle",         "Lifestyle (books, PC, phone, internet)",          2500),
    ("sports",            "Sports Equipment & Activities",                   1000),
    ("ev_charging",       "EV Charging Equipment",                           2500),
    ("epf",               "EPF Contributions",                               4000),
    ("life_insurance",    "Life Insurance Premium",                          3000),
    ("edu_medical_ins",   "Education & Medical Insurance",                   4000),
    ("socso",             "SOCSO Contributions",                              350),
    ("prs",               "Private Retirement Scheme (PRS)",                 3000),
    ("housing_interest",  "First Home Housing Loan Interest",                7000),
]

# ── Expense categories ────────────────────────────────────────────────────────
# key: (display_label, is_tax_deductible, linked_relief_key)
EXPENSE_CATS = {
    "food":       ("Food & Dining",              False, ""),
    "education":  ("Education",                   True,  "education_self"),
    "sports":     ("Sports & Fitness",            True,  "sports"),
    "medical":    ("Medical & Health",            True,  "medical"),
    "lifestyle":  ("Lifestyle (Tech / Books)",    True,  "lifestyle"),
    "insurance":  ("Insurance Premium",           True,  "life_insurance"),
    "epf":        ("EPF Contributions",           True,  "epf"),
    "childcare":  ("Childcare",                   True,  "childcare"),
    "transport":  ("Transport",                   False, ""),
    "utilities":  ("Utilities",                   False, ""),
    "housing":    ("Housing / Rent",              False, "housing_interest"),
    "others":     ("Others",                      False, ""),
}

# ── Progressive tax bands YA 2025 ─────────────────────────────────────────────
# (band_size, rate, display_label)
TAX_BANDS = [
    (5_000,       0.00,  "RM 0 - RM 5,000"),
    (15_000,      0.01,  "RM 5,001 - RM 20,000"),
    (15_000,      0.03,  "RM 20,001 - RM 35,000"),
    (15_000,      0.08,  "RM 35,001 - RM 50,000"),
    (20_000,      0.13,  "RM 50,001 - RM 70,000"),
    (30_000,      0.21,  "RM 70,001 - RM 100,000"),
    (150_000,     0.24,  "RM 100,001 - RM 250,000"),
    (150_000,     0.245, "RM 250,001 - RM 400,000"),
    (200_000,     0.25,  "RM 400,001 - RM 600,000"),
    (400_000,     0.26,  "RM 600,001 - RM 1,000,000"),
    (1_000_000,   0.28,  "RM 1,000,001 - RM 2,000,000"),
    (float("inf"),0.30,  "Above RM 2,000,000"),
]

# ── Sidebar navigation items ──────────────────────────────────────────────────
NAV_ITEMS = [
    ("Dashboard",  "📊", "dashboard"),
    ("Income",     "💵", "income"),
    ("Expenses",   "🧾", "expenses"),
    ("Income Tax", "📋", "tax"),
    ("Settings",   "⚙️",  "settings"),
]

# ── Theme palettes ────────────────────────────────────────────────────────────
_LIGHT_PALETTE = dict(
    C_SIDEBAR     = "#1e1b4b",
    C_SIDEBAR_H   = "#312e81",
    C_SIDEBAR_ACT = "#4f46e5",
    C_BG          = "#f1f5f9",
    C_CARD        = "#ffffff",
    C_PRIMARY     = "#4f46e5",
    C_PRIMARY_LT  = "#e0e7ff",
    C_SUCCESS     = "#10b981",
    C_DANGER      = "#ef4444",
    C_WARNING     = "#f59e0b",
    C_TEXT        = "#1e293b",
    C_TEXT_MED    = "#64748b",
    C_TEXT_LT     = "#94a3b8",
    C_BORDER      = "#e2e8f0",
    C_ACCENT      = "#7c3aed",
)

_DARK_PALETTE = dict(
    C_SIDEBAR     = "#0d0b1e",
    C_SIDEBAR_H   = "#1a1850",
    C_SIDEBAR_ACT = "#4f46e5",
    C_BG          = "#0f172a",
    C_CARD        = "#1e293b",
    C_PRIMARY     = "#818cf8",
    C_PRIMARY_LT  = "#1e1b4b",
    C_SUCCESS     = "#34d399",
    C_DANGER      = "#f87171",
    C_WARNING     = "#fbbf24",
    C_TEXT        = "#f1f5f9",
    C_TEXT_MED    = "#94a3b8",
    C_TEXT_LT     = "#475569",
    C_BORDER      = "#334155",
    C_ACCENT      = "#a78bfa",
)

def _detect_system_dark() -> bool:
    """Best-effort system dark-mode detection (Windows/macOS/Linux)."""
    try:
        import darkdetect            # pip install darkdetect (optional)
        return darkdetect.isDark()
    except Exception:
        pass
    try:
        import subprocess, sys
        if sys.platform == "win32":
            import winreg
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                r"Software\\Microsoft\\Windows\\CurrentVersion\\Themes\\Personalize")
            val, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
            return val == 0
        if sys.platform == "darwin":
            out = subprocess.check_output(
                ["defaults", "read", "-g", "AppleInterfaceStyle"],
                stderr=subprocess.DEVNULL).decode().strip()
            return out.lower() == "dark"
    except Exception:
        pass
    return False

def apply_theme(theme_name: str) -> None:
    """
    Update every module-level colour constant in config for the chosen theme.
    theme_name: 'light' | 'dark' | 'system'
    """
    import sys
    mod = sys.modules[__name__]
    if theme_name == "dark":
        palette = _DARK_PALETTE
    elif theme_name == "system":
        palette = _DARK_PALETTE if _detect_system_dark() else _LIGHT_PALETTE
    else:
        palette = _LIGHT_PALETTE
    for k, v in palette.items():
        setattr(mod, k, v)