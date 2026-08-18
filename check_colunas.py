from db_bridge import show_query

print("=" * 60)
print("COLUNAS DA GEO2 (original)")
print("=" * 60)
query = """
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'geo2'
ORDER BY ordinal_position
"""
show_query(query)

print("\n" + "=" * 60)
print("COLUNAS DA GEO3 (otimizada)")
print("=" * 60)
query = """
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'geo3'
ORDER BY ordinal_position
"""
show_query(query)
