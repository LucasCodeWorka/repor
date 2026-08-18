"""
Detalhe da diferença no cd_nivel = 341001
"""
from db_bridge import show_query

ref = '341001'

print("=" * 70)
print(f"ANÁLISE DETALHADA: cd_nivel = {ref}")
print("=" * 70)

# Comparar por produto e data
print("\n[1] COMPARAÇÃO DIRETA POR CHAVE")
print("-" * 70)
query = f"""
WITH mv AS (
    SELECT codigoproduto, seqtamanho, seqsortimento, dataproduto, quantidade as qtd_mv
    FROM mv_geo3 WHERE cd_nivel = '{ref}'
),
g2 AS (
    SELECT codigoproduto, seqtamanho, seqsortimento, dataproduto, quantidade as qtd_geo2
    FROM geo2 WHERE cd_nivel = '{ref}'
)
SELECT
    COALESCE(mv.codigoproduto, g2.codigoproduto) as produto,
    COALESCE(mv.seqtamanho, g2.seqtamanho) as tam,
    COALESCE(mv.seqsortimento, g2.seqsortimento) as cor,
    COALESCE(mv.dataproduto, g2.dataproduto) as data,
    mv.qtd_mv,
    g2.qtd_geo2,
    COALESCE(mv.qtd_mv, 0) - COALESCE(g2.qtd_geo2, 0) as diferenca
FROM mv
FULL OUTER JOIN g2
    ON mv.codigoproduto = g2.codigoproduto
    AND mv.seqtamanho = g2.seqtamanho
    AND mv.seqsortimento = g2.seqsortimento
    AND mv.dataproduto = g2.dataproduto
WHERE COALESCE(mv.qtd_mv, 0) <> COALESCE(g2.qtd_geo2, 0)
ORDER BY produto, data
"""
show_query(query, limit=50)

# Total por data
print("\n[2] TOTAIS POR DATA")
print("-" * 70)
query = f"""
SELECT 'mv_geo3' as fonte, dataproduto, COUNT(*) as rows, SUM(quantidade) as total
FROM mv_geo3 WHERE cd_nivel = '{ref}'
GROUP BY dataproduto
UNION ALL
SELECT 'geo2' as fonte, dataproduto, COUNT(*) as rows, SUM(quantidade) as total
FROM geo2 WHERE cd_nivel = '{ref}'
GROUP BY dataproduto
ORDER BY dataproduto, fonte
"""
show_query(query)
