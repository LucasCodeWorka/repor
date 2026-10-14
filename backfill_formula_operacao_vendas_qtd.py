"""
Backfill pontual: corrige a formula de mv_vendas_qtd para o historico ja
fechado (antes da janela movel de 10 dias, que o refresh_mv_vendas_qtd.py
ja recalcula sozinho com a formula nova).

Bug corrigido (confirmado com o usuario, dia 2026-09-30: 2387 -> 2475):
  - Operacoes 240/241/243/238 estavam na lista de exclusao por engano
    (vendas/devolucoes legitimas de modalidade 3/4 sendo cortadas).
  - tp_operacao = 'E' com modalidade != '3' estava sendo somado como se
    fosse venda (deveria contar 0 -- so modalidade 3 'E' eh devolucao,
    e so 'S' eh venda).

Em vez de reprocessar a tabela inteira, calcula so o DELTA (novo - antigo)
por linha afetada e soma direto em cima do que ja existe.
"""

import os
import time
from dotenv import load_dotenv
import psycopg2

load_dotenv('C:/Users/ce_lu/OneDrive/Documentos/geo2/.env')

JANELA_DIAS = 10  # mesmo corte do refresh incremental -- dali pra frente ele ja recalcula certo

DELTA_SQL = """
    SELECT t.cd_empresa AS idempresa,
        i.dt_transacao AS data,
        i.cd_produto AS idproduto,
        sum(i.qt_solicitada * (
            -- novo valor da linha
            (CASE
                WHEN t.cd_operacao = ANY (ARRAY[140,76,25,26,27,273,44,242,244,245,239,237,236]::bigint[]) THEN 0
                WHEN t.tp_operacao = 'E' AND t.tp_modalidade::text = '3' THEN -1
                WHEN t.tp_operacao = 'S' THEN 1
                ELSE 0
            END)
            -
            -- valor antigo da linha (formula em producao ate agora)
            (CASE
                WHEN t.cd_operacao = ANY (ARRAY[140,76,25,26,27,273,44,240,241,242,243,244,245,239,238,237,236]::bigint[]) THEN 0
                WHEN t.tp_modalidade::text = '3' THEN -1
                ELSE 1
            END)
        )::double precision) AS delta
    FROM vr_tra_transacao t
    JOIN vr_tra_transitem i ON t.nr_transacao = i.nr_transacao AND t.cd_empresa = i.cd_empresa
    WHERE t.cd_empresa <> 1
      AND i.dt_transacao >= '2025-01-01'::date
      AND i.dt_transacao < %(corte)s::date
      AND i.cd_compvend <> 1
      AND t.tp_situacao <> 6
      AND t.tp_modalidade::text = ANY (ARRAY['3','4','8'])
      AND (
            t.cd_operacao = ANY (ARRAY[240,241,243,238]::bigint[])
         OR (t.tp_operacao = 'E' AND t.tp_modalidade::text <> '3')
      )
    GROUP BY t.cd_empresa, i.dt_transacao, i.cd_produto
    HAVING sum(i.qt_solicitada * (
            (CASE
                WHEN t.cd_operacao = ANY (ARRAY[140,76,25,26,27,273,44,242,244,245,239,237,236]::bigint[]) THEN 0
                WHEN t.tp_operacao = 'E' AND t.tp_modalidade::text = '3' THEN -1
                WHEN t.tp_operacao = 'S' THEN 1
                ELSE 0
            END)
            -
            (CASE
                WHEN t.cd_operacao = ANY (ARRAY[140,76,25,26,27,273,44,240,241,242,243,244,245,239,238,237,236]::bigint[]) THEN 0
                WHEN t.tp_modalidade::text = '3' THEN -1
                ELSE 1
            END)
        )::double precision) <> 0
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
cur.execute("SELECT (CURRENT_DATE - %(dias)s * INTERVAL '1 day')::date", {'dias': JANELA_DIAS})
corte = cur.fetchone()[0]
print(f'corte (janela movel do refresh incremental): {corte}')

print('1/3 calculando delta (linhas afetadas pela correcao de formula)...')
cur.execute("DROP TABLE IF EXISTS tmp_delta_formula;")
cur.execute(f"""
    CREATE TEMP TABLE tmp_delta_formula AS
    {DELTA_SQL}
""", {'corte': corte})
cur.execute("SELECT count(*), sum(delta) FROM tmp_delta_formula;")
n_linhas, total_delta = cur.fetchone()
print(f'   {n_linhas} combinacoes (empresa,data,produto) afetadas, delta total {total_delta}. {time.time()-t0:.1f}s')

t1 = time.time()
print('2/3 somando o delta nas linhas existentes de mv_vendas_qtd...')
cur.execute("""
    UPDATE mv_vendas_qtd m
    SET qt_liquida = m.qt_liquida + d.delta
    FROM tmp_delta_formula d
    WHERE m.idempresa = d.idempresa AND m.data = d.data AND m.idproduto = d.idproduto;
""")
n_update = cur.rowcount
print(f'   {n_update} linhas atualizadas. {time.time()-t1:.1f}s')

t2 = time.time()
print('3/3 inserindo combinacoes que ainda nao existiam na tabela...')
cur.execute("""
    INSERT INTO mv_vendas_qtd (idempresa, data, idproduto, qt_liquida)
    SELECT d.idempresa, d.data, d.idproduto, d.delta
    FROM tmp_delta_formula d
    WHERE NOT EXISTS (
        SELECT 1 FROM mv_vendas_qtd m
        WHERE m.idempresa = d.idempresa AND m.data = d.data AND m.idproduto = d.idproduto
    );
""")
n_insert = cur.rowcount
print(f'   {n_insert} linhas novas inseridas. {time.time()-t2:.1f}s')

conn.commit()
print()
print(f'Concluido em {time.time()-t0:.1f}s total.')
conn.close()
