"""
Script para testar a view otimizada vs a original
"""
from db_bridge import execute_query, show_query
import time

def test_query(name, query, limit=10):
    """Executa uma query e mede o tempo"""
    print(f"\n{'='*60}")
    print(f"TESTANDO: {name}")
    print('='*60)

    start = time.time()
    try:
        columns, rows = execute_query(query, limit=limit)
        elapsed = time.time() - start

        if columns:
            print(f"Colunas: {len(columns)}")
            print(f"Rows retornadas: {len(rows)}")
            print(f"Tempo: {elapsed:.2f}s")
            return True, elapsed, len(rows)
        else:
            print(f"Resultado: {rows}")
            return False, elapsed, 0
    except Exception as e:
        elapsed = time.time() - start
        print(f"ERRO: {e}")
        return False, elapsed, 0


# Ler a view otimizada do arquivo
with open('view_otimizada.sql', 'r', encoding='utf-8') as f:
    view_otimizada = f.read()

# View original (simplificada para teste - apenas conta registros)
print("\n" + "="*60)
print("TESTE 1: Verificar estrutura das CTEs")
print("="*60)

# Testa CTE de classificações
test_cte_clas = """
SELECT COUNT(*) as total,
       COUNT(DISTINCT cd_produto) as produtos
FROM (
    SELECT
        pc.cd_produto,
        MAX(CASE WHEN pc.cd_tipoclas = 20 THEN pc.cd_classificacao END) AS clas_20_cd,
        MAX(CASE WHEN pc.cd_tipoclas = 21 THEN pc.cd_classificacao END) AS clas_21_cd,
        MAX(CASE WHEN pc.cd_tipoclas = 27 THEN pc.cd_classificacao END) AS clas_27_cd,
        MAX(CASE WHEN pc.cd_tipoclas = 124 THEN pc.cd_classificacao END) AS clas_124_cd
    FROM prd_produtoclas pc
    WHERE pc.cd_tipoclas IN (20, 21, 27, 124)
    GROUP BY pc.cd_produto
) x
"""
print("\nCTE Classificações:")
show_query(test_cte_clas)

# Testa CTE de pedidos pendentes
test_cte_ped = """
SELECT COUNT(DISTINCT cd_produto) as produtos_com_pedido,
       SUM(qt_pendente) as total_pendente
FROM (
    SELECT
        cd_produto,
        COALESCE(SUM(qt_pendente), 0) AS qt_pendente
    FROM vr_ped_pedidoi
    WHERE cd_operacao <> 44
      AND cd_empresa = 1
      AND tp_situacao <> 6
    GROUP BY cd_produto
) x
"""
print("\nCTE Pedidos Pendentes:")
show_query(test_cte_ped)

# Testa CTE de OPs
test_cte_op = """
SELECT COUNT(DISTINCT cd_produto) as produtos_em_op,
       SUM(qt_pendente) as total_op
FROM (
    SELECT
        aa.cd_produto,
        SUM(COALESCE(aa.qt_real, 0) - COALESCE(aa.qt_finalizada, 0)) AS qt_pendente
    FROM vr_pcp_opi aa
    JOIN vr_pcp_opc bb ON aa.cd_empresa = bb.cd_empresa
                       AND aa.nr_ciclo = bb.nr_ciclo
                       AND aa.nr_op = bb.nr_op
    WHERE aa.cd_empresa = 1
      AND COALESCE(bb.cd_categoria, 0) <> 15
      AND aa.tp_situacao IN (5, 10, 15, 20)
    GROUP BY aa.cd_produto
) x
"""
print("\nCTE OPs em Produção:")
show_query(test_cte_op)

# Testa lotes
test_lotes = """
SELECT
    p.cd_auxiliar,
    COUNT(DISTINCT b.cd_produto) as produtos,
    SUM(GREATEST(b.qt_lote - COALESCE(b.qt_gerouop, 0), 0)) as qt_total
FROM vr_pcp_lotepl2 b
LEFT JOIN pcp_lotepv p ON b.nr_lote = p.nr_lote
WHERE p.cd_auxiliar IN ('MA', 'MG', 'PX', 'UL')
GROUP BY p.cd_auxiliar
ORDER BY p.cd_auxiliar
"""
print("\nLotes por Auxiliar:")
show_query(test_lotes)

print("\n" + "="*60)
print("TESTE 2: Comparar contagens entre view original e otimizada")
print("="*60)

# Conta produtos na view original (apenas primeiro UNION para teste rápido)
test_original_count = """
SELECT COUNT(*) as total
FROM vr_prd_prdgrade a
JOIN vr_prd_prdinfo b ON b.cd_produto = a.cd_produto AND b.cd_empresa = 1
WHERE b.in_inativo = 'F'
  AND a.cd_cor <> 'LF        '
  AND (f_dic_prd_classificacao(a.cd_produto, 'CD', 20) IN ('0001', '0002', '0003', '0020', '0009'))
  AND (f_dic_prd_classificacao(a.cd_produto, 'CD', 124) IN ('001', '002', '007', '004', '005')
       OR f_dic_prd_classificacao(a.cd_produto, 'CD', 124) IS NULL)
  AND (a.cd_produto < 1000000 OR a.cd_produto IN (5001609, 5001610, 5001319, 5001611))
"""

test_otimizada_count = """
WITH classificacoes AS (
    SELECT
        pc.cd_produto,
        MAX(CASE WHEN pc.cd_tipoclas = 20 THEN pc.cd_classificacao END) AS clas_20_cd,
        MAX(CASE WHEN pc.cd_tipoclas = 124 THEN pc.cd_classificacao END) AS clas_124_cd
    FROM prd_produtoclas pc
    WHERE pc.cd_tipoclas IN (20, 124)
    GROUP BY pc.cd_produto
)
SELECT COUNT(*) as total
FROM vr_prd_prdgrade a
JOIN vr_prd_prdinfo b ON b.cd_produto = a.cd_produto AND b.cd_empresa = 1
LEFT JOIN classificacoes c ON c.cd_produto = a.cd_produto
WHERE b.in_inativo = 'F'
  AND a.cd_cor <> 'LF        '
  AND c.clas_20_cd IN ('0001', '0002', '0003', '0020', '0009')
  AND (c.clas_124_cd IN ('001', '002', '007', '004', '005') OR c.clas_124_cd IS NULL)
  AND (a.cd_produto < 1000000 OR a.cd_produto IN (5001609, 5001610, 5001319, 5001611))
"""

print("\nContagem usando função f_dic_prd_classificacao (original):")
result = test_query("View Original (contagem)", test_original_count, 1)

print("\nContagem usando JOIN com prd_produtoclas (otimizada):")
result = test_query("View Otimizada (contagem)", test_otimizada_count, 1)

print("\n" + "="*60)
print("TESTES CONCLUÍDOS")
print("="*60)
