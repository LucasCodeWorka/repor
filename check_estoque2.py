from db_bridge import show_query

# Verificar definição da função f_prd_saldo_produto
print("=" * 60)
print("DEFINIÇÃO DA FUNÇÃO f_prd_saldo_produto")
print("=" * 60)
query = """
SELECT pg_get_functiondef(oid)
FROM pg_proc
WHERE proname = 'f_prd_saldo_produto'
LIMIT 1
"""
show_query(query, limit=1)

# Verificar se existe tabela com depósitos
print("\n" + "=" * 60)
print("TABELAS COM 'deposito' NO NOME")
print("=" * 60)
query = """
SELECT table_name
FROM information_schema.tables
WHERE table_name LIKE '%deposito%'
   OR table_name LIKE '%saldo%'
ORDER BY table_name
"""
show_query(query)

# Verificar estrutura da view materializada em detalhes
print("\n" + "=" * 60)
print("DEFINIÇÃO DA VIEW MV_PCP_ESTOQUE_ATUAL")
print("=" * 60)
query = """
SELECT pg_get_viewdef('mv_pcp_estoque_atual'::regclass, true)
"""
show_query(query, limit=1)

# Comparar MV com função
print("\n" + "=" * 60)
print("COMPARAÇÃO: MV_PCP_ESTOQUE_ATUAL vs f_prd_saldo_produto")
print("=" * 60)
query = """
SELECT
    mv.cd_produto,
    mv.estoque_bruto as estoque_mv,
    COALESCE(f_prd_saldo_produto(1, 1, mv.cd_produto, NULL), 0) as saldo_dep1_func,
    COALESCE(f_prd_saldo_produto(1, 7, mv.cd_produto, NULL), 0) as saldo_dep7_func,
    COALESCE(f_prd_saldo_produto(1, 1, mv.cd_produto, NULL), 0) +
    COALESCE(f_prd_saldo_produto(1, 7, mv.cd_produto, NULL), 0) as soma_func
FROM mv_pcp_estoque_atual mv
WHERE mv.estoque_bruto > 0
LIMIT 10
"""
show_query(query)
