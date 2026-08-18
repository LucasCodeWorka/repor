from db_bridge import show_query

# Verificar os tipos de classificação usados na view (20, 21, 27, 124)
print("=" * 60)
print("TIPOS DE CLASSIFICAÇÃO USADOS NA VIEW")
print("=" * 60)

query = """
    SELECT DISTINCT pc.cd_tipoclas,
           (SELECT ds_classificacao FROM prd_classificacao
            WHERE cd_tipoclas = pc.cd_tipoclas LIMIT 1) as exemplo_desc,
           COUNT(DISTINCT pc.cd_produto) as qtd_produtos
    FROM prd_produtoclas pc
    WHERE pc.cd_tipoclas IN (20, 21, 27, 124)
    GROUP BY pc.cd_tipoclas
    ORDER BY pc.cd_tipoclas
"""
show_query(query)

print("\n" + "=" * 60)
print("CLASSIFICAÇÕES DO TIPO 20 (familia/categoria)")
print("=" * 60)
query = """
    SELECT cd_classificacao, ds_classificacao
    FROM prd_classificacao
    WHERE cd_tipoclas = 20
    ORDER BY cd_classificacao
    LIMIT 20
"""
show_query(query)

print("\n" + "=" * 60)
print("CLASSIFICAÇÕES DO TIPO 21 (coleção)")
print("=" * 60)
query = """
    SELECT cd_classificacao, ds_classificacao
    FROM prd_classificacao
    WHERE cd_tipoclas = 21
    ORDER BY cd_classificacao
    LIMIT 20
"""
show_query(query)

print("\n" + "=" * 60)
print("CLASSIFICAÇÕES DO TIPO 27")
print("=" * 60)
query = """
    SELECT cd_classificacao, ds_classificacao
    FROM prd_classificacao
    WHERE cd_tipoclas = 27
    ORDER BY cd_classificacao
    LIMIT 20
"""
show_query(query)

print("\n" + "=" * 60)
print("CLASSIFICAÇÕES DO TIPO 124")
print("=" * 60)
query = """
    SELECT cd_classificacao, ds_classificacao
    FROM prd_classificacao
    WHERE cd_tipoclas = 124
    ORDER BY cd_classificacao
    LIMIT 20
"""
show_query(query)
