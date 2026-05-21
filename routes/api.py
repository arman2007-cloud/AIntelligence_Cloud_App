"""
==============================================================================
API ROUTES (routes/api.py)
Controlador de tráfico entre Frontend, Nube y Bot Local
==============================================================================
"""

import time
import random
import json
import re
import os
from flask import Blueprint, request, jsonify, session
from flask_login import login_required, current_user
from sqlalchemy import desc
from dotenv import load_dotenv

from celery import Celery

from database import (
    SessionLocal, TaskQueueDB, 
    get_lead_count, get_favorite_companies, add_favorite_company, 
    remove_favorite_company, get_daily_count, force_set_daily_count,
    save_lead, update_lead_status, log_activity
)
from task_manager import create_task, update_task, get_task

api_bp = Blueprint('api', __name__)

load_dotenv(override=True) 

redis_url = os.getenv("REDIS_URL")
celery_client = Celery('emisor_tareas', broker=redis_url)

WORKER_API_KEY = os.getenv("WORKER_API_KEY")

def error_response(message: str, code: int = 400):
    return jsonify({"status": "error", "message": message}), code

def purge_zombie_tasks(user_id):
    db = SessionLocal()
    try:
        db.query(TaskQueueDB).filter(
            TaskQueueDB.user_id == user_id,
            TaskQueueDB.status.in_(['error', 'CANCELED', 'stopped'])
        ).delete(synchronize_session=False)
        db.commit()
    except Exception:
        pass
    finally:
        db.close()

# ==============================================================================
# 🛡️ MIDDLEWARE DE SEGURIDAD DUAL (WEB vs BOT)
# ==============================================================================
@api_bp.before_request
def check_api_token():
    # 1. Definimos las rutas que usa el Bot Local
    rutas_del_bot = [
        'api.bot_save_lead',
        'api.bot_update_lead_status',
        'api.bot_log_activity',
        'api.bot_get_daily_count',
        'api.bot_update_task',
        'api.bot_get_task'
    ]
    
    # 2. Si la ruta pertenece al Bot, exigimos la WORKER_API_KEY
    if request.endpoint in rutas_del_bot:
        llave_bot = request.headers.get('X-Worker-Key')
        if not llave_bot or llave_bot != WORKER_API_KEY:
            return jsonify({'status': 'error', 'message': 'Bloqueo Bot: Worker Key inválida.'}), 403
        return # Si tiene la llave correcta, pasa.

    # 3. Excepciones que no requieren seguridad (Health check) o la manejan internamente
    rutas_excepciones = ['api.api_health', 'api.api_get_favorites']
    if request.endpoint in rutas_excepciones:
        return

    # 4. Para el resto (El panel Web Frontend), exigimos el token dinámico de sesión
    token_recibido = request.headers.get('X-API-Token')
    token_real = session.get('api_token')
    if not token_real or token_recibido != token_real:
        return jsonify({'status': 'error', 'message': 'Bloqueo Web: Token CSRF/Sesión inválido.'}), 403

# ==============================================================================
# RUTAS DE LA API (FRONTEND)
# ==============================================================================
@api_bp.route('/api/health', methods=['GET'])
def api_health():
    try: return jsonify({"status": "ok", "db_leads": get_lead_count(1)}) 
    except: return error_response("Database disconnected", 500)

@api_bp.route('/api/status', methods=['GET'])
@login_required
def get_status():
    db = SessionLocal()
    try:
        response_data = {"tasks": {}}
        tipos_tarea = ['candidates', 'jobs', 'outreach', 'manual', 'analyze']
        
        for t_type in tipos_tarea:
            t = db.query(TaskQueueDB).filter(
                TaskQueueDB.user_id == current_user.id,
                TaskQueueDB.task_type == t_type
            ).order_by(desc(TaskQueueDB.created_at)).first()
            
            if t:
                res_list = []
                if t.result:
                    try: res_list = json.loads(t.result)
                    except: pass
                
                response_data["tasks"][t_type] = {
                    "task_id": t.id,
                    "is_running": t.status in ["pending", "running", "paused"],
                    "progress_pct": t.progress,
                    "message": t.message,
                    "results": res_list,
                    "drive_link": t.drive_link,
                    "error": t.error
                }
            else:
                response_data["tasks"][t_type] = {
                    "task_id": None,
                    "is_running": False,
                    "progress_pct": 0,
                    "message": "",
                    "results": [],
                    "drive_link": "",
                    "error": None
                }
        return jsonify(response_data)
    finally:
        db.close()

@api_bp.route('/api/favorites', methods=['GET'])
def api_get_favorites():
    # Si viene con user_id y la llave correcta desde el bot
    llave_bot = request.headers.get('X-Worker-Key')
    user_id = request.args.get('user_id')
    
    if user_id and llave_bot == WORKER_API_KEY:
        return jsonify({"status": "success", "favorites": get_favorite_companies(int(user_id))})
    
    # Si es una petición desde la web
    if not current_user.is_authenticated:
        return error_response("No autorizado", 401)
    return jsonify({"status": "success", "favorites": get_favorite_companies(current_user.id)})

@api_bp.route('/api/favorites', methods=['POST'])
@login_required
def api_add_favorite():
    data = request.json or {}
    company = data.get('company', '')
    if not company or not isinstance(company, str) or len(company.strip()) == 0: 
        return error_response("Company name required")
    if len(company) > 100:
        return error_response("Nombre demasiado largo.")
    add_favorite_company(company.strip(), current_user.id)
    return jsonify({"status": "success", "favorites": get_favorite_companies(current_user.id)})

@api_bp.route('/api/favorites/<path:company>', methods=['DELETE'])
@login_required
def api_remove_favorite(company):
    remove_favorite_company(company, current_user.id)
    return jsonify({"status": "success", "favorites": get_favorite_companies(current_user.id)})

@api_bp.route('/api/control', methods=['POST'])
@login_required
def control_task():
    action = (request.json or {}).get('action')
    db = SessionLocal()
    try:
        tareas_activas = db.query(TaskQueueDB).filter(
            TaskQueueDB.user_id == current_user.id,
            TaskQueueDB.status.in_(['pending', 'running', 'paused'])
        ).all()
        
        for t in tareas_activas:
            if action == 'pause': update_task(t.id, status='paused')
            elif action == 'resume': update_task(t.id, status='running')
            elif action == 'stop': update_task(t.id, status='CANCELED')
        
        return jsonify({"status": "success"})
    finally:
        db.close()

# ==============================================================================
# DISPARADORES DE TAREAS 
# ==============================================================================
@api_bp.route('/api/analyze_profile', methods=['POST'])
@login_required
def analyze_profile():
    data = request.json or {}
    url, name = data.get('url'), data.get('name')
    if not url or not name: return error_response("Faltan datos.")
    
    purge_zombie_tasks(current_user.id) 
    t_id = create_task(current_user.id, 'analyze', {'url': url, 'name': name})
    
    celery_client.send_task(
        'services.tasks.task_analyze_profile',
        args=[t_id, current_user.id, url, name],
        queue=f"cola_usuario_{current_user.id}"
    )
    return jsonify({"status": "accepted", "task_id": t_id})

@api_bp.route('/api/search_candidates', methods=['POST'])
@login_required
def search_candidates():
    data = request.json or {}
    cargo = str(data.get('cargo', '')).strip()
    location = str(data.get('location', 'Malta')).strip()
    paginas = max(1, min(int(data.get('pages', 1)), 10))
    if not cargo: return error_response("Job title required")
    
    purge_zombie_tasks(current_user.id) 
    t_id = create_task(current_user.id, 'candidates', {'cargo': cargo, 'location': location})
    
    celery_client.send_task(
        'services.tasks.task_search_candidates',
        args=[t_id, current_user.id, cargo, location, paginas],
        queue=f"cola_usuario_{current_user.id}"
    )
    return jsonify({"status": "accepted", "task_id": t_id})

@api_bp.route('/api/search_jobs', methods=['POST'])
@login_required
def search_jobs():
    data = request.json or {}
    cargo, location = str(data.get('cargo', '')).strip(), str(data.get('location', 'Malta')).strip()
    if not cargo: return error_response("Job title required")
    
    purge_zombie_tasks(current_user.id) 
    t_id = create_task(current_user.id, 'jobs', {'cargo': cargo, 'location': location})
    
    celery_client.send_task(
        'services.tasks.task_search_jobs',
        args=[t_id, current_user.id, cargo, location],
        queue=f"cola_usuario_{current_user.id}"
    )
    return jsonify({"status": "accepted", "task_id": t_id})

@api_bp.route('/api/run_outreach', methods=['POST'])
@login_required
def run_outreach():
    data = request.json or {}
    selected = data.get('selected_candidates', [])
    msg = str(data.get('message', "")).strip()
    
    if len(msg) > 500: return error_response("Mensaje demasiado largo.")
    msg = re.sub(r'<[^>]*>', '', msg)
    
    user_invites_today = get_daily_count("connections", current_user.id)
    if user_invites_today + len(selected) > 15:
        return error_response("Límite diario excedido.")
        
    purge_zombie_tasks(current_user.id) 
    t_id = create_task(current_user.id, 'outreach', {'count': len(selected)})
    
    db = SessionLocal()
    last_cand = db.query(TaskQueueDB).filter(
        TaskQueueDB.user_id == current_user.id, 
        TaskQueueDB.task_type == 'candidates'
    ).order_by(desc(TaskQueueDB.created_at)).first()
    db.close()
    
    cand_task_id = last_cand.id if last_cand else None
    
    celery_client.send_task(
        'services.tasks.task_run_outreach',
        args=[t_id, current_user.id, selected, msg, cand_task_id],
        queue=f"cola_usuario_{current_user.id}"
    )
    return jsonify({"status": "accepted", "task_id": t_id})

@api_bp.route('/api/run_manual_outreach', methods=['POST'])
@login_required
def run_manual_outreach():
    data = request.json or {}
    sheet_url = str(data.get('url', '')).strip()
    mensaje_base = str(data.get('message', '')).strip()
    
    if len(mensaje_base) > 500: return error_response("Mensaje demasiado largo.")
    mensaje_base = re.sub(r'<[^>]*>', '', mensaje_base)
    
    pattern = r'^https://docs\.google\.com/spreadsheets/d/([a-zA-Z0-9-_]+)'
    match = re.match(pattern, sheet_url)
    if not match: return error_response("Invalid URL format.")
        
    sheet_id = match.group(1)
    
    purge_zombie_tasks(current_user.id) 
    t_id = create_task(current_user.id, 'manual', {'sheet_id': sheet_id, 'message': mensaje_base})
    
    celery_client.send_task(
        'services.tasks.task_run_manual_outreach',
        args=[t_id, current_user.id, sheet_id, mensaje_base],
        queue=f"cola_usuario_{current_user.id}"
    )
    return jsonify({"status": "accepted", "task_id": t_id})

# ==============================================================================
# RUTAS DE UTILIDAD
# ==============================================================================
@api_bp.route('/api/clear_results', methods=['POST'])
@login_required
def clear_results():
    db = SessionLocal()
    try:
        db.query(TaskQueueDB).filter(
            TaskQueueDB.user_id == current_user.id,
            TaskQueueDB.status.in_(['done', 'error', 'CANCELED', 'stopped'])
        ).delete(synchronize_session=False)
        db.commit()
        return jsonify({"status": "success"})
    finally:
        db.close()

@api_bp.route('/api/stats', methods=['GET'])
@login_required
def api_get_stats():
    return jsonify({
        "connections": get_daily_count("connections", current_user.id), 
        "messages": get_daily_count("messages", current_user.id), 
        "total_leads": get_lead_count(current_user.id)
    })

@api_bp.route('/api/set_counter', methods=['POST'])
@login_required
def set_counter():
    count = int((request.json or {}).get('count', 0))
    
    # 🛡️ FIX: Hemos eliminado el bloqueo de seguridad. 
    # Ahora el administrador manda sobre el contador, sea para subirlo o para bajarlo a 0.
    force_set_daily_count("connections", count, current_user.id)
    
    return jsonify({"status": "success", "invites_today": count})


# ==============================================================================
# 📞 RECEPCIONISTA: ENDPOINTS EXCLUSIVOS PARA EL BOT LOCAL
# ==============================================================================
@api_bp.route('/api/leads', methods=['POST'])
def bot_save_lead():
    data = request.json
    save_lead(data['lead'], data['user_id'])
    return jsonify({"status": "success"}), 200

@api_bp.route('/api/leads/status', methods=['PUT'])
def bot_update_lead_status():
    data = request.json
    update_lead_status(data['url'], data['status'], data['user_id'])
    return jsonify({"status": "success"}), 200

@api_bp.route('/api/activity', methods=['POST'])
def bot_log_activity():
    data = request.json
    log_activity(data['action_type'], data['url'], data['success'], data['user_id'])
    return jsonify({"status": "success"}), 200

@api_bp.route('/api/limits/daily', methods=['GET'])
def bot_get_daily_count():
    action_type = request.args.get('action_type')
    user_id = int(request.args.get('user_id'))
    count = get_daily_count(action_type, user_id)
    return jsonify({"count": count}), 200

@api_bp.route('/api/tasks/<task_id>', methods=['PATCH'])
def bot_update_task(task_id):
    data = request.json
    update_task(task_id, **data)
    return jsonify({"status": "success"}), 200

@api_bp.route('/api/tasks/<task_id>', methods=['GET'])
def bot_get_task(task_id):
    user_id = request.args.get('user_id')
    user_id = int(user_id) if user_id else None
    task = get_task(task_id, user_id)
    return jsonify({"task": task}), 200