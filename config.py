"""
==============================================================================
CLOUD CONFIGURATION SYSTEM (config.py)
Configuración centralizada para el Servidor Web (Modo Estricto)
==============================================================================
"""

import os
from dotenv import load_dotenv

# Carga las variables desde el archivo .env de la nube
load_dotenv()

# ------------------------------------------------------------------------------
# 1. INFRAESTRUCTURA Y CONEXIONES
# ------------------------------------------------------------------------------
DATABASE_URL = os.getenv("DATABASE_URL")
REDIS_URL = os.getenv("REDIS_URL")

# ------------------------------------------------------------------------------
# 2. SEGURIDAD WEB (FLASK)
# ------------------------------------------------------------------------------
# Llave maestra para encriptar las sesiones (cookies)
SECRET_KEY = os.getenv("SECRET_KEY")

# Contraseña inicial para crear el primer administrador
ADMIN_SETUP_PASSWORD = os.getenv("ADMIN_SETUP_PASSWORD")

# ------------------------------------------------------------------------------
# 3. SEGURIDAD DE LA API (EL CARNET DEL BOT)
# ------------------------------------------------------------------------------
WORKER_API_KEY = os.getenv("WORKER_API_KEY")

# ------------------------------------------------------------------------------
# Verificación Crítica (El servidor no arrancará si faltan secretos vitales)
# ------------------------------------------------------------------------------
if not SECRET_KEY:
    raise ValueError("💀 FATAL ERROR: Falta SECRET_KEY en el archivo .env")
if not WORKER_API_KEY:
    raise ValueError("💀 FATAL ERROR: Falta WORKER_API_KEY en el archivo .env")
if not DATABASE_URL:
    raise ValueError("💀 FATAL ERROR: Falta DATABASE_URL en el archivo .env")