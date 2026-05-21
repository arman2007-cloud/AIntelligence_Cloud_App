"""
==============================================================================
CLOUD TASK MANAGER (task_manager.py)
Gestión de estado de tareas en PostgreSQL
==============================================================================
"""

import json
from database import SessionLocal, TaskQueueDB

def create_task(user_id: int, task_type: str, params_dict: dict) -> str:
    db = SessionLocal()
    try:
        task = TaskQueueDB(
            user_id=user_id,
            task_type=task_type,
            status="pending",
            params=json.dumps(params_dict)
        )
        db.add(task)
        db.commit()
        db.refresh(task)
        return task.id
    finally:
        db.close()

def update_task(task_id: str, **kwargs):
    db = SessionLocal()
    try:
        task = db.query(TaskQueueDB).filter(TaskQueueDB.id == task_id).first()
        if task:
            for key, value in kwargs.items():
                setattr(task, key, value)
            db.commit()
    finally:
        db.close()

def get_task(task_id: str, user_id: int = None) -> dict:
    db = SessionLocal()
    try:
        query = db.query(TaskQueueDB).filter(TaskQueueDB.id == task_id)
        if user_id:
            query = query.filter(TaskQueueDB.user_id == user_id)
        
        task = query.first()
        if task:
            return {
                "id": task.id,
                "task_type": task.task_type,
                "status": task.status,
                "result": task.result,
                "progress": task.progress,
                "message": task.message,
                "error": task.error,
                "drive_link": task.drive_link
            }
        return None
    finally:
        db.close()

def fail_stuck_tasks():
    """Si el servidor se reinicia, marcamos como fallidas las tareas que estaban a medias."""
    db = SessionLocal()
    try:
        stuck_tasks = db.query(TaskQueueDB).filter(TaskQueueDB.status.in_(["pending", "running"])).all()
        for t in stuck_tasks:
            t.status = "failed"
            t.error = "Servidor reiniciado inesperadamente."
        db.commit()
    finally:
        db.close()