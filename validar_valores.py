"""
Validação: Comparar valores entre geo2 (original) e geo3 (otimizada)
"""
from db_bridge import show_query, execute_query
import time

# Referências para testar
referencias = ['103010', '201301', '101000', '103006', '341001']

def comparar_referencia(cd_nivel):
    print(f"\n{'='*70}")
    print(f"VALIDANDO: cd_nivel = {cd_nivel}")
    print('='*70)

    # Query geo3 (otimizada - rápida)
    print(f"\n[GEO3 - Otimizada]")
    start = time.time()
    query_geo3 = f"""
    SELECT
        cd_nivel,
        codigoproduto,
        seqtamanho,
        seqsortimento,
        dataproduto,
        quantidade,
        quantidadeprontaentrega
    FROM geo3
    WHERE cd_nivel = '{cd_nivel}'
    ORDER BY dataproduto, seqtamanho
    """
    columns, rows = execute_query(query_geo3, limit=50)
    t_geo3 = time.time() - start
    print(f"Tempo: {t_geo3:.2f}s | Rows: {len(rows)}")

    if rows:
        # Mostrar primeiros resultados
        for row in rows[:6]:
            print(f"  prod={row[1]} tam={row[2]} cor={row[3]} data={row[4]} qtd={row[5]} pronta={row[6]}")
        if len(rows) > 6:
            print(f"  ... mais {len(rows)-6} rows")

    # Query geo2 (original - lenta)
    print(f"\n[GEO2 - Original]")
    start = time.time()
    query_geo2 = f"""
    SELECT
        cd_nivel,
        codigoproduto,
        seqtamanho,
        seqsortimento,
        dataproduto,
        quantidade,
        quantidadeprontaentrega
    FROM geo2
    WHERE cd_nivel = '{cd_nivel}'
    ORDER BY dataproduto, seqtamanho
    """
    columns2, rows2 = execute_query(query_geo2, limit=50)
    t_geo2 = time.time() - start
    print(f"Tempo: {t_geo2:.2f}s | Rows: {len(rows2)}")

    if rows2:
        for row in rows2[:6]:
            print(f"  prod={row[1]} tam={row[2]} cor={row[3]} data={row[4]} qtd={row[5]} pronta={row[6]}")
        if len(rows2) > 6:
            print(f"  ... mais {len(rows2)-6} rows")

    # Comparação
    print(f"\n[COMPARAÇÃO]")
    print(f"GEO3: {len(rows)} rows em {t_geo3:.2f}s")
    print(f"GEO2: {len(rows2)} rows em {t_geo2:.2f}s")
    print(f"Speedup: {t_geo2/t_geo3:.1f}x")

    # Verificar diferenças
    if len(rows) == len(rows2):
        diffs = 0
        for i, (r3, r2) in enumerate(zip(rows, rows2)):
            if r3[5] != r2[5]:  # quantidade
                diffs += 1
                print(f"  DIFF linha {i}: GEO3 qtd={r3[5]} vs GEO2 qtd={r2[5]}")
        if diffs == 0:
            print("  OK - Valores iguais!")
        else:
            print(f"  ATENÇÃO: {diffs} diferenças encontradas")
    else:
        print(f"  ATENÇÃO: Número de rows diferente!")

    return len(rows), len(rows2), t_geo3, t_geo2


# Testar primeira referência
print("Testando primeira referência: 103010")
comparar_referencia('103010')
