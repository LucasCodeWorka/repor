"""
Validar 5 produtos aleatórios: mv_geo3 vs geo2
"""
from db_bridge import execute_query, show_query
import time

# Pegar 5 produtos aleatórios da mv_geo3
print("=" * 70)
print("PEGANDO 5 PRODUTOS ALEATÓRIOS")
print("=" * 70)

query = """
SELECT DISTINCT codigoproduto
FROM mv_geo3
ORDER BY RANDOM()
LIMIT 5
"""
cols, rows = execute_query(query, limit=5)
produtos = [r[0] for r in rows]
print(f"Produtos selecionados: {produtos}")

# Validar cada produto
print("\n" + "=" * 70)
print("VALIDAÇÃO POR PRODUTO")
print("=" * 70)

for prod in produtos:
    print(f"\n>>> Produto: {prod}")

    # mv_geo3
    start = time.time()
    query = f"""
    SELECT COUNT(*) as rows, SUM(quantidade) as total
    FROM mv_geo3 WHERE codigoproduto = {prod}
    """
    cols, rows_mv = execute_query(query, limit=1)
    t_mv = time.time() - start
    r_mv, tot_mv = rows_mv[0] if rows_mv else (0, 0)

    # geo2
    start = time.time()
    query = f"""
    SELECT COUNT(*) as rows, SUM(quantidade) as total
    FROM geo2 WHERE codigoproduto = {prod}
    """
    cols, rows_g2 = execute_query(query, limit=1)
    t_g2 = time.time() - start
    r_g2, tot_g2 = rows_g2[0] if rows_g2 else (0, 0)

    # Comparar
    status = "OK" if r_mv == r_g2 and abs((tot_mv or 0) - (tot_g2 or 0)) < 10 else "DIFF"
    print(f"    mv_geo3: {r_mv} rows, total={tot_mv} ({t_mv:.3f}s)")
    print(f"    geo2:    {r_g2} rows, total={tot_g2} ({t_g2:.1f}s)")
    print(f"    Status: {status}")
