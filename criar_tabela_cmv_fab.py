"""
Converte mv_cmv_fab de materialized view para TABELA normal, mantendo o
mesmo nome -- mesma ideia do que foi feito com mv_vendas_qtd.

Motivo: o REFRESH MATERIALIZED VIEW completo levava ~6h (recalculava
2025-01-01 ate hoje toda vez, com f_prd_valor_produto2 chamada por linha)
e travava a leitura da view durante todo esse tempo.

Passos:
  1. Copia os dados que a materialized view ja tem (instantaneo).
  2. Troca os nomes: a tabela nova vira mv_cmv_fab, a materialized view
     antiga fica guardada como mv_cmv_fab_old_mv (pode apagar depois de
     confirmar que esta tudo certo).
  3. Cria indices.

Dai pra frente quem mantem atualizada e o refresh_cmv_fab.py, que so
recalcula a janela recente (DELETE + INSERT), em segundos.
"""

import os
import time
from dotenv import load_dotenv
import psycopg2

load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

conn = psycopg2.connect(
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
conn.autocommit = False
cur = conn.cursor()

t0 = time.time()
print('1/4 copiando os dados que mv_cmv_fab ja tem...')
cur.execute("DROP TABLE IF EXISTS mv_cmv_fab_new;")
cur.execute("CREATE TABLE mv_cmv_fab_new AS SELECT * FROM mv_cmv_fab;")
cur.execute("SELECT count(*), min(data), max(data) FROM mv_cmv_fab_new;")
total, min_data, max_data = cur.fetchone()
print(f'   {total:,} linhas, de {min_data} ate {max_data}. {time.time()-t0:.1f}s')

if not total:
    raise SystemExit('ABORTADO: a copia ficou vazia.')

t1 = time.time()
print('2/4 trocando os nomes...')
cur.execute("ALTER MATERIALIZED VIEW mv_cmv_fab RENAME TO mv_cmv_fab_old_mv;")
cur.execute("ALTER TABLE mv_cmv_fab_new RENAME TO mv_cmv_fab;")
print(f'   ok. {time.time()-t1:.1f}s')

t2 = time.time()
print('3/4 criando indices...')
cur.execute("CREATE INDEX idx_mv_cmv_fab_data ON mv_cmv_fab (data);")
cur.execute("CREATE INDEX idx_mv_cmv_fab_conta_data ON mv_cmv_fab (idconta, data);")
cur.execute("CREATE INDEX idx_mv_cmv_fab_produto ON mv_cmv_fab (idproduto);")
print(f'   ok. {time.time()-t2:.1f}s')

conn.commit()

print('4/4 conferindo resultado final...')
cur.execute("SELECT count(*), min(data), max(data) FROM mv_cmv_fab;")
print('   mv_cmv_fab (agora tabela):', cur.fetchone())

print()
print(f'Concluido em {time.time()-t0:.1f}s.')
print('A materialized view antiga ficou como mv_cmv_fab_old_mv (apagar depois de confirmar).')
conn.close()
