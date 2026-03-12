"""
==============================================================================
GLOBAL CONFIGURATION AND DESIGN SYSTEM (config.py)
==============================================================================
Architecture:
    Acts as the 'Single Source of Truth'. Separates configuration and UI
    colors from the business logic, adhering to the Separation of Concerns.
==============================================================================
"""

import os
from dotenv import load_dotenv

# Load environment variables safely from the hidden .env file
load_dotenv()

# ------------------------------------------------------------------------------
# 1. FILE PATHS AND SECURITY LIMITS (.env)
# ------------------------------------------------------------------------------
COOKIES_FILE = "session_cookies.json"   # Stores Chrome session to prevent re-logins
PROCESSED_FILE = "procesados.txt"       # Lightweight database to avoid duplicate interactions

# Daily security limits pulled from .env to prevent LinkedIn shadowbans
MAX_CONNECTIONS_PER_DAY = int(os.getenv("MAX_CONEXIONES", "20"))
MAX_FOLLOWS_PER_DAY = int(os.getenv("MAX_SEGUIR", "30"))

# ------------------------------------------------------------------------------
# 2. DESIGN SYSTEM (Obsidian Dark Theme)
# ------------------------------------------------------------------------------
BG = "#07070c"            # Deep dark background
PANEL = "#0f0f17"         # Elevated background for sidebar
CARD = "#141420"          # Card container background
BORDER = "#252535"        # Standard divider border
BORDER_LT = "#33334a"     # Light borders for inputs
CYAN = "#00d4ff"          # Primary action accent (Leads)
CYAN_DIM = "#0099bb"      # Hover state for Cyan
CORAL = "#ff4d6d"         # Accent for Job Finder
CORAL_DIM = "#cc2d4a"     # Hover state for Coral
EMERALD = "#00c896"       # Accent for Networking & Success states
AMBER = "#ffb347"         # Accent for Warnings / Pauses
RED = "#f43f5e"           # Destructive actions (Stop)
TEXT = "#eeeef5"          # Primary highly-readable text
TEXT_DIM = "#7070a0"      # Secondary text / Metadata
TEXT_GHOST = "#3a3a5a"    # Placeholder text

# ------------------------------------------------------------------------------
# 3. TYPOGRAPHY SCALE
# ------------------------------------------------------------------------------
F_TITLE = ("Calibri", 28, "bold")         # H1
F_SECTION = ("Calibri", 13, "bold")       # H2
F_LABEL = ("Segoe UI", 11, "bold")        # Input labels
F_UI = ("Segoe UI", 13)                   # Standard body
F_UI_B = ("Segoe UI", 13, "bold")         # Emphasized body
F_STAT_NUM = ("Calibri", 32, "bold")      # Dashboard KPI numbers
F_STAT_LBL = ("Segoe UI", 10)             # KPI Subtitles
F_MON = ("Consolas", 11)                  # Monospaced font for Terminal Logs
F_BTN = ("Calibri", 15, "bold")           # Call to Action Buttons
F_SUBTITLE = ("Segoe UI", 12)             # Subtitles and guides