# main.py
import os
import logging
import secrets
from datetime import timedelta
from flask import Flask, session
from dotenv import load_dotenv

# --- Seguridad Web ---
from flask_login import LoginManager, current_user
from werkzeug.middleware.proxy_fix import ProxyFix
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# --- Configuración Base y Base de Datos ---
from logging_config import setup_logging
from database import init_db, get_user_by_id
from task_manager import fail_stuck_tasks
from models import User

# --- Blueprints (Aquí registramos nuestras carpetas) ---
from routes.auth import auth_bp
from routes.views import views_bp
from routes.api import api_bp

load_dotenv()
logger = setup_logging()

# Inicializamos Flask
app = Flask(__name__)

# 🛡️ PROTECCIÓN DE PROXYS
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

# 🛡️ LLAVE MAESTRA Y COOKIES
secret = os.getenv("SECRET_KEY")
if not secret:
    raise RuntimeError("💀 FATAL: SECRET_KEY no definida en el archivo .env.")
app.secret_key = secret

app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=8)
app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Strict'

# --- CONFIGURACIÓN DE LOGIN ---
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.login'
login_manager.login_message = "Por favor, inicia sesión para acceder a esta página."
login_manager.login_message_category = "error"

@login_manager.user_loader
def load_user(user_id):
    user_data = get_user_by_id(int(user_id))
    if user_data:
        return User(user_data)
    return None

# --- INICIALIZACIÓN BD Y TAREAS ---
init_db()
fail_stuck_tasks()

werkzeug_log = logging.getLogger('werkzeug')
werkzeug_log.setLevel(logging.ERROR)
import flask.cli
flask.cli.show_server_banner = lambda *args: None

# 🚀 ESCUDO ANTI-COLAPSO Y FUERZA BRUTA (Nivel Global)
storage_uri = os.getenv("REDIS_URL", "memory://")
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["2000 per day", "300 per hour"],
    storage_uri=storage_uri
)

# --- PROTECCIÓN PARA PANTALLA DE ERROR 429 ---
@app.errorhandler(429)
def ratelimit_handler(e):
    return "Demasiadas peticiones. Por seguridad, espera 1 minuto y vuelve a intentarlo.", 429

# ==============================================================================
# 🛡️ GENERADOR DE TOKENS DINÁMICOS Y CONTEXTO HTML (NUEVO)
# ==============================================================================
@app.before_request
def generate_dynamic_token():
    # Generamos el token de seguridad si el usuario está logueado y no tiene uno
    if current_user.is_authenticated and 'api_token' not in session:
        session['api_token'] = secrets.token_hex(16)

@app.context_processor
def inject_api_token():
    # Esto inyecta la variable {{ api_token }} automáticamente en TODOS tus archivos HTML
    return dict(api_token=session.get('api_token', ''))
# ==============================================================================

# 🚀 REGISTRO DE BLUEPRINTS (Conectamos todos los cables)
app.register_blueprint(auth_bp)
app.register_blueprint(views_bp)
app.register_blueprint(api_bp)

# 🛡️ CABECERAS DE SEGURIDAD HTTP EXTREMA
@app.after_request
def add_security_headers(response):
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    response.headers['Permissions-Policy'] = 'geolocation=(), microphone=()'
    response.headers['Content-Security-Policy'] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdnjs.cloudflare.com; "
        "font-src 'self' https://fonts.gstatic.com https://cdnjs.cloudflare.com; "
        "img-src 'self' data:; "
        "connect-src 'self'"
    )
    return response

# --- ARRANQUE ---
if __name__ == '__main__':
    logger.info("🚀 Levantando servidor SaaS limpio y modular...")
    # 🛡️ FIX: use_reloader=False evita que el servidor se reinicie al crearse archivos temporales de Chrome
    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)