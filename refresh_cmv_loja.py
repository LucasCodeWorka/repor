"""
Refresh de mv_cmv_loja_v2 e mv_cmv_loja, EM ORDEM:
  1. REFRESH mv_cmv_loja_v2
  2. Confere se populou (count > 0 e max(data) recente)
  3. So entao REFRESH mv_cmv_loja

Separado de mv_cmv_fab (ver refresh_cmv_fab.py) -- sao tarefas
independentes, cada uma com sua propria conexao, pra uma nao travar
nem ser afetada pela outra.
"""

import os
import time
import logging
from dotenv import load_dotenv
import psycopg2

LOG_FILE = os.path.join(os.path.dirname(__file__), 'refresh_cmv_loja.log')

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


def get_connection():
    # keepalives: o REFRESH leva muitos minutos sem trafego na conexao e ela
    # vinha caindo com "server closed the connection unexpectedly" no meio.
    return psycopg2.connect(
        host=os.getenv('DB_HOST'),
        port=os.getenv('DB_PORT'),
        dbname=os.getenv('DB_NAME'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD'),
        keepalives=1,
        keepalives_idle=30,
        keepalives_interval=10,
        keepalives_count=5,
    )


def refresh():
    logger.info("=" * 50)
    logger.info("INICIANDO REFRESH mv_cmv_loja_v2 -> mv_cmv_loja (em ordem)")

    try:
        conn = get_connection()
        conn.autocommit = True

        # 1. mv_cmv_loja_v2
        start = time.time()
        with conn.cursor() as cur:
            cur.execute("REFRESH MATERIALIZED VIEW mv_cmv_loja_v2;")
        elapsed = time.time() - start
        logger.info(f"mv_cmv_loja_v2: REFRESH OK - {elapsed:.1f}s")

        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*), MAX(data) FROM mv_cmv_loja_v2;")
            count, max_data = cur.fetchone()
            logger.info(f"mv_cmv_loja_v2: {count} registros, max(data)={max_data}")

        # 2. confere se populou antes de seguir
        if not count or count == 0:
            logger.error("mv_cmv_loja_v2 ficou vazia -- NAO vou rodar mv_cmv_loja. Abortando.")
            conn.close()
            return False

        # 3. mv_cmv_loja (so depois de confirmar que v2 populou)
        start = time.time()
        with conn.cursor() as cur:
            cur.execute("REFRESH MATERIALIZED VIEW mv_cmv_loja;")
        elapsed = time.time() - start
        logger.info(f"mv_cmv_loja: REFRESH OK - {elapsed:.1f}s")

        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*), MAX(data) FROM mv_cmv_loja;")
            count2, max_data2 = cur.fetchone()
            logger.info(f"mv_cmv_loja: {count2} registros, max(data)={max_data2}")

        conn.close()
        logger.info("CONCLUIDO")
        return True

    except Exception as e:
        logger.error(f"ERRO: {e}")
        try:
            conn.close()
        except Exception:
            pass
        return False


if __name__ == "__main__":
    refresh()
