"""
Reconstroi mv_vendas_qtd como tabela normal, sem precisar reprocessar
2025-01-01 ate hoje:
  1. Copia o que a materialized view ja tem (instantaneo, ja esta pronto
     ate 28/09 do ultimo REFRESH).
  2. Completa so a janela recente (29/09 em diante) com a mesma logica
     de vr_vendas_qtd.
  3. Troca o nome atomicamente: a tabela nova vira mv_vendas_qtd, a
     materialized view antiga fica guardada como mv_vendas_qtd_old_mv.

Dai pra frente, mv_vendas_qtd e uma TABELA normal -- pra manter
atualizada, so rodar de novo a partir do passo 2 (DELETE + INSERT da
janela recente), sem nunca mais precisar de REFRESH MATERIALIZED VIEW
completo.
"""

import os
import time
from dotenv import load_dotenv
import psycopg2

load_dotenv()

CORTE = '2026-09-29'  # inicio da janela a reprocessar (dados ja cobertos ate 28/09)

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
print('1/4 copiando dados ja existentes da materialized view (ate 28/09)...')
cur.execute("DROP TABLE IF EXISTS mv_vendas_qtd_new;")
cur.execute("""
    CREATE TABLE mv_vendas_qtd_new AS
    SELECT * FROM mv_vendas_qtd WHERE data < %(corte)s::date;
""", {'corte': CORTE})
print(f'   ok em {time.time()-t0:.1f}s')

t1 = time.time()
print(f'2/4 completando janela recente (>= {CORTE})...')
cur.execute(f"""
    INSERT INTO mv_vendas_qtd_new
    {VENDAS_QTD_SQL}
""", {'corte': CORTE})
print(f'   ok em {time.time()-t1:.1f}s')

cur.execute("SELECT count(*), max(data) FROM mv_vendas_qtd_new;")
total, max_data = cur.fetchone()
print(f'3/4 total na tabela nova: {total:,} linhas, max(data) = {max_data}')

print('4/4 trocando nomes atomicamente...')
cur.execute("ALTER MATERIALIZED VIEW mv_vendas_qtd RENAME TO mv_vendas_qtd_old_mv;")
cur.execute("ALTER TABLE mv_vendas_qtd_new RENAME TO mv_vendas_qtd;")
cur.execute("CREATE INDEX idx_mv_vendas_qtd_empresa_produto_data ON mv_vendas_qtd (idempresa, idproduto, data);")
cur.execute("CREATE INDEX idx_mv_vendas_qtd_data ON mv_vendas_qtd (data);")
conn.commit()

print()
print(f'Concluido em {time.time()-t0:.1f}s total.')
print('mv_vendas_qtd agora e uma TABELA normal (mesma estrutura/nome).')
print('A materialized view antiga ficou guardada como mv_vendas_qtd_old_mv (pode apagar depois de confirmar).')
conn.close()
