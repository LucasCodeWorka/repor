from db_bridge import show_query, describe_table

print("=" * 60)
print("ESTRUTURA: MV_PCP_ESTOQUE_ATUAL (View Materializada)")
print("=" * 60)
describe_table('mv_pcp_estoque_atual')

print("\n" + "=" * 60)
print("AMOSTRA: MV_PCP_ESTOQUE_ATUAL (5 rows)")
print("=" * 60)
query = "SELECT * FROM mv_pcp_estoque_atual LIMIT 5"
show_query(query)

print("\n" + "=" * 60)
print("ESTRUTURA: prd_prdsaldo")
print("=" * 60)
describe_table('prd_prdsaldo')

print("\n" + "=" * 60)
print("AMOSTRA: prd_prdsaldo (5 rows)")
print("=" * 60)
query = "SELECT * FROM prd_prdsaldo LIMIT 5"
show_query(query)

print("\n" + "=" * 60)
print("DEPÓSITOS USADOS NA VIEW (cd_deposito)")
print("=" * 60)
query = """
SELECT cd_deposito, COUNT(*) as qtd_registros, SUM(qt_saldo) as total_saldo
FROM prd_prdsaldo
WHERE cd_empresa = 1
GROUP BY cd_deposito
ORDER BY cd_deposito
"""
show_query(query)

print("\n" + "=" * 60)
print("COMPARAÇÃO: função vs tabela direta")
print("=" * 60)
query = """
SELECT
    s.cd_produto,
    s.cd_deposito,
    s.qt_saldo as saldo_tabela,
    f_prd_saldo_produto(1, s.cd_deposito, s.cd_produto, NULL) as saldo_funcao
FROM prd_prdsaldo s
WHERE s.cd_empresa = 1
  AND s.cd_deposito IN (1, 7)
  AND s.qt_saldo > 0
LIMIT 10
"""
show_query(query)
