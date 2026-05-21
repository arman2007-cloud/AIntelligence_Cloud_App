# security.py
from functools import wraps
from flask import flash, redirect, url_for, jsonify, request
from flask_login import current_user

def admin_required(f):
    """
    Decorador profesional para proteger rutas.
    Verifica si el usuario es Admin. Si no lo es, lo expulsa.
    Funciona tanto para rutas web (HTML) como para rutas API (JSON).
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # 1. Si no está logueado o no es admin, lo bloqueamos
        if not current_user.is_authenticated or current_user.role != 'admin':
            
            # 2. Si la petición era de una API (fetch desde Javascript)
            if request.is_json or request.path.startswith('/api/'):
                return jsonify({"status": "error", "message": "Acceso denegado. Se requieren privilegios de Administrador."}), 403
            
            # 3. Si la petición era normal (navegar por la web)
            flash("Acceso denegado. Área exclusiva de administración.", "error")
            return redirect(url_for('views.index'))
            
        return f(*args, **kwargs)
    return decorated_function