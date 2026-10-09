"""
Backfill pontual: soma a contribuicao de tp_modalidade=8 (que faltava na
formula original) ao historico de mv_vendas_qtd ja existente (< 2026-09-29),
sem reprocessar a tabela inteira.

A partir de 2026-09-29 em diante o refresh_mv_vendas_qtd.py (janela movel de
10 dias) ja recalcula com modalidade 8 incluida -- esse script so corrige o
que ja estava fechado antes disso.
"""

import os
import time
from dotenv import load_dotenv
import psycopg2

load_dotenv('C:/Users/ce_lu/OneDrive/Documentos/geo2/.env')

CORTE = '2026-09-29'  # a partir daqui o refresh incremental ja cobre modalidade 8

MODALIDADE8_SQL = """
    SELECT t.cd_empresa AS idempresa,
        i.dt_transacao AS data,
        i.cd_produto AS idproduto,
        sum(i.qt_solicitada) AS qt_liquida
    FROM vr_tra_transacao t
    JOIN vr_tra_transitem i ON t.nr_transacao = i.nr_transacao AND t.cd_empresa = i.cd_empresa
    WHERE t.cd_empresa <> 1
      AND t.cd_operacao <> ALL (ARRAY[140,76,25,26,27,273,44,240,241,242,243,244,245,239,238,237,236]::bigint[])
      AND i.dt_transacao < %(corte)s::date
      AND i.cd_compvend <> 1
      AND t.tp_situacao <> 6
      AND t.tp_modalidade::text = '8'
    GROUP BY t.cd_empresa, i.dt_transacao, i.cd_produto
"""

conn = psycopg2.connect(
    host=os.getenv('DB_HOST'),
    port=os.getenv('DB_PORT'),
    dbname=os.getenv('DB_NAME'),
    user=os.getenv('DB_USER'),
    password=os.getenv('DB_PASSWORD'),
)
conn.autocommit = False
cur = conn.cursor()

t0 = time.time()
print('1/3 criando tabela temporaria com a contribuicao de modalidade 8...')
cur.execute("DROP TABLE IF EXISTS tmp_backfill_modalidade8;")
cur.execute(f"""
    CREATE TEMP TABLE tmp_backfill_modalidade8 AS
    {MODALIDADE8_SQL}
""", {'corte': CORTE})
cur.execute("SELECT count(*), sum(qt_liquida) FROM tmp_backfill_modalidade8;")
n_linhas, total_qtd = cur.fetchone()
print(f'   {n_linhas} combinacoes (empresa,data,produto), total {total_qtd} unidades. {time.time()-t0:.1f}s')

t1 = time.time()
print('2/3 somando nas linhas existentes de mv_vendas_qtd...')
cur.execute("""
    UPDATE mv_vendas_qtd m
    SET qt_liquida = m.qt_liquida + b.qt_liquida
    FROM tmp_backfill_modalidade8 b
    WHERE m.idempresa = b.idempresa AND m.data = b.data AND m.idproduto = b.idproduto;
""")
n_update = cur.rowcount
print(f'   {n_update} linhas atualizadas. {time.time()-t1:.1f}s')

t2 = time.time()
print('3/3 inserindo combinacoes que ainda nao existiam na tabela...')
cur.execute("""
    INSERT INTO mv_vendas_qtd (idempresa, data, idproduto, qt_liquida)
    SELECT b.idempresa, b.data, b.idproduto, b.qt_liquida
    FROM tmp_backfill_modalidade8 b
    WHERE NOT EXISTS (
        SELECT 1 FROM mv_vendas_qtd m
        WHERE m.idempresa = b.idempresa AND m.data = b.data AND m.idproduto = b.idproduto
    );
""")
n_insert = cur.rowcount
print(f'   {n_insert} linhas novas inseridas. {time.time()-t2:.1f}s')

conn.commit()
print()
print(f'Concluido em {time.time()-t0:.1f}s total.')
conn.close()
