"""
Validação: mv_geo3 (materializada) vs geo2 (original)
"""
from db_bridge import execute_query
import time

referencias = ['103010', '201301', '101000', '103006', '341001']

print("=" * 70)
print("VALIDAÇÃO: mv_geo3 vs geo2")
print("=" * 70)

for ref in referencias:
    print(f"\n>>> cd_nivel = {ref}")

    # mv_geo3 (materializada - deve ser instantânea)
    start = time.time()
    query = f"""
    SELECT COUNT(*) as rows, SUM(quantidade) as total
    FROM mv_geo3 WHERE cd_nivel = '{ref}'
    """
    cols, rows_mv = execute_query(query, limit=1)
    t_mv = time.time() - start
    r_mv, tot_mv = rows_mv[0] if rows_mv else (0, 0)

    # geo2 (original - lenta)
    start = time.time()
    query = f"""
    SELECT COUNT(*) as rows, SUM(quantidade) as total
    FROM geo2 WHERE cd_nivel = '{ref}'
    """
    cols, rows_geo2 = execute_query(query, limit=1)
    t_geo2 = time.time() - start
    r_geo2, tot_geo2 = rows_geo2[0] if rows_geo2 else (0, 0)

    # Comparação
    status = "OK" if r_mv == r_geo2 and tot_mv == tot_geo2 else "DIFF"
    print(f"    mv_geo3: {r_mv} rows, total={tot_mv:.0f} ({t_mv:.3f}s)")
    print(f"    geo2:    {r_geo2} rows, total={tot_geo2:.0f} ({t_geo2:.1f}s)")
    print(f"    Status: {status} | Speedup: {t_geo2/t_mv:.0f}x")

print("\n" + "=" * 70)
print("RESUMO")
print("=" * 70)
