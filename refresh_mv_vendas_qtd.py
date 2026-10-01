"""
Atualiza mv_vendas_qtd (agora uma tabela normal, nao mais materialized
view -- ver reconstruir_mv_vendas_qtd.py).

Em vez de reprocessar 2025-01-01 ate hoje (o que levava 80+ minutos e
travava outras consultas), atualiza so a janela recente: apaga e
reinsere os ultimos N dias (cobre corrigcoes/lancamentos atrasados)
com a mesma logica de vr_vendas_qtd. Isso leva segundos, nao horas, e
nao precisa de REFRESH MATERIALIZED VIEW (tabela normal nao trava
leitura durante o DELETE/INSERT).
"""

import os
import time
import logging
from dotenv import load_dotenv
import psycopg2

JANELA_DIAS = 10  # reprocessa os ultimos N dias a cada rodada (cobre lancamento atrasado)
LOG_FILE = os.path.join(os.path.dirname(__file__), 'refresh_mv_vendas_qtd.log')

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

VENDAS_QTD_SQL = """
    SELECT t.cd_empresa AS idempresa,
        i.dt_transacao AS data,
        i.cd_produto AS idproduto,
        sum(i.qt_solicitada *
            CASE WHEN t.tp_modalidade::text = '3' THEN -1 ELSE 1 END::double precision
        ) AS qt_liquida
    FROM vr_tra_transacao t
    JOIN vr_tra_transitem i ON t.nr_transacao = i.nr_transacao AND t.cd_empresa = i.cd_empresa
    WHERE t.cd_empresa <> 1
      AND t.cd_operacao <> ALL (ARRAY[140,76,25,26,27,273,44,240,241,242,243,244,245,239,238,237,236]::bigint[])
      AND i.dt_transacao >= %(corte)s::date
      AND i.cd_compvend <> 1
      AND t.tp_situacao <> 6
      AND t.tp_modalidade::text = ANY (ARRAY['3','4'])
    GROUP BY t.cd_empresa, i.dt_transacao, i.cd_produto

    UNION ALL

    SELECT c.cd_empresa AS idempresa,
        c.dt_pedido AS data,
        i.cd_produto AS idproduto,
        sum(i.qt_solicitada) AS qt_liquida
    FROM vr_ped_pedidoc2 c
    LEFT JOIN vr_ped_pedidoi i ON c.cd_empresa = i.cd_empresa AND i.cd_pedido = c.cd_pedido
    WHERE c.dt_pedido >= %(corte)s::date
      AND c.cd_cliente <> 110000001
      AND c.cd_representant <> 32098
      AND c.tp_situacao <> 6
      AND c.cd_empresa = 1
      AND c.cd_operacao = ANY (ARRAY[1,18,52,166,148,98,55,97,30,79,93,137,141,142,156,159,310,598,180,58,69,85,124,182]::bigint[])
    GROUP BY c.cd_empresa, c.dt_pedido, i.cd_produto
"""


def get_connection():
    return psycopg2.connect(
        host=os.getenv('DB_HOST'),
        port=os.getenv('DB_PORT'),
        dbname=os.getenv('DB_NAME'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD'),
    )


def refresh():
    logger.info("=" * 50)
    logger.info(f"INICIANDO REFRESH incremental mv_vendas_qtd (ultimos {JANELA_DIAS} dias)")
    start = time.time()

    # corte = CURRENT_DATE - JANELA_DIAS, calculado no banco pra evitar
    # divergencia de timezone entre app e servidor
    try:
        conn = get_connection()
        conn.autocommit = False
        cur = conn.cursor()

        cur.execute("SELECT (CURRENT_DATE - %(dias)s * INTERVAL '1 day')::date", {'dias': JANELA_DIAS})
        corte = cur.fetchone()[0]

        cur.execute("DELETE FROM mv_vendas_qtd WHERE data >= %(corte)s::date;", {'corte': corte})
        deletadas = cur.rowcount
        logger.info(f"Removidas {deletadas:,} linhas da janela >= {corte} (serao recalculadas)")

        cur.execute(f"INSERT INTO mv_vendas_qtd {VENDAS_QTD_SQL}", {'corte': corte})
        inseridas = cur.rowcount
        logger.info(f"Inseridas {inseridas:,} linhas atualizadas")

        conn.commit()

        cur.execute("SELECT count(*), max(data) FROM mv_vendas_qtd;")
        total, max_data = cur.fetchone()

        elapsed = time.time() - start
        logger.info(f"REFRESH concluido em {elapsed:.1f}s - total {total:,} linhas, max(data) = {max_data}")

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
