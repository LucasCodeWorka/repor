"""
Validação detalhada: Comparar valores por produto específico
"""
from db_bridge import show_query

cd_nivel = '103010'

print("=" * 70)
print(f"COMPARAÇÃO DETALHADA: cd_nivel = {cd_nivel}")
print("=" * 70)

# Comparar totais por dataproduto
print("\n[1] TOTAIS POR DATA - GEO3")
query = f"""
SELECT dataproduto, COUNT(*) as qtd_rows, SUM(quantidade) as total_qtd
FROM geo3
WHERE cd_nivel = '{cd_nivel}'
GROUP BY dataproduto
ORDER BY dataproduto
"""
show_query(query)

print("\n[2] TOTAIS POR DATA - GEO2")
query = f"""
SELECT dataproduto, COUNT(*) as qtd_rows, SUM(quantidade) as total_qtd
FROM geo2
WHERE cd_nivel = '{cd_nivel}'
GROUP BY dataproduto
ORDER BY dataproduto
"""
show_query(query)

# Comparar detalhes de um produto específico
print("\n[3] DETALHE PRODUTO 38438 - GEO3")
query = """
SELECT codigoproduto, seqtamanho, seqsortimento, dataproduto, quantidade, quantidadeprontaentrega
FROM geo3
WHERE codigoproduto = 38438
ORDER BY dataproduto, seqtamanho
"""
show_query(query)

print("\n[4] DETALHE PRODUTO 38438 - GEO2")
query = """
SELECT codigoproduto, seqtamanho, seqsortimento, dataproduto, quantidade, quantidadeprontaentrega
FROM geo2
WHERE codigoproduto = 38438
ORDER BY dataproduto, seqtamanho
"""
show_query(query)

# Verificar se há diferença real nos cálculos
print("\n[5] COMPARAÇÃO DIRETA - MESMA CHAVE")
query = f"""
WITH geo3_data AS (
    SELECT codigoproduto, seqtamanho, seqsortimento, dataproduto, quantidade as qtd_geo3
    FROM geo3
    WHERE cd_nivel = '{cd_nivel}'
),
geo2_data AS (
    SELECT codigoproduto, seqtamanho, seqsortimento, dataproduto, quantidade as qtd_geo2
    FROM geo2
    WHERE cd_nivel = '{cd_nivel}'
)
SELECT
    COALESCE(g3.codigoproduto, g2.codigoproduto) as produto,
    COALESCE(g3.seqtamanho, g2.seqtamanho) as tamanho,
    COALESCE(g3.seqsortimento, g2.seqsortimento) as cor,
    COALESCE(g3.dataproduto, g2.dataproduto) as data,
    g3.qtd_geo3,
    g2.qtd_geo2,
    CASE WHEN g3.qtd_geo3 = g2.qtd_geo2 THEN 'OK' ELSE 'DIFF' END as status
FROM geo3_data g3
FULL OUTER JOIN geo2_data g2
    ON g3.codigoproduto = g2.codigoproduto
    AND g3.seqtamanho = g2.seqtamanho
    AND g3.seqsortimento = g2.seqsortimento
    AND g3.dataproduto = g2.dataproduto
ORDER BY produto, data, tamanho
"""
show_query(query, limit=50)
