"""
Teste: Quanto tempo leva para materializar a view geo3?
"""
from db_bridge import execute_query, show_query
import time

print("=" * 70)
print("ESTIMATIVA DE TEMPO PARA MATERIALIZAÇÃO")
print("=" * 70)

# 1. Contar total de registros na geo3
print("\n[1] Contando registros totais na geo3...")
start = time.time()
query = "SELECT COUNT(*) FROM geo3"
cols, rows = execute_query(query, limit=1)
t1 = time.time() - start
total = rows[0][0] if rows else 0
print(f"    Total de registros: {total:,}")
print(f"    Tempo para contar: {t1:.1f}s")

# 2. Estimar tempo de materialização
print("\n[2] Estimativa de materialização:")
print(f"    - Se contar levou {t1:.1f}s, materializar (SELECT *) levaria ~{t1*1.5:.0f}s a {t1*2:.0f}s")
print(f"    - Isso equivale a {t1*1.5/60:.1f} a {t1*2/60:.1f} minutos")

# 3. Verificar se as vr_* são views
print("\n[3] Verificando se as vr_* são views ou tabelas...")
query = """
SELECT table_name, table_type
FROM information_schema.tables
WHERE table_name IN ('vr_ped_pedidoi', 'vr_pcp_opi', 'vr_pcp_opc',
                     'vr_pcp_lotepl2', 'vr_prd_prdgrade', 'vr_prd_prdinfo')
ORDER BY table_name
"""
show_query(query)

# 4. Sugestão de VIEW MATERIALIZADA
print("\n[4] PROPOSTA: VIEW MATERIALIZADA")
print("-" * 70)
print("""
-- Criar view materializada (roda uma vez, depois é instantânea)
CREATE MATERIALIZED VIEW mv_geovendas_estoque AS
<conteúdo da view_otimizada_v2.sql>
WITH DATA;

-- Criar índice na view materializada para buscas rápidas
CREATE INDEX idx_mv_geovendas_cd_nivel ON mv_geovendas_estoque (cd_nivel);
CREATE INDEX idx_mv_geovendas_produto ON mv_geovendas_estoque (codigoproduto);
CREATE INDEX idx_mv_geovendas_data ON mv_geovendas_estoque (dataproduto);

-- Para atualizar (rodar periodicamente via cron/scheduler):
REFRESH MATERIALIZED VIEW CONCURRENTLY mv_geovendas_estoque;

Benefícios:
- Consultas instantâneas (< 1 segundo)
- Pode atualizar em background sem travar leituras (CONCURRENTLY)
- Ideal se dados não precisam ser 100% tempo real
""")
