from db_bridge import show_query

print("=" * 60)
print("ESTRUTURA: vr_prd_prdgrade")
print("=" * 60)
query = """
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'vr_prd_prdgrade'
ORDER BY ordinal_position
"""
show_query(query)

print("\n" + "=" * 60)
print("AMOSTRA: vr_prd_prdgrade")
print("=" * 60)
query = "SELECT * FROM vr_prd_prdgrade LIMIT 3"
show_query(query)
