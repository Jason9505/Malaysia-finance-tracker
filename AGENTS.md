# AGENTS.md

This file provides guidance to agents when working with code in this repository.

## Run Command
```
python main.py
```

## Project-Specific Patterns (Non-Obvious)

- **Theme propagation**: [`apply_theme()`](config.py:173) propagates C_* color constants to ALL imported modules via sys.modules iteration. Pages must import colors at module level before theme application to receive updated values.

- **Database thread-safety**: [`DB`](database.py:9) uses `check_same_thread=False` on SQLite connection - enables cross-thread access but requires synchronization.

- **Lazy page loading**: Pages built only when first navigated via [`show_page()`](main.py:224). Pages needing refresh implement `refresh()` called by [`refresh_page()`](main.py:244).

- **Receipt naming**: Files in `data/receipts/` use `receipt_YYYYMMDD_HHMMSS_MMMMMM.ext` format (microseconds in timestamp).

- **ScrollFrame scroll binding**: [`ScrollFrame`](widgets.py:33) uses `<Enter>` arming with root-level `<Motion>` to detect true mouse exit (not child widget hover).

- **Broken receipt handling**: [`clear_receipt()`](database.py:263) safely clears broken receipt paths without deleting entries.

## Color Constants
All UI colors use C_* prefix: C_BG, C_CARD, C_SIDEBAR, C_PRIMARY, C_SUCCESS, C_DANGER, C_WARNING, C_TEXT, C_TEXT_MED, C_TEXT_LT, C_BORDER, C_ACCENT

## Dependencies
- Required: tkinter (stdlib)
- Optional: pillow (images), openpyxl (Excel export), darkdetect (system dark mode)
