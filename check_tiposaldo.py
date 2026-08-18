from db_bridge import show_query, describe_table

print("=" * 60)
print("ESTRUTURA: prd_tiposaldof (saldos compostos)")
print("=" * 60)
describe_table('prd_tiposaldof')

print("\n" + "=" * 60)
print("DADOS: prd_tiposaldof - relação de saldos")
print("=" * 60)
query = """
SELECT * FROM prd_tiposaldof ORDER BY cd_saldo, cd_saldof
"""
show_query(query)

print("\n" + "=" * 60)
print("TIPOS DE SALDO USADOS (cd_saldo = 1 e cd_saldo = 7)")
print("=" * 60)
query = """
SELECT
    t.cd_saldo,
    t.cd_saldof,
    COUNT(DISTINCT s.cd_produto) as produtos_com_saldo,
    SUM(s.qt_saldo) as total_saldo
FROM prd_tiposaldof t
LEFT JOIN prd_prdsaldo s ON s.cd_saldo = t.cd_saldof AND s.cd_empresa = 1
WHERE t.cd_saldo IN (1, 7)
GROUP BY t.cd_saldo, t.cd_saldof
ORDER BY t.cd_saldo, t.cd_saldof
"""
show_query(query)

print("\n" + "=" * 60)
print("SALDO DIRETO vs SALDO COMPOSTO para produto exemplo")
print("=" * 60)
query = """
WITH produto_teste AS (
    SELECT 36751 AS cd_produto
)
SELECT
    pt.cd_produto,
    -- Saldo direto cd_saldo = 1
    (SELECT qt_saldo FROM prd_prdsaldo
     WHERE cd_empresa = 1 AND cd_saldo = 1 AND cd_produto = pt.cd_produto
     ORDER BY dt_saldo DESC LIMIT 1) as saldo_direto_1,
    -- Saldo via função
    f_prd_saldo_produto(1, 1, pt.cd_produto, NULL) as saldo_funcao_1,
    -- Saldo direto cd_saldo = 7
    (SELECT qt_saldo FROM prd_prdsaldo
     WHERE cd_empresa = 1 AND cd_saldo = 7 AND cd_produto = pt.cd_produto
     ORDER BY dt_saldo DESC LIMIT 1) as saldo_direto_7,
    -- Saldo via função
    f_prd_saldo_produto(1, 7, pt.cd_produto, NULL) as saldo_funcao_7
FROM produto_teste pt
"""
show_query(query)

print("\n" + "=" * 60)
print("ANÁLISE: Quais cd_saldo existem para o produto 36751")
print("=" * 60)
query = """
SELECT cd_saldo, dt_saldo, qt_saldo
FROM prd_prdsaldo
WHERE cd_empresa = 1 AND cd_produto = 36751
ORDER BY cd_saldo, dt_saldo DESC
"""
show_query(query)
