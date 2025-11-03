import logging
from logging.handlers import RotatingFileHandler
import os

def setup_logging():
    # Crear directorio de logs si no existe
    if not os.path.exists('logs'):
        os.makedirs('logs')
    # Configurar logging general
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            RotatingFileHandler('logs/app.log', maxBytes=1024*1024*10, backupCount=5),
            logging.StreamHandler()
        ]
    )
    # Logger específico para auditoría
    audit_logger = logging.getLogger('audit')
    audit_handler = RotatingFileHandler('logs/audit.log', maxBytes=1024*1024*10, backupCount=5)
    audit_handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
    audit_logger.addHandler(audit_handler)
    audit_logger.setLevel(logging.INFO)
    audit_logger.propagate = False
    return audit_logger

audit_logger = setup_logging()
