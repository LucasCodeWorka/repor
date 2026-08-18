from db_bridge import show_query

print("=" * 60)
print("SALDO 7: Existe algum produto com saldo no depósito 7?")
print("=" * 60)
query = """
SELECT
    cd_saldo,
    COUNT(DISTINCT cd_produto) as qtd_produtos,
    SUM(qt_saldo) as total_saldo
FROM prd_prdsaldo
WHERE cd_empresa = 1
  AND cd_saldo IN (1, 7)
  AND cd_produto < 1000000
GROUP BY cd_saldo
"""
show_query(query)

print("\n" + "=" * 60)
print("PRODUTOS COM SALDO NO CD_SALDO = 7")
print("=" * 60)
query = """
SELECT cd_produto, dt_saldo, qt_saldo
FROM prd_prdsaldo
WHERE cd_empresa = 1 AND cd_saldo = 7 AND qt_saldo > 0
ORDER BY qt_saldo DESC
LIMIT 20
"""
show_query(query)

print("\n" + "=" * 60)
print("PROPOSTA: Criar view de saldo otimizada")
print("=" * 60)
print("""
Ao invés de chamar f_prd_saldo_produto(1, 1, produto, NULL) para cada produto,
podemos criar uma CTE que já traz todos os saldos de uma vez:

WITH saldos_atuais AS (
    SELECT DISTINCT ON (cd_produto, cd_saldo)
        cd_produto,
        cd_saldo,
        qt_saldo
    FROM prd_prdsaldo
    WHERE cd_empresa = 1
      AND cd_saldo IN (1, 7)
      AND cd_produto < 1000000
    ORDER BY cd_produto, cd_saldo, dt_saldo DESC
)
SELECT
    cd_produto,
    COALESCE(MAX(CASE WHEN cd_saldo = 1 THEN qt_saldo END), 0) as saldo_dep1,
    COALESCE(MAX(CASE WHEN cd_saldo = 7 THEN qt_saldo END), 0) as saldo_dep7
FROM saldos_atuais
GROUP BY cd_produto
""")

# Testar a CTE proposta
print("\n" + "=" * 60)
print("TESTE: CTE de saldos otimizada (10 rows)")
print("=" * 60)
query = """
WITH saldos_atuais AS (
    SELECT DISTINCT ON (cd_produto, cd_saldo)
        cd_produto,
        cd_saldo,
        qt_saldo
    FROM prd_prdsaldo
    WHERE cd_empresa = 1
      AND cd_saldo IN (1, 7)
      AND cd_produto < 1000000
    ORDER BY cd_produto, cd_saldo, dt_saldo DESC
)
SELECT
    cd_produto,
    COALESCE(MAX(CASE WHEN cd_saldo = 1 THEN qt_saldo END), 0) as saldo_dep1,
    COALESCE(MAX(CASE WHEN cd_saldo = 7 THEN qt_saldo END), 0) as saldo_dep7
FROM saldos_atuais
GROUP BY cd_produto
ORDER BY cd_produto DESC
LIMIT 10
"""
show_query(query)
