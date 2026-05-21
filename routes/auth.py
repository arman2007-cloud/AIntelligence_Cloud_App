# routes/auth.py
from flask import Blueprint, render_template, redirect, url_for, flash, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField
from wtforms.validators import DataRequired, Length
from werkzeug.security import check_password_hash

# Importamos nuestro modelo, seguridad y base de datos
from models import User
from security import admin_required
from database import get_user_by_username, create_user, get_all_users, delete_user

# Creamos el Blueprint (el mini-servidor para autenticación)
auth_bp = Blueprint('auth', __name__)

# --- FORMULARIOS SEGUROS ---
class LoginForm(FlaskForm):
    username = StringField('Usuario', validators=[DataRequired(message="El usuario es obligatorio.")])
    password = PasswordField('Contraseña', validators=[DataRequired(message="La contraseña es obligatoria.")])

class RegisterForm(FlaskForm):
    username = StringField('Usuario', validators=[
        DataRequired(message="El usuario es obligatorio."),
        Length(min=4, max=25, message="El usuario debe tener entre 4 y 25 caracteres.")
    ])
    password = PasswordField('Contraseña', validators=[
        DataRequired(message="La contraseña es obligatoria."),
        Length(min=8, message="Por seguridad, la contraseña debe tener al menos 8 caracteres.")
    ])

# --- RUTAS DE AUTENTICACIÓN ---
@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('views.index'))

    form = LoginForm()
    if form.validate_on_submit():
        user_data = get_user_by_username(form.username.data)
        if user_data and check_password_hash(user_data['password_hash'], form.password.data):
            user = User(user_data)
            login_user(user)
            return redirect(url_for('views.index'))
        else:
            flash("Usuario o contraseña incorrectos.", "error")

    return render_template('login.html', form=form)

@auth_bp.route('/register', methods=['GET', 'POST'])
@login_required 
@admin_required  # <-- ¡Nuestro guardián en acción!
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        if create_user(form.username.data, form.password.data):
            flash(f"Empleado '{form.username.data}' registrado correctamente.", "success")
            return redirect(url_for('auth.register'))
        else:
            flash("Error: Ese nombre de usuario ya está en uso.", "error")
            
    if form.errors:
        for field, errors in form.errors.items():
            for error in errors:
                flash(error, "error")

    return render_template('register.html', form=form)

@auth_bp.route('/admin/users', methods=['GET'])
@login_required
@admin_required
def manage_users():
    users = get_all_users()
    return jsonify({"status": "success", "users": users})

@auth_bp.route('/admin/users/<int:user_id>', methods=['DELETE'])
@login_required
@admin_required
def api_delete_user(user_id):
    if user_id == current_user.id:
        return jsonify({"status": "error", "message": "No puedes eliminar tu propia cuenta."}), 400
        
    if delete_user(user_id):
        return jsonify({"status": "success", "message": "Usuario eliminado correctamente."})
    
    return jsonify({"status": "error", "message": "No se pudo eliminar el usuario."}), 500

@auth_bp.route('/logout', methods=['GET', 'POST'])
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))