"""
==============================================================================
LOGGING CONFIGURATION (logging_config.py)
Sistema de logs rotativos y estructurados para producción (Nube)
==============================================================================
"""

import os
import logging
import logging.handlers
import json
from datetime import datetime, timezone

class StructuredFormatter(logging.Formatter):
    """Logs en formato JSON — legibles por sistemas de monitorización o grep."""
    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            # Usamos timezone.utc en lugar del obsoleto utcnow()
            "ts": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "level": record.levelname,
            "module": record.module,
            "msg": record.getMessage(),
        }
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_entry, ensure_ascii=False)

def setup_logging() -> logging.Logger:
    os.makedirs("logs", exist_ok=True)
    logger = logging.getLogger("aintelligence_cloud")
    logger.setLevel(logging.INFO)
    
    # Evitar handlers duplicados si Flask o Gunicorn recargan el entorno
    if not logger.handlers:
        # Handler 1: Consola (Formato clásico y bonito para desarrollo)
        console = logging.StreamHandler()
        console.setFormatter(logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(module)s | %(message)s",
            datefmt="%H:%M:%S"
        ))
        
        # Handler 2: Archivo rotativo JSON (Para producción en Plesk)
        # Máximo 5MB por archivo, guarda los últimos 5 archivos
        file_handler = logging.handlers.RotatingFileHandler(
            "logs/aintelligence_cloud.log",
            maxBytes=5 * 1024 * 1024,
            backupCount=5,
            encoding="utf-8"
        )
        file_handler.setFormatter(StructuredFormatter())
        
        logger.addHandler(console)
        logger.addHandler(file_handler)
        
    return logger