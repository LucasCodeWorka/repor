"""
Verificar se todos os produtos da geo2 estão na mv_geo3
"""
from db_bridge import show_query

print("=" * 70)
print("VERIFICAÇÃO DE PRODUTOS: geo2 vs mv_geo3")
print("=" * 70)

# 1. Contagem total
print("\n[1] CONTAGEM TOTAL DE REGISTROS")
print("-" * 70)
query = """
SELECT 'geo2' as view, COUNT(*) as total_rows, COUNT(DISTINCT codigoproduto) as produtos_distintos
FROM geo2
UNION ALL
SELECT 'mv_geo3' as view, COUNT(*) as total_rows, COUNT(DISTINCT codigoproduto) as produtos_distintos
FROM mv_geo3
"""
show_query(query)

# 2. Contagem por cd_nivel (referência)
print("\n[2] CONTAGEM DE REFERÊNCIAS (cd_nivel)")
print("-" * 70)
query = """
SELECT 'geo2' as view, COUNT(DISTINCT cd_nivel) as referencias
FROM geo2
UNION ALL
SELECT 'mv_geo3' as view, COUNT(DISTINCT cd_nivel) as referencias
FROM mv_geo3
"""
show_query(query)

# 3. Produtos que estão na geo2 mas NÃO estão na mv_geo3
print("\n[3] PRODUTOS NA GEO2 QUE NÃO ESTÃO NA MV_GEO3")
print("-" * 70)
query = """
SELECT DISTINCT codigoproduto, cd_nivel
FROM geo2
WHERE codigoproduto NOT IN (SELECT DISTINCT codigoproduto FROM mv_geo3)
ORDER BY codigoproduto
LIMIT 20
"""
show_query(query)

# 4. Produtos que estão na mv_geo3 mas NÃO estão na geo2
print("\n[4] PRODUTOS NA MV_GEO3 QUE NÃO ESTÃO NA GEO2")
print("-" * 70)
query = """
SELECT DISTINCT codigoproduto, cd_nivel
FROM mv_geo3
WHERE codigoproduto NOT IN (SELECT DISTINCT codigoproduto FROM geo2)
ORDER BY codigoproduto
LIMIT 20
"""
show_query(query)

# 5. Resumo
print("\n[5] RESUMO DA COMPARAÇÃO")
print("-" * 70)
query = """
WITH geo2_prods AS (SELECT DISTINCT codigoproduto FROM geo2),
     mv_prods AS (SELECT DISTINCT codigoproduto FROM mv_geo3)
SELECT
    (SELECT COUNT(*) FROM geo2_prods) as produtos_geo2,
    (SELECT COUNT(*) FROM mv_prods) as produtos_mv_geo3,
    (SELECT COUNT(*) FROM geo2_prods WHERE codigoproduto NOT IN (SELECT codigoproduto FROM mv_prods)) as faltando_na_mv,
    (SELECT COUNT(*) FROM mv_prods WHERE codigoproduto NOT IN (SELECT codigoproduto FROM geo2_prods)) as extras_na_mv
"""
show_query(query)
