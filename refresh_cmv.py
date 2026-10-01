"""
Executa o REFRESH das views materializadas mv_cmv_loja_v2 e mv_cmv_fab
Use com o Agendador de Tarefas do Windows (instalar_tarefa_cmv.bat)
"""

import os
import time
import logging
from dotenv import load_dotenv
import psycopg2

LOG_FILE = os.path.join(os.path.dirname(__file__), 'refresh_cmv.log')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

VIEWS = ['mv_cmv_loja_v2', 'mv_cmv_fab']


def get_connection():
    """Cria conexao com o banco PostgreSQL"""
    return psycopg2.connect(
        host=os.getenv('DB_HOST'),
        port=os.getenv('DB_PORT'),
        dbname=os.getenv('DB_NAME'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD')
    )


def refresh():
    """Executa o REFRESH de mv_cmv_loja_v2 e mv_cmv_fab"""
    logger.info("=" * 50)
    logger.info("INICIANDO REFRESH mv_cmv_loja_v2 / mv_cmv_fab")

    ok = True
    try:
        conn = get_connection()
        conn.autocommit = True

        for view in VIEWS:
            start = time.time()
            try:
                with conn.cursor() as cur:
                    cur.execute(f"REFRESH MATERIALIZED VIEW {view};")
                elapsed = time.time() - start
                logger.info(f"{view}: REFRESH OK - {elapsed:.1f}s")

                with conn.cursor() as cur:
                    cur.execute(f"SELECT COUNT(*) FROM {view};")
                    count = cur.fetchone()[0]
                    logger.info(f"{view}: {count} registros")
            except Exception as e:
                ok = False
                logger.error(f"{view}: ERRO - {e}")

        conn.close()

    except Exception as e:
        ok = False
        logger.error(f"ERRO de conexao: {e}")

    logger.info("CONCLUIDO" if ok else "CONCLUIDO COM ERROS")
    return ok


if __name__ == "__main__":
    refresh()
