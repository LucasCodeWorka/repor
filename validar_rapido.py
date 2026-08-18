"""
Validação rápida: Compara totais entre geo2 e geo3
"""
from db_bridge import execute_query
import time

referencias = ['201301', '101000', '103006', '341001']

print("=" * 70)
print("VALIDAÇÃO RÁPIDA - COMPARAÇÃO DE TOTAIS")
print("=" * 70)

for ref in referencias:
    print(f"\n>>> cd_nivel = {ref}")

    # GEO3 primeiro (rápido)
    start = time.time()
    query = f"""
    SELECT COUNT(*) as rows, SUM(quantidade) as total
    FROM geo3 WHERE cd_nivel = '{ref}'
    """
    cols, rows3 = execute_query(query, limit=1)
    t3 = time.time() - start
    r3, tot3 = rows3[0] if rows3 else (0, 0)

    # GEO2 (lento)
    start = time.time()
    query = f"""
    SELECT COUNT(*) as rows, SUM(quantidade) as total
    FROM geo2 WHERE cd_nivel = '{ref}'
    """
    cols, rows2 = execute_query(query, limit=1)
    t2 = time.time() - start
    r2, tot2 = rows2[0] if rows2 else (0, 0)

    # Resultado
    status = "OK" if r3 == r2 and tot3 == tot2 else "DIFF"
    print(f"    GEO3: {r3} rows, total={tot3:.0f} ({t3:.1f}s)")
    print(f"    GEO2: {r2} rows, total={tot2:.0f} ({t2:.1f}s)")
    print(f"    Status: {status} | Speedup: {t2/t3:.1f}x")
