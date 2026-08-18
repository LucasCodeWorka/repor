"""
Benchmark: View Original vs View Otimizada V2
"""
from db_bridge import execute_query, show_query
import time

def benchmark(name, query, limit=100):
    """Executa uma query e retorna tempo e contagem"""
    print(f"\n{'='*60}")
    print(f"BENCHMARK: {name}")
    print('='*60)

    start = time.time()
    try:
        columns, rows = execute_query(query, limit=limit)
        elapsed = time.time() - start

        if columns:
            print(f"Colunas: {len(columns)}")
            print(f"Rows (limit {limit}): {len(rows)}")
            print(f"Tempo: {elapsed:.2f}s")
            if rows:
                print(f"Primeira row: {rows[0][:5]}...")
            return elapsed, len(rows)
        return elapsed, 0
    except Exception as e:
        elapsed = time.time() - start
        print(f"ERRO: {e}")
        return elapsed, 0


# Ler a view otimizada
with open('view_otimizada_v2.sql', 'r', encoding='utf-8') as f:
    view_otimizada = f.read()

# Ler a view original
with open('geovendas.sql', 'r', encoding='utf-8') as f:
    view_original = f.read()

print("\n" + "="*60)
print("TESTE 1: Apenas o primeiro UNION (30 dias) - Contagem")
print("="*60)

# Simplificado para teste - apenas conta registros do primeiro UNION
query_original_count = """
SELECT COUNT(*) as total
FROM (
    SELECT a.cd_produto
    FROM vr_prd_prdgrade a,
        vr_prd_prdinfo b
    WHERE b.cd_produto = a.cd_produto
      AND (f_dic_prd_classificacao(a.cd_produto, 'CD', 124) IN ('001', '002', '007', '004', '005')
           OR f_dic_prd_classificacao(a.cd_produto, 'CD', 124) IS NULL)
      AND b.in_inativo = 'F'
      AND a.cd_cor <> 'LF        '
      AND b.cd_empresa = 1
      AND f_dic_prd_classificacao(a.cd_produto, 'CD', 20) IN ('0001', '0002', '0003', '0020', '0009')
      AND (a.cd_produto < 1000000 OR a.cd_produto IN (5001609, 5001610, 5001319, 5001611))
    LIMIT 1000
) x
"""

query_otimizada_count = """
WITH classificacoes AS (
    SELECT
        pc.cd_produto,
        MAX(CASE WHEN pc.cd_tipoclas = 20 THEN TRIM(pc.cd_classificacao) END) AS clas_20,
        MAX(CASE WHEN pc.cd_tipoclas = 124 THEN TRIM(pc.cd_classificacao) END) AS clas_124
    FROM prd_produtoclas pc
    WHERE pc.cd_tipoclas IN (20, 124)
    GROUP BY pc.cd_produto
)
SELECT COUNT(*) as total
FROM (
    SELECT a.cd_produto
    FROM vr_prd_prdgrade a
    JOIN vr_prd_prdinfo b ON b.cd_produto = a.cd_produto AND b.cd_empresa = 1
    LEFT JOIN classificacoes c ON c.cd_produto = a.cd_produto
    WHERE b.in_inativo = 'F'
      AND a.cd_cor <> 'LF        '
      AND c.clas_20 IN ('0001', '0002', '0003', '0020', '0009')
      AND (c.clas_124 IN ('001', '002', '007', '004', '005') OR c.clas_124 IS NULL)
      AND (a.cd_produto < 1000000 OR a.cd_produto IN (5001609, 5001610, 5001319, 5001611))
    LIMIT 1000
) x
"""

t1, c1 = benchmark("Original (com funções) - 1000 rows", query_original_count, 1)
t2, c2 = benchmark("Otimizada (com JOINs) - 1000 rows", query_otimizada_count, 1)

print(f"\n>>> Speedup: {t1/t2:.1f}x mais rápido")

print("\n" + "="*60)
print("TESTE 2: Query completa com saldos (10 produtos)")
print("="*60)

query_original_full = """
SELECT
    a.cd_produto,
    COALESCE(f_prd_saldo_produto(1, 1, a.cd_produto, NULL), 0) as saldo_dep1,
    COALESCE(f_prd_saldo_produto(1, 7, a.cd_produto, NULL), 0) as saldo_dep7,
    f_dic_prd_classificacao(a.cd_produto, 'CD', 20) as familia,
    f_dic_prd_classificacao(a.cd_produto, 'CD', 21) as colecao,
    f_dic_prd_classificacao(a.cd_produto, 'CD', 27) as status
FROM vr_prd_prdgrade a
JOIN vr_prd_prdinfo b ON b.cd_produto = a.cd_produto AND b.cd_empresa = 1
WHERE b.in_inativo = 'F'
  AND a.cd_produto < 1000000
LIMIT 10
"""

query_otimizada_full = """
WITH classificacoes AS (
    SELECT
        pc.cd_produto,
        MAX(CASE WHEN pc.cd_tipoclas = 20 THEN TRIM(pc.cd_classificacao) END) AS clas_20,
        MAX(CASE WHEN pc.cd_tipoclas = 21 THEN TRIM(pc.cd_classificacao) END) AS clas_21,
        MAX(CASE WHEN pc.cd_tipoclas = 27 THEN TRIM(pc.cd_classificacao) END) AS clas_27
    FROM prd_produtoclas pc
    WHERE pc.cd_tipoclas IN (20, 21, 27)
    GROUP BY pc.cd_produto
),
saldos_atuais AS (
    SELECT DISTINCT ON (cd_produto, cd_saldo)
        cd_produto,
        cd_saldo,
        qt_saldo
    FROM prd_prdsaldo
    WHERE cd_empresa = 1 AND cd_saldo IN (1, 7)
    ORDER BY cd_produto, cd_saldo, dt_saldo DESC
),
saldos_pivot AS (
    SELECT
        cd_produto,
        COALESCE(MAX(CASE WHEN cd_saldo = 1 THEN qt_saldo END), 0) AS saldo_dep1,
        COALESCE(MAX(CASE WHEN cd_saldo = 7 THEN qt_saldo END), 0) AS saldo_dep7
    FROM saldos_atuais
    GROUP BY cd_produto
)
SELECT
    a.cd_produto,
    COALESCE(s.saldo_dep1, 0) as saldo_dep1,
    COALESCE(s.saldo_dep7, 0) as saldo_dep7,
    c.clas_20 as familia,
    c.clas_21 as colecao,
    c.clas_27 as status
FROM vr_prd_prdgrade a
JOIN vr_prd_prdinfo b ON b.cd_produto = a.cd_produto AND b.cd_empresa = 1
LEFT JOIN classificacoes c ON c.cd_produto = a.cd_produto
LEFT JOIN saldos_pivot s ON s.cd_produto = a.cd_produto
WHERE b.in_inativo = 'F'
  AND a.cd_produto < 1000000
LIMIT 10
"""

t1, c1 = benchmark("Original (funções saldo + classificação)", query_original_full, 10)
t2, c2 = benchmark("Otimizada (JOINs diretos)", query_otimizada_full, 10)

print(f"\n>>> Speedup: {t1/t2:.1f}x mais rápido")

print("\n" + "="*60)
print("TESTE 3: View completa otimizada V2 (primeiro UNION apenas)")
print("="*60)

query_view_v2_union1 = """
WITH
classificacoes AS (
    SELECT
        pc.cd_produto,
        MAX(CASE WHEN pc.cd_tipoclas = 20 THEN TRIM(pc.cd_classificacao) END) AS clas_20,
        MAX(CASE WHEN pc.cd_tipoclas = 21 THEN TRIM(pc.cd_classificacao) END) AS clas_21,
        MAX(CASE WHEN pc.cd_tipoclas = 27 THEN TRIM(pc.cd_classificacao) END) AS clas_27,
        MAX(CASE WHEN pc.cd_tipoclas = 124 THEN TRIM(pc.cd_classificacao) END) AS clas_124
    FROM prd_produtoclas pc
    WHERE pc.cd_tipoclas IN (20, 21, 27, 124)
    GROUP BY pc.cd_produto
),
colecao_desc AS (
    SELECT TRIM(cd_classificacao) AS cd_classificacao, ds_classificacao
    FROM prd_classificacao WHERE cd_tipoclas = 21
),
saldos_atuais AS (
    SELECT DISTINCT ON (cd_produto, cd_saldo)
        cd_produto, cd_saldo, qt_saldo
    FROM prd_prdsaldo
    WHERE cd_empresa = 1 AND cd_saldo IN (1, 7)
    ORDER BY cd_produto, cd_saldo, dt_saldo DESC
),
saldos_pivot AS (
    SELECT cd_produto,
        COALESCE(MAX(CASE WHEN cd_saldo = 1 THEN qt_saldo END), 0) AS saldo_dep1,
        COALESCE(MAX(CASE WHEN cd_saldo = 7 THEN qt_saldo END), 0) AS saldo_dep7
    FROM saldos_atuais GROUP BY cd_produto
),
pedidos_pendentes AS (
    SELECT cd_produto, COALESCE(SUM(qt_pendente), 0) AS qt_pendente
    FROM vr_ped_pedidoi
    WHERE cd_operacao <> 44 AND cd_empresa = 1 AND tp_situacao <> 6
    GROUP BY cd_produto
),
ops_producao AS (
    SELECT aa.cd_produto, SUM(COALESCE(aa.qt_real, 0) - COALESCE(aa.qt_finalizada, 0)) AS qt_op
    FROM vr_pcp_opi aa
    JOIN vr_pcp_opc bb ON aa.cd_empresa = bb.cd_empresa AND aa.nr_ciclo = bb.nr_ciclo AND aa.nr_op = bb.nr_op
    WHERE aa.cd_empresa = 1 AND COALESCE(bb.cd_categoria, 0) <> 15 AND aa.tp_situacao IN (5, 10, 15, 20)
    GROUP BY aa.cd_produto
)
SELECT COUNT(*) as total
FROM vr_prd_prdgrade a
JOIN vr_prd_prdinfo b ON b.cd_produto = a.cd_produto AND b.cd_empresa = 1 AND b.in_inativo = 'F'
LEFT JOIN classificacoes c ON c.cd_produto = a.cd_produto
LEFT JOIN saldos_pivot s ON s.cd_produto = a.cd_produto
LEFT JOIN pedidos_pendentes pp ON pp.cd_produto = a.cd_produto
LEFT JOIN ops_producao op ON op.cd_produto = a.cd_produto
WHERE a.cd_cor <> 'LF        '
  AND c.clas_20 IN ('0001', '0002', '0003', '0020', '0009')
  AND (c.clas_124 IN ('001', '002', '007', '004', '005') OR c.clas_124 IS NULL)
  AND (a.cd_produto < 1000000 OR a.cd_produto IN (5001609, 5001610, 5001319, 5001611))
"""

t3, c3 = benchmark("View V2 - Contagem total de produtos base", query_view_v2_union1, 1)

print("\n" + "="*60)
print("RESUMO")
print("="*60)
print("""
A view otimizada V2 substitui:
1. f_dic_prd_classificacao() -> JOIN com prd_produtoclas (PIVÔ)
2. f_prd_saldo_produto() -> Query direta em prd_prdsaldo (DISTINCT ON)
3. Subqueries correlacionadas -> CTEs pré-calculadas

Benefícios esperados:
- Eliminação de loops PL/pgSQL nas funções
- Uma única passagem pelos dados ao invés de N chamadas de função
- Melhor uso do plano de execução do PostgreSQL
""")
