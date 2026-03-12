"""
==============================================================================
MÓDULO DE CONFIGURACIÓN GLOBAL Y SISTEMA DE DISEÑO (config.py)
==============================================================================
"""

import os
from dotenv import load_dotenv

# Carga las variables de entorno desde el archivo .env
load_dotenv()

# ------------------------------------------------------------------------------
# 1. SISTEMA DE ARCHIVOS Y LÍMITES DE SEGURIDAD (.env)
# ------------------------------------------------------------------------------
ARCHIVO_COOKIES = "session_cookies.json"
ARCHIVO_PROCESADOS = "procesados.txt"

# Leemos los límites que tú configuraste en tu archivo .env
MAX_CONEXIONES_DIA = int(os.getenv("MAX_CONEXIONES", "20"))
MAX_SEGUIR_DIA = int(os.getenv("MAX_SEGUIR", "30"))

# ------------------------------------------------------------------------------
# 2. SISTEMA DE DISEÑO (Design System - Obsidian Dark Theme)
# ------------------------------------------------------------------------------
BG = "#07070c"
PANEL = "#0f0f17"
CARD = "#141420"
BORDER = "#252535"
BORDER_LT = "#33334a"
CYAN = "#00d4ff"
CYAN_DIM = "#0099bb"
CORAL = "#ff4d6d"
CORAL_DIM = "#cc2d4a"
EMERALD = "#00c896"
AMBER = "#ffb347"
RED = "#f43f5e"
TEXT = "#eeeef5"
TEXT_DIM = "#7070a0"
TEXT_GHOST = "#3a3a5a"

# ------------------------------------------------------------------------------
# 3. ESCALA TIPOGRÁFICA (Typography Scale)
# ------------------------------------------------------------------------------
F_TITLE = ("Calibri", 28, "bold")
F_SECTION = ("Calibri", 13, "bold")
F_LABEL = ("Segoe UI", 11, "bold")
F_UI = ("Segoe UI", 13)
F_UI_B = ("Segoe UI", 13, "bold")
F_STAT_NUM = ("Calibri", 32, "bold")
F_STAT_LBL = ("Segoe UI", 10)
F_MON = ("Consolas", 11)
F_BTN = ("Calibri", 15, "bold")
F_SUBTITLE = ("Segoe UI", 12)