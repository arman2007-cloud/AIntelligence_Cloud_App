# routes/views.py
from flask import Blueprint, render_template
from flask_login import login_required, current_user

# Creamos el Blueprint para las vistas HTML
views_bp = Blueprint('views', __name__)

@views_bp.route('/')
@login_required
def index():
    # Renderizamos el panel principal pasando los datos del usuario
    return render_template('index.html', username=current_user.username, role=current_user.role)