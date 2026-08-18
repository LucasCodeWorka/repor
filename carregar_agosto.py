"""
Carrega agosto 2026 - necessidade projetada
"""

import os
from dotenv import load_dotenv
import psycopg2
import pandas as pd
from datetime import datetime

load_dotenv()

conn = psycopg2.connect(
    host=os.getenv('DB_HOST'),
    port=os.getenv('DB_PORT'),
    dbname=os.getenv('DB_NAME'),
    user=os.getenv('DB_USER'),
    password=os.getenv('DB_PASSWORD')
)

mes = '2026-08'
inicio_mes = '2026-08-01'
fim_mes = '2026-09-01'
lote_periodo = '26.08%'

print(f'Carregando {mes} (lote: {lote_periodo})')
print(f'Vendas base: maio/junho/julho 2026')
print()

query = """
INSERT INTO extrato_reposicao_loja_perm_analitico
WITH produtos_permanente AS (
    SELECT DISTINCT pc.cd_produto
    FROM prd_produtoclas pc
    JOIN prd_classificacao c
        ON pc.cd_classificacao = c.cd_classificacao
        AND pc.cd_tipoclas = c.cd_tipoclas
    WHERE pc.cd_tipoclas = 802
      AND c.ds_classificacao IN ('PERMANENTE', 'PERMANENTE COR NOVA')
),

entradas_mes AS (
    SELECT
        %(mes)s AS mes,
        t.cd_empresa AS cd_loja,
        i.cd_produto,
        i.qt_solicitada AS qt_entrada,
        t.nr_transacao,
        i.dt_transacao,
        lote.cd_lote,
        CASE
            WHEN lote.cd_lote LIKE %(lote_periodo)s THEN 'PERIODO'
            WHEN lote.cd_lote IS NULL THEN 'SEM_LOTE'
            ELSE 'ATRASADA'
        END AS tipo_entrada
    FROM vr_tra_transacao t
    JOIN vr_tra_transitem i
        ON t.nr_transacao = i.nr_transacao
        AND t.cd_empresa = i.cd_empresa
    LEFT JOIN vr_ped_pedidotra ped
        ON ped.nr_transacao = t.nr_transacaoori
    LEFT JOIN vr_ped_pedidoc2 lote
        ON ped.cd_emppedido = lote.cd_empresa
        AND ped.cd_pedido = lote.cd_pedido
        AND ped.cd_representant = lote.cd_representant
    WHERE t.cd_empresa > 1
      AND t.cd_empresa <> 4
      AND t.tp_operacao = 'E'
      AND t.tp_modalidade::text = '2'
      AND t.tp_situacao = 4
      AND t.cd_empresaori = 1
      AND i.dt_transacao >= %(inicio_mes)s::date
      AND i.dt_transacao < %(fim_mes)s::date
),

entradas_agregadas AS (
    SELECT
        mes,
        cd_loja,
        cd_produto,
        COALESCE(SUM(qt_entrada) FILTER (WHERE tipo_entrada = 'PERIODO'), 0) AS entrada_periodo,
        COALESCE(SUM(qt_entrada) FILTER (WHERE tipo_entrada = 'ATRASADA'), 0) AS entrada_atrasada,
        COALESCE(SUM(qt_entrada) FILTER (WHERE tipo_entrada = 'SEM_LOTE'), 0) AS entrada_sem_lote,
        COALESCE(SUM(qt_entrada), 0) AS entrada_total,
        COUNT(DISTINCT nr_transacao) FILTER (WHERE tipo_entrada = 'PERIODO') AS qtd_transacoes_periodo,
        COUNT(DISTINCT nr_transacao) FILTER (WHERE tipo_entrada = 'ATRASADA') AS qtd_transacoes_atrasadas,
        MIN(dt_transacao) AS primeira_entrada,
        MAX(dt_transacao) AS ultima_entrada,
        STRING_AGG(DISTINCT cd_lote, ', ' ORDER BY cd_lote) AS lotes_entrada
    FROM entradas_mes
    GROUP BY mes, cd_loja, cd_produto
),

vendas_3m AS (
    SELECT
        %(mes)s AS mes,
        %(inicio_mes)s::date AS inicio_mes,
        t.cd_empresa AS cd_loja,
        i.cd_produto,
        SUM(
            i.qt_solicitada *
            CASE WHEN t.tp_modalidade::text = '3' THEN -1 ELSE 1 END
        ) AS vendas_3m
    FROM vr_tra_transacao t
    JOIN vr_tra_transitem i
        ON t.nr_transacao = i.nr_transacao
        AND t.cd_empresa = i.cd_empresa
    WHERE t.cd_empresa > 1
      AND t.cd_empresa <> 4
      AND t.cd_operacao NOT IN (
          140, 76, 25, 26, 27, 273, 44,
          240, 241, 242, 243, 244, 245,
          239, 238, 237, 236
      )
      AND i.dt_transacao >= %(inicio_mes)s::date - INTERVAL '3 months'
      AND i.dt_transacao < %(inicio_mes)s::date
      AND i.cd_compvend <> 1
      AND t.tp_situacao <> 6
      AND t.tp_modalidade::text IN ('3', '4')
    GROUP BY t.cd_empresa, i.cd_produto
    HAVING SUM(
        i.qt_solicitada *
        CASE WHEN t.tp_modalidade::text = '3' THEN -1 ELSE 1 END
    ) > 0
),

base_sem_curva AS (
    SELECT
        v.mes,
        v.cd_loja,
        emp.nm_grupoempresa AS nome_loja,
        v.cd_produto,
        f_dic_prd_nivel(v.cd_produto, 'CD'::bpchar) AS referencia,
        f_dic_prd_nivel(v.cd_produto, 'DS'::bpchar) AS descricao_produto,
        v.vendas_3m,
        ROUND(v.vendas_3m / 3.0, 2) AS media_mensal,
        ROUND(v.vendas_3m / 3.0 * 1.5, 0) AS estoque_minimo,
        COALESCE(
            f_prd_saldo_produto(
                v.cd_loja,
                1::bigint,
                v.cd_produto,
                v.inicio_mes
            ),
            0
        ) AS saldo_inicial
    FROM vendas_3m v
    JOIN vr_ger_empresa emp
        ON v.cd_loja = emp.cd_empresa
    JOIN produtos_permanente pp
        ON v.cd_produto = pp.cd_produto
),

base AS (
    SELECT
        b.*,
        COALESCE(abc.curva_completa, 'SEM CURVA') AS curva_completa
    FROM base_sem_curva b
    LEFT JOIN curva_abc abc
        ON abc.referencia = b.referencia
),

analise AS (
    SELECT
        b.*,
        GREATEST(0, b.estoque_minimo - b.saldo_inicial) AS necessidade,
        COALESCE(e.entrada_periodo, 0) AS entrada_periodo,
        COALESCE(e.entrada_atrasada, 0) AS entrada_atrasada,
        COALESCE(e.entrada_sem_lote, 0) AS entrada_sem_lote,
        COALESCE(e.entrada_total, 0) AS entrada_total,
        COALESCE(e.qtd_transacoes_periodo, 0) AS qtd_transacoes_periodo,
        COALESCE(e.qtd_transacoes_atrasadas, 0) AS qtd_transacoes_atrasadas,
        e.primeira_entrada,
        e.ultima_entrada,
        e.lotes_entrada
    FROM base b
    LEFT JOIN entradas_agregadas e
        ON b.mes = e.mes
        AND b.cd_loja = e.cd_loja
        AND b.cd_produto = e.cd_produto
)

SELECT
    mes,
    cd_loja,
    nome_loja,
    cd_produto,
    referencia,
    descricao_produto,
    curva_completa,
    vendas_3m,
    media_mensal,
    estoque_minimo,
    saldo_inicial,
    necessidade,
    entrada_periodo,
    entrada_atrasada,
    entrada_sem_lote,
    entrada_total,
    GREATEST(0, necessidade - entrada_total) AS faltou,
    GREATEST(0, entrada_periodo - necessidade) AS sobra_periodo,
    qtd_transacoes_periodo,
    qtd_transacoes_atrasadas,
    primeira_entrada,
    ultima_entrada,
    lotes_entrada,
    CASE
        WHEN necessidade <= 0 THEN 'SEM NECESSIDADE'
        WHEN entrada_total >= necessidade THEN 'OK'
        WHEN entrada_total > 0 THEN 'PARCIAL'
        ELSE 'SEM ENTRADA'
    END AS status_reposicao,
    CASE
        WHEN entrada_atrasada > 0 AND entrada_periodo > 0 THEN 'PERIODO + ATRASADA'
        WHEN entrada_atrasada > 0 THEN 'SOMENTE ATRASADA'
        WHEN entrada_sem_lote > 0 THEN 'FABRICA SEM LOTE'
        WHEN entrada_periodo > 0 THEN 'SOMENTE PERIODO'
        ELSE 'SEM ENTRADA'
    END AS status_entrada
FROM analise;
"""

cur = conn.cursor()
inicio = datetime.now()

# Limpar dados anteriores de agosto se existirem
cur.execute("DELETE FROM extrato_reposicao_loja_perm_analitico WHERE mes = %s", (mes,))

cur.execute(query, {
    'mes': mes,
    'inicio_mes': inicio_mes,
    'fim_mes': fim_mes,
    'lote_periodo': lote_periodo
})

conn.commit()

cur.execute("SELECT COUNT(*) FROM extrato_reposicao_loja_perm_analitico WHERE mes = %s", (mes,))
count = cur.fetchone()[0]

duracao = (datetime.now() - inicio).total_seconds()
print(f'Inseridos {count:,} registros em {duracao:.1f}s')

# Resumo de agosto
df = pd.read_sql("""
    SELECT
        cd_loja,
        nome_loja,
        SUM(estoque_minimo) AS estoque_minimo,
        SUM(saldo_inicial) AS saldo_01ago,
        SUM(necessidade) AS necessidade,
        SUM(entrada_total) AS entrada_ate_agora,
        SUM(faltou) AS falta_prevista,
        COUNT(*) FILTER (WHERE necessidade > 0) AS skus_demanda,
        COUNT(*) FILTER (WHERE status_reposicao = 'OK') AS skus_ok,
        COUNT(*) FILTER (WHERE status_reposicao = 'SEM ENTRADA') AS skus_sem_entrada
    FROM extrato_reposicao_loja_perm_analitico
    WHERE mes = '2026-08'
    GROUP BY cd_loja, nome_loja
    ORDER BY cd_loja
""", conn)

print()
print('AGOSTO 2026 - NECESSIDADE vs SALDO INICIAL (01/AGO)')
print('='*140)
print(df.to_string(index=False))

# Total geral
print()
print('TOTAIS:')
print(f"  Estoque Minimo Total: {df['estoque_minimo'].sum():,.0f}")
print(f"  Saldo em 01/Ago:      {df['saldo_01ago'].sum():,.0f}")
print(f"  Necessidade:          {df['necessidade'].sum():,.0f}")
print(f"  Entrada ate agora:    {df['entrada_ate_agora'].sum():,.0f}")
print(f"  Falta Prevista:       {df['falta_prevista'].sum():,.0f}")

conn.close()
