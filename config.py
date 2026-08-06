"""
config.py
Central configuration for the Movie Ticket Management System.
Holds paths, color palette, fonts, and application-wide constants.
"""

import os

# ---------------------------------------------------------------------------
# Base paths
# ---------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DATABASE_DIR = os.path.join(BASE_DIR, "database")
DATABASE_PATH = os.path.join(DATABASE_DIR, "movies.db")

ASSETS_DIR = os.path.join(BASE_DIR, "assets")
POSTERS_DIR = os.path.join(ASSETS_DIR, "posters")
LOGO_PATH = os.path.join(ASSETS_DIR, "logo.png")
BANNER_PATH = os.path.join(ASSETS_DIR, "banner.png")

RECEIPTS_DIR = os.path.join(BASE_DIR, "receipts")
EXPORTS_DIR = os.path.join(BASE_DIR, "exports")
BACKUPS_DIR = os.path.join(BASE_DIR, "backups")

# Ensure runtime directories exist even on a fresh checkout
for _dir in (DATABASE_DIR, ASSETS_DIR, POSTERS_DIR, RECEIPTS_DIR, EXPORTS_DIR, BACKUPS_DIR):
    os.makedirs(_dir, exist_ok=True)

# ---------------------------------------------------------------------------
# Application metadata
# ---------------------------------------------------------------------------
APP_NAME = "Movie Ticket Management System"
APP_VERSION = "1.0.0"
APP_AUTHOR = "Cineplex Software Solutions"

DEFAULT_USERNAME = "admin"
DEFAULT_PASSWORD = ""

DEFAULT_TAX_PERCENT = 18.0  # GST %
CURRENCY_SYMBOL = "Rs."

SEAT_ROWS = ["A", "B", "C", "D", "E"]
SEATS_PER_ROW = 8

# ---------------------------------------------------------------------------
# Theme / color palettes
# ---------------------------------------------------------------------------
DARK_THEME = {
    "bg": "#121212",
    "surface": "#1e1e1e",
    "surface_alt": "#242424",
    "primary": "#e50914",
    "primary_dark": "#b0060f",
    "accent": "#00b4d8",
    "text": "#f5f5f5",
    "text_muted": "#a0a0a0",
    "success": "#2ecc71",
    "danger": "#e74c3c",
    "warning": "#f39c12",
    "seat_available": "#2ecc71",
    "seat_booked": "#e74c3c",
    "seat_selected": "#3498db",
    "border": "#333333",
    "entry_bg": "#2a2a2a",
}

LIGHT_THEME = {
    "bg": "#f4f4f6",
    "surface": "#ffffff",
    "surface_alt": "#eeeeee",
    "primary": "#e50914",
    "primary_dark": "#b0060f",
    "accent": "#0077b6",
    "text": "#1a1a1a",
    "text_muted": "#555555",
    "success": "#27ae60",
    "danger": "#c0392b",
    "warning": "#e67e22",
    "seat_available": "#27ae60",
    "seat_booked": "#c0392b",
    "seat_selected": "#2980b9",
    "border": "#cccccc",
    "entry_bg": "#ffffff",
}

FONT_FAMILY = "Segoe UI"
FONT_TITLE = (FONT_FAMILY, 22, "bold")
FONT_HEADING = (FONT_FAMILY, 15, "bold")
FONT_SUBHEADING = (FONT_FAMILY, 11, "bold")
FONT_NORMAL = (FONT_FAMILY, 10)
FONT_SMALL = (FONT_FAMILY, 9)
FONT_BUTTON = (FONT_FAMILY, 10, "bold")

WINDOW_WIDTH = 1200
WINDOW_HEIGHT = 750
