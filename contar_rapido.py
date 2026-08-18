"""
Contagem rápida - só na mv_geo3 (instantânea)
"""
from db_bridge import show_query
import time

print("=" * 70)
print("CONTAGEM RÁPIDA NA MV_GEO3")
print("=" * 70)

start = time.time()

query = """
SELECT
    COUNT(*) as total_rows,
    COUNT(DISTINCT codigoproduto) as produtos_distintos,
    COUNT(DISTINCT cd_nivel) as referencias_distintas
FROM mv_geo3
"""
show_query(query)

print(f"\nTempo: {time.time()-start:.2f}s")

# Comparar com geo3 (view normal, demora um pouco)
print("\n" + "=" * 70)
print("CONTAGEM NA GEO3 (view normal)")
print("=" * 70)

start = time.time()
query = """
SELECT
    COUNT(*) as total_rows,
    COUNT(DISTINCT codigoproduto) as produtos_distintos,
    COUNT(DISTINCT cd_nivel) as referencias_distintas
FROM geo3
"""
show_query(query)
print(f"\nTempo: {time.time()-start:.2f}s")
