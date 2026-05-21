"""
==============================================================================
DATABASE CORE (database.py)
Motor ORM PostgreSQL y lógica de persistencia en la Nube
==============================================================================
"""

import os
import uuid
import secrets
from datetime import datetime, date, timezone
from werkzeug.security import generate_password_hash

from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, Text, Date
from sqlalchemy.orm import declarative_base, sessionmaker

# Conectamos con el contenedor Docker
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://admin:superpassword@localhost:5432/aintelligence")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Helper para la hora actual en UTC
def get_utc_now():
    return datetime.now(timezone.utc)

# --- DEFINICIÓN DE LAS TABLAS (Modelos) ---

class UserDB(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, default="recruiter")
    created_at = Column(DateTime, default=get_utc_now)

class LeadDB(Base):
    __tablename__ = "leads"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True)
    url = Column(String, index=True)
    name = Column(String)
    job_title = Column(String)
    company = Column(String)
    location = Column(String)
    score = Column(Integer)
    source = Column(String)
    status = Column(String, default="new")
    created_at = Column(DateTime, default=get_utc_now)

class FavoriteCompanyDB(Base):
    __tablename__ = "favorite_companies"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True)
    company_name = Column(String)

class ActivityLogDB(Base):
    __tablename__ = "activity_logs"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True)
    action_type = Column(String)
    url = Column(String)
    success = Column(Boolean)
    created_at = Column(DateTime, default=get_utc_now)

class DailyLimitDB(Base):
    __tablename__ = "daily_limits"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True)
    action_type = Column(String)
    log_date = Column(Date, default=date.today)
    count = Column(Integer, default=0)

class TaskQueueDB(Base):
    __tablename__ = "task_queue"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(Integer, index=True)
    task_type = Column(String)
    status = Column(String, default="pending")
    params = Column(Text)
    result = Column(Text)
    progress = Column(Integer, default=0)
    message = Column(String, default="")
    error = Column(String, default="")
    drive_link = Column(String, default="")
    created_at = Column(DateTime, default=get_utc_now)
    updated_at = Column(DateTime, default=get_utc_now, onupdate=get_utc_now)

# --- FUNCIONES DE BASE DE DATOS ---

def init_db():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        admin = db.query(UserDB).filter(UserDB.username == 'admin').first()
        if not admin:
            # 🛡️ FIX SEC-02: Nunca dejamos una contraseña por defecto
            initial_pass = os.getenv("ADMIN_SETUP_PASSWORD")
            
            if not initial_pass:
                # Si no hay clave en el .env, generamos una aleatoria de alta seguridad
                initial_pass = secrets.token_urlsafe(12)
                print("\n" + "="*60)
                print("⚠️ ADVERTENCIA: No se encontró ADMIN_SETUP_PASSWORD en .env.")
                print(f"🔒 Contraseña autogenerada para el administrador: {initial_pass}")
                print("Guárdala ahora. Esta será la única vez que se muestre en consola.")
                print("="*60 + "\n")
                
            admin = UserDB(
                username='admin', 
                password_hash=generate_password_hash(initial_pass), 
                role='admin'
            )
            db.add(admin)
            db.commit()
            print("✅ Administrador inicial creado con éxito en la base de datos.")
    finally:
        db.close()

# -- Usuarios --
def get_user_by_username(username: str) -> dict:
    db = SessionLocal()
    try:
        u = db.query(UserDB).filter(UserDB.username == username).first()
        if u: return {"id": u.id, "username": u.username, "password_hash": u.password_hash, "role": u.role}
        return None
    finally: db.close()

def get_user_by_id(user_id: int) -> dict:
    db = SessionLocal()
    try:
        u = db.query(UserDB).filter(UserDB.id == user_id).first()
        if u: return {"id": u.id, "username": u.username, "role": u.role}
        return None
    finally: db.close()

def create_user(username: str, password_raw: str, role: str = 'recruiter') -> bool:
    db = SessionLocal()
    try:
        if db.query(UserDB).filter(UserDB.username == username).first(): return False
        nuevo = UserDB(username=username, password_hash=generate_password_hash(password_raw), role=role)
        db.add(nuevo)
        db.commit()
        return True
    finally: db.close()

def get_all_users() -> list:
    db = SessionLocal()
    try:
        users = db.query(UserDB).all()
        return [{"id": u.id, "username": u.username, "role": u.role, "created_at": u.created_at.isoformat()} for u in users]
    finally: db.close()

def delete_user(user_id: int) -> bool:
    db = SessionLocal()
    try:
        u = db.query(UserDB).filter(UserDB.id == user_id).first()
        if u:
            db.delete(u)
            db.commit()
            return True
        return False
    finally: db.close()

# -- Leads y Actividad --
def save_lead(lead_dict: dict, user_id: int):
    db = SessionLocal()
    try:
        nuevo = LeadDB(
            user_id=user_id,
            url=lead_dict.get('url'),
            name=lead_dict.get('name'),
            job_title=lead_dict.get('job_title'),
            company=lead_dict.get('company'),
            location=lead_dict.get('location'),
            score=lead_dict.get('score', 50),
            source=lead_dict.get('source')
        )
        db.add(nuevo)
        db.commit()
    finally: db.close()

def update_lead_status(url: str, status: str, user_id: int):
    db = SessionLocal()
    try:
        lead = db.query(LeadDB).filter(LeadDB.url == url, LeadDB.user_id == user_id).first()
        if lead:
            lead.status = status
            db.commit()
    finally: db.close()

def get_lead_count(user_id: int) -> int:
    db = SessionLocal()
    try: return db.query(LeadDB).filter(LeadDB.user_id == user_id).count()
    finally: db.close()

def log_activity(action_type: str, url: str, success: bool, user_id: int):
    db = SessionLocal()
    try:
        act = ActivityLogDB(user_id=user_id, action_type=action_type, url=url, success=success)
        db.add(act)
        
        hoy = date.today()
        lim = db.query(DailyLimitDB).filter(DailyLimitDB.user_id == user_id, DailyLimitDB.action_type == action_type, DailyLimitDB.log_date == hoy).first()
        if not lim:
            lim = DailyLimitDB(user_id=user_id, action_type=action_type, log_date=hoy, count=1)
            db.add(lim)
        else:
            lim.count += 1
        db.commit()
    finally: db.close()

def get_daily_count(action_type: str, user_id: int) -> int:
    db = SessionLocal()
    try:
        hoy = date.today()
        lim = db.query(DailyLimitDB).filter(DailyLimitDB.user_id == user_id, DailyLimitDB.action_type == action_type, DailyLimitDB.log_date == hoy).first()
        return lim.count if lim else 0
    finally: db.close()

def force_set_daily_count(action_type: str, count: int, user_id: int):
    db = SessionLocal()
    try:
        hoy = date.today()
        lim = db.query(DailyLimitDB).filter(DailyLimitDB.user_id == user_id, DailyLimitDB.action_type == action_type, DailyLimitDB.log_date == hoy).first()
        if not lim:
            lim = DailyLimitDB(user_id=user_id, action_type=action_type, log_date=hoy, count=count)
            db.add(lim)
        else:
            lim.count = count
        db.commit()
    finally: db.close()

# -- Favoritos --
def get_favorite_companies(user_id: int) -> list:
    db = SessionLocal()
    try:
        favs = db.query(FavoriteCompanyDB).filter(FavoriteCompanyDB.user_id == user_id).all()
        return [f.company_name for f in favs]
    finally: db.close()

def add_favorite_company(company: str, user_id: int):
    db = SessionLocal()
    try:
        if not db.query(FavoriteCompanyDB).filter(FavoriteCompanyDB.user_id == user_id, FavoriteCompanyDB.company_name == company).first():
            db.add(FavoriteCompanyDB(user_id=user_id, company_name=company))
            db.commit()
    finally: db.close()

def remove_favorite_company(company: str, user_id: int):
    db = SessionLocal()
    try:
        fav = db.query(FavoriteCompanyDB).filter(FavoriteCompanyDB.user_id == user_id, FavoriteCompanyDB.company_name == company).first()
        if fav:
            db.delete(fav)
            db.commit()
    finally: db.close()