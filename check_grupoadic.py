from db_bridge import show_query

print("=" * 60)
print("ESTRUTURA: prd_grupoadic")
print("=" * 60)
query = """
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'prd_grupoadic'
ORDER BY ordinal_position
"""
show_query(query)

print("\n" + "=" * 60)
print("AMOSTRA: prd_grupoadic")
print("=" * 60)
query = "SELECT * FROM prd_grupoadic LIMIT 5"
show_query(query)

print("\n" + "=" * 60)
print("TESTE: Substituir f_dic_prd_nivel por JOIN")
print("=" * 60)
query = """
SELECT
    a.cd_produto,
    f_dic_prd_nivel(a.cd_produto, 'CD') as nivel_funcao,
    g.cd_nivel as nivel_join,
    f_dic_prd_nivel(a.cd_produto, 'DS') as ds_funcao,
    g.ds_nivel as ds_join
FROM vr_prd_prdgrade a
JOIN prd_prdgrade pg ON pg.cd_produto = a.cd_produto
JOIN prd_grupoadic g ON g.cd_seqgrupo = pg.cd_seqgrupo
WHERE a.cd_produto IN (38438, 35254, 36751)
"""
show_query(query)
