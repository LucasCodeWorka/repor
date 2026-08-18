"""
Validar 5 produtos aleatórios: mv_geo3 vs geo2
"""
from db_bridge import execute_query
import time

# Pegar 5 produtos aleatórios da mv_geo3
print("=" * 70)
print("PEGANDO 5 PRODUTOS ALEATÓRIOS")
print("=" * 70)

query = """
SELECT codigoproduto FROM (
    SELECT DISTINCT codigoproduto FROM mv_geo3
) x
ORDER BY RANDOM()
LIMIT 5
"""
cols, rows = execute_query(query, limit=5)
produtos = [r[0] for r in rows]
print(f"Produtos: {produtos}")

# Validar cada produto
print("\n" + "=" * 70)
print("VALIDAÇÃO")
print("=" * 70)

for prod in produtos:
    print(f"\n>>> Produto: {prod}")

    # mv_geo3
    start = time.time()
    query = f"SELECT COUNT(*), SUM(quantidade) FROM mv_geo3 WHERE codigoproduto = {prod}"
    cols, r_mv = execute_query(query, limit=1)
    t_mv = time.time() - start
    cnt_mv, tot_mv = r_mv[0] if r_mv else (0, 0)

    # geo2
    start = time.time()
    query = f"SELECT COUNT(*), SUM(quantidade) FROM geo2 WHERE codigoproduto = {prod}"
    cols, r_g2 = execute_query(query, limit=1)
    t_g2 = time.time() - start
    cnt_g2, tot_g2 = r_g2[0] if r_g2 else (0, 0)

    # Comparar
    diff = abs((tot_mv or 0) - (tot_g2 or 0))
    status = "OK" if cnt_mv == cnt_g2 and diff < 10 else "DIFF"
    print(f"    mv: {cnt_mv} rows, total={tot_mv} ({t_mv:.2f}s)")
    print(f"    g2: {cnt_g2} rows, total={tot_g2} ({t_g2:.1f}s)")
    print(f"    {status}")
