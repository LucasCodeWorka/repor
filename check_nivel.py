from db_bridge import show_query

print("=" * 60)
print("VERIFICANDO FUNÇÃO f_dic_prd_nivel")
print("=" * 60)

# Ver definição da função
query = """
SELECT pg_get_functiondef(oid)
FROM pg_proc
WHERE proname = 'f_dic_prd_nivel'
LIMIT 1
"""
show_query(query, limit=1)

# Verificar se existe tabela com níveis
print("\n" + "=" * 60)
print("TABELAS COM 'nivel' NO NOME")
print("=" * 60)
query = """
SELECT table_name FROM information_schema.tables
WHERE table_name LIKE '%nivel%'
ORDER BY table_name
"""
show_query(query)

# Verificar prd_produto
print("\n" + "=" * 60)
print("ESTRUTURA: prd_produto")
print("=" * 60)
query = """
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'prd_produto'
ORDER BY ordinal_position
LIMIT 20
"""
show_query(query)
