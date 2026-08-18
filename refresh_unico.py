"""
Executa um único REFRESH da mv_geo3
Use com Agendador de Tarefas do Windows
"""

import os
import time
import logging
from datetime import datetime
from dotenv import load_dotenv
import psycopg2

# Configuração
LOG_FILE = os.path.join(os.path.dirname(__file__), 'refresh_service.log')

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Carregar variáveis de ambiente
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

def get_connection():
    """Cria conexão com o banco PostgreSQL"""
    return psycopg2.connect(
        host=os.getenv('DB_HOST'),
        port=os.getenv('DB_PORT'),
        dbname=os.getenv('DB_NAME'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD')
    )

def refresh():
    """Executa o REFRESH"""
    logger.info("=" * 50)
    logger.info("INICIANDO REFRESH mv_geo3")
    start = time.time()

    try:
        conn = get_connection()
        conn.autocommit = True

        with conn.cursor() as cur:
            cur.execute("REFRESH MATERIALIZED VIEW mv_geo3;")

        elapsed = time.time() - start
        logger.info(f"REFRESH OK - {elapsed:.1f}s")

        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM mv_geo3;")
            count = cur.fetchone()[0]
            logger.info(f"Registros: {count}")

        conn.close()
        return True

    except Exception as e:
        logger.error(f"ERRO: {e}")
        return False

if __name__ == "__main__":
    refresh()
