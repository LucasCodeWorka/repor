"""
Atualiza mv_cmv_fab (agora uma tabela normal, nao mais materialized view
-- ver criar_tabela_cmv_fab.py).

Em vez de recalcular 2025-01-01 ate hoje a cada rodada (REFRESH
MATERIALIZED VIEW levava ~6h e travava a leitura durante todo o periodo),
apaga e reinsere so a janela recente -- leva segundos e nao trava leitura.

Efeito colateral conhecido e desejado: os custos vem de
f_prd_valor_produto2(..., NULL) = custo de hoje. No REFRESH completo isso
recalculava o CMV de TODOS os meses passados com o custo atual (janeiro
mudava de valor se o custo de uma materia-prima mudasse hoje). Com a
janela movel, os meses fechados ficam congelados com o custo da epoca.
"""

import os
import time
import logging
from dotenv import load_dotenv
import psycopg2

from cmv_fab_sql import CMV_FAB_SQL

JANELA_DIAS = 10  # reprocessa os ultimos N dias a cada rodada
LOG_FILE = os.path.join(os.path.dirname(__file__), 'refresh_cmv_fab.log')

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
    logger.info(f"INICIANDO REFRESH incremental mv_cmv_fab (ultimos {JANELA_DIAS} dias)")
    start = time.time()

    conn = None
    try:
        conn = get_connection()
        conn.autocommit = False
        cur = conn.cursor()

        # corte calculado no banco, pra evitar divergencia de timezone
        cur.execute("SELECT (CURRENT_DATE - %(dias)s * INTERVAL '1 day')::date", {'dias': JANELA_DIAS})
        corte = cur.fetchone()[0]

        cur.execute("DELETE FROM mv_cmv_fab WHERE data >= %(corte)s::date;", {'corte': corte})
        logger.info(f"Removidas {cur.rowcount:,} linhas da janela >= {corte} (serao recalculadas)")

        cur.execute(f"INSERT INTO mv_cmv_fab {CMV_FAB_SQL}", {'corte': corte})
        logger.info(f"Inseridas {cur.rowcount:,} linhas atualizadas")

        conn.commit()

        cur.execute("SELECT count(*), max(data) FROM mv_cmv_fab;")
        total, max_data = cur.fetchone()
        logger.info(f"REFRESH concluido em {time.time()-start:.1f}s - total {total:,} linhas, max(data) = {max_data}")

        conn.close()
        return True

    except Exception as e:
        logger.error(f"ERRO no refresh: {e}")
        try:
            conn.rollback()
            conn.close()
        except Exception:
            pass
        return False


if __name__ == "__main__":
    refresh()
