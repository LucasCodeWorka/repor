"""
Análise de índices para otimização da view geo3
"""
from db_bridge import show_query

print("=" * 70)
print("ANÁLISE DE ÍNDICES PARA OTIMIZAÇÃO")
print("=" * 70)

# 1. Verificar índices existentes nas tabelas principais
tabelas = [
    'prd_produtoclas',
    'prd_prdsaldo',
    'vr_ped_pedidoi',
    'vr_pcp_opi',
    'vr_pcp_opc',
    'vr_pcp_lotepl2',
    'pcp_lotepv',
    'vr_prd_prdgrade',
    'vr_prd_prdinfo'
]

print("\n[1] ÍNDICES EXISTENTES NAS TABELAS PRINCIPAIS")
print("-" * 70)

for tabela in tabelas:
    query = f"""
    SELECT indexname, indexdef
    FROM pg_indexes
    WHERE tablename = '{tabela}'
    ORDER BY indexname
    """
    print(f"\n>>> {tabela}")
    show_query(query, limit=20)

# 2. Analisar plano de execução de uma CTE crítica
print("\n" + "=" * 70)
print("[2] ESTATÍSTICAS DAS TABELAS")
print("-" * 70)

query = """
SELECT
    relname as tabela,
    n_live_tup as linhas_estimadas,
    seq_scan as scans_sequenciais,
    idx_scan as scans_indice
FROM pg_stat_user_tables
WHERE relname IN ('prd_produtoclas', 'prd_prdsaldo', 'vr_ped_pedidoi',
                  'vr_pcp_opi', 'vr_pcp_opc', 'vr_pcp_lotepl2', 'pcp_lotepv')
ORDER BY n_live_tup DESC
"""
show_query(query)

# 3. Sugestões de índices
print("\n" + "=" * 70)
print("[3] ÍNDICES SUGERIDOS PARA CRIAR")
print("-" * 70)
print("""
-- Índices para acelerar as CTEs da view geo3:

-- 1. prd_produtoclas - usado na CTE classificacoes (PIVOT)
CREATE INDEX IF NOT EXISTS idx_produtoclas_tipoclas_produto
ON prd_produtoclas (cd_tipoclas, cd_produto);

-- 2. prd_prdsaldo - usado na CTE saldos_atuais (DISTINCT ON)
CREATE INDEX IF NOT EXISTS idx_prdsaldo_empresa_saldo_produto_data
ON prd_prdsaldo (cd_empresa, cd_saldo, cd_produto, dt_saldo DESC);

-- 3. vr_ped_pedidoi - usado na CTE pedidos_pendentes
CREATE INDEX IF NOT EXISTS idx_pedidoi_empresa_operacao_situacao
ON vr_ped_pedidoi (cd_empresa, cd_operacao, tp_situacao)
WHERE cd_operacao <> 44 AND tp_situacao <> 6;

-- 4. vr_pcp_opi - usado na CTE ops_producao
CREATE INDEX IF NOT EXISTS idx_opi_empresa_situacao
ON vr_pcp_opi (cd_empresa, tp_situacao)
WHERE tp_situacao IN (5, 10, 15, 20);

-- 5. vr_pcp_lotepl2 + pcp_lotepv - usado nas CTEs de lotes
CREATE INDEX IF NOT EXISTS idx_lotepl2_nr_lote_produto
ON vr_pcp_lotepl2 (nr_lote, cd_produto);

CREATE INDEX IF NOT EXISTS idx_lotepv_auxiliar_lote
ON pcp_lotepv (cd_auxiliar, nr_lote);
""")
