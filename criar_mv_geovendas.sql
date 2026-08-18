-- ============================================================
-- VIEW MATERIALIZADA DE ESTOQUE GEOVENDAS
-- ============================================================
-- Tempo de criação: ~45-60 segundos
-- Tempo de consulta: < 1 segundo
-- ============================================================

-- 1. Dropar se existir (opcional - comentado por segurança)
-- DROP MATERIALIZED VIEW IF EXISTS mv_geovendas_estoque;

-- 2. Criar a View Materializada
CREATE MATERIALIZED VIEW mv_geovendas_estoque AS
WITH
-- =============================================================
-- CTE 1: Classificações por produto
-- =============================================================
classificacoes AS (
    SELECT
        pc.cd_produto,
        MAX(CASE WHEN pc.cd_tipoclas = 20 THEN TRIM(pc.cd_classificacao) END) AS clas_20,
        MAX(CASE WHEN pc.cd_tipoclas = 21 THEN TRIM(pc.cd_classificacao) END) AS clas_21,
        MAX(CASE WHEN pc.cd_tipoclas = 27 THEN TRIM(pc.cd_classificacao) END) AS clas_27,
        MAX(CASE WHEN pc.cd_tipoclas = 124 THEN TRIM(pc.cd_classificacao) END) AS clas_124
    FROM prd_produtoclas pc
    WHERE pc.cd_tipoclas IN (20, 21, 27, 124)
    GROUP BY pc.cd_produto
),

-- =============================================================
-- CTE 2: Descrição da coleção
-- =============================================================
colecao_desc AS (
    SELECT TRIM(cd_classificacao) AS cd_classificacao, ds_classificacao
    FROM prd_classificacao
    WHERE cd_tipoclas = 21
),

-- =============================================================
-- CTE 3: Saldos atuais por produto
-- =============================================================
saldos_atuais AS (
    SELECT DISTINCT ON (cd_produto, cd_saldo)
        cd_produto,
        cd_saldo,
        qt_saldo
    FROM prd_prdsaldo
    WHERE cd_empresa = 1
      AND cd_saldo IN (1, 7)
    ORDER BY cd_produto, cd_saldo, dt_saldo DESC
),

saldos_pivot AS (
    SELECT
        cd_produto,
        COALESCE(MAX(CASE WHEN cd_saldo = 1 THEN qt_saldo END), 0) AS saldo_dep1,
        COALESCE(MAX(CASE WHEN cd_saldo = 7 THEN qt_saldo END), 0) AS saldo_dep7
    FROM saldos_atuais
    GROUP BY cd_produto
),

-- =============================================================
-- CTE 4: Pedidos pendentes
-- =============================================================
pedidos_pendentes AS (
    SELECT
        cd_produto,
        COALESCE(SUM(qt_pendente), 0) AS qt_pendente
    FROM vr_ped_pedidoi
    WHERE cd_operacao <> 44
      AND cd_empresa = 1
      AND tp_situacao <> 6
    GROUP BY cd_produto
),

-- =============================================================
-- CTE 5: OPs em produção
-- =============================================================
ops_producao AS (
    SELECT
        aa.cd_produto,
        SUM(COALESCE(aa.qt_real, 0) - COALESCE(aa.qt_finalizada, 0)) AS qt_op
    FROM vr_pcp_opi aa
    JOIN vr_pcp_opc bb ON aa.cd_empresa = bb.cd_empresa
                       AND aa.nr_ciclo = bb.nr_ciclo
                       AND aa.nr_op = bb.nr_op
    WHERE aa.cd_empresa = 1
      AND COALESCE(bb.cd_categoria, 0) <> 15
      AND aa.tp_situacao IN (5, 10, 15, 20)
    GROUP BY aa.cd_produto
),

-- =============================================================
-- CTE 6: OPs pronta entrega
-- =============================================================
ops_pronta_entrega AS (
    SELECT
        aa.cd_produto,
        SUM(COALESCE(aa.qt_real, 0) - COALESCE(aa.qt_finalizada, 0)) AS qt_op_pronta
    FROM vr_pcp_opi aa
    JOIN vr_pcp_opc bb ON aa.cd_empresa = bb.cd_empresa
                       AND aa.nr_ciclo = bb.nr_ciclo
                       AND aa.nr_op = bb.nr_op
    JOIN prd_produtoclas cc ON aa.cd_produto = cc.cd_produto
                            AND cc.cd_tipoclas = 802
                            AND TRIM(cc.cd_classificacao) = '2'
    WHERE aa.cd_empresa = 1
      AND bb.dt_inclusao <= '2026-05-19 00:00:00'::timestamp
      AND COALESCE(bb.cd_categoria, 0) <> 15
      AND aa.tp_situacao IN (5, 10, 15, 20)
    GROUP BY aa.cd_produto
),

-- =============================================================
-- CTE 7: Lotes MA/MG
-- =============================================================
lotes_ma_mg AS (
    SELECT
        b.cd_produto,
        COALESCE(SUM(GREATEST(b.qt_lote - COALESCE(b.qt_gerouop, 0), 0)), 0) AS qt_lote
    FROM vr_pcp_lotepl2 b
    JOIN pcp_lotepv p ON b.nr_lote = p.nr_lote
    WHERE p.cd_auxiliar IN ('MA', 'MG')
    GROUP BY b.cd_produto
),

-- =============================================================
-- CTE 8: Lotes PX
-- =============================================================
lotes_px AS (
    SELECT
        b.cd_produto,
        COALESCE(SUM(GREATEST(b.qt_lote - COALESCE(b.qt_gerouop, 0), 0)), 0) AS qt_lote
    FROM vr_pcp_lotepl2 b
    JOIN pcp_lotepv p ON b.nr_lote = p.nr_lote
    WHERE p.cd_auxiliar = 'PX'
    GROUP BY b.cd_produto
),

-- =============================================================
-- CTE 9: Lotes UL
-- =============================================================
lotes_ul AS (
    SELECT
        b.cd_produto,
        COALESCE(SUM(GREATEST(b.qt_lote - COALESCE(b.qt_gerouop, 0), 0)), 0) AS qt_lote
    FROM vr_pcp_lotepl2 b
    JOIN pcp_lotepv p ON b.nr_lote = p.nr_lote
    WHERE p.cd_auxiliar = 'UL'
    GROUP BY b.cd_produto
),

-- =============================================================
-- CTE 10: Base de produtos
-- =============================================================
produtos_base AS (
    SELECT
        a.cd_produto,
        a.cd_tamanho,
        a.cd_cor,
        a.ds_tamanho,
        a.ds_cor,
        c.clas_20,
        c.clas_21,
        c.clas_27,
        c.clas_124,
        cd.ds_classificacao AS ds_colecao,
        COALESCE(s.saldo_dep1, 0) AS saldo_dep1,
        COALESCE(s.saldo_dep7, 0) AS saldo_dep7,
        COALESCE(pp.qt_pendente, 0) AS qt_pendente,
        CASE
            WHEN c.clas_124 IN ('001', '002', '004', '005') OR c.clas_124 IS NULL
            THEN COALESCE(op.qt_op, 0)
            ELSE 0
        END AS qt_op,
        CASE
            WHEN c.clas_124 IN ('001', '002', '004', '005') OR c.clas_124 IS NULL
            THEN COALESCE(opp.qt_op_pronta, 0)
            ELSE 0
        END AS qt_op_pronta,
        COALESCE(lmg.qt_lote, 0) AS qt_lote_ma_mg,
        COALESCE(lpx.qt_lote, 0) AS qt_lote_px,
        COALESCE(lul.qt_lote, 0) AS qt_lote_ul
    FROM vr_prd_prdgrade a
    JOIN vr_prd_prdinfo b ON b.cd_produto = a.cd_produto
                          AND b.cd_empresa = 1
                          AND b.in_inativo = 'F'
    LEFT JOIN classificacoes c ON c.cd_produto = a.cd_produto
    LEFT JOIN colecao_desc cd ON cd.cd_classificacao = c.clas_21
    LEFT JOIN saldos_pivot s ON s.cd_produto = a.cd_produto
    LEFT JOIN pedidos_pendentes pp ON pp.cd_produto = a.cd_produto
    LEFT JOIN ops_producao op ON op.cd_produto = a.cd_produto
    LEFT JOIN ops_pronta_entrega opp ON opp.cd_produto = a.cd_produto
    LEFT JOIN lotes_ma_mg lmg ON lmg.cd_produto = a.cd_produto
    LEFT JOIN lotes_px lpx ON lpx.cd_produto = a.cd_produto
    LEFT JOIN lotes_ul lul ON lul.cd_produto = a.cd_produto
    WHERE a.cd_cor <> 'LF        '
      AND c.clas_20 IN ('0001', '0002', '0003', '0020', '0009')
      AND (c.clas_124 IN ('001', '002', '007', '004', '005') OR c.clas_124 IS NULL)
      AND (a.cd_produto < 1000000 OR a.cd_produto IN (5001609, 5001610, 5001319, 5001611))
),

-- =============================================================
-- CTE 11: Cálculos de estoque
-- =============================================================
produtos_calc AS (
    SELECT
        p.*,
        (p.saldo_dep1 - p.qt_pendente + p.saldo_dep7) AS estoque_base,
        (p.saldo_dep1 - p.qt_pendente + p.saldo_dep7 + p.qt_op) AS estoque_30d,
        (p.saldo_dep1 - p.qt_pendente + p.saldo_dep7 + p.qt_op + p.qt_lote_ma_mg + p.qt_lote_px) AS estoque_60d,
        (p.saldo_dep1 - p.qt_pendente + p.saldo_dep7 + p.qt_op + p.qt_lote_ma_mg + p.qt_lote_px + p.qt_lote_ul) AS estoque_90d,
        (p.saldo_dep1 - p.qt_pendente + p.saldo_dep7 + p.qt_op_pronta) AS estoque_pronta
    FROM produtos_base p
)

-- ============================================================
-- UNION 1: 30 dias
-- ============================================================
SELECT
    1 AS codempresa,
    f_dic_prd_nivel(cd_produto, 'CD') AS cd_nivel,
    cd_produto AS codigoproduto,
    cd_tamanho AS seqtamanho,
    cd_cor AS seqsortimento,
    clas_21 AS colecao,
    1 AS estoquelimitado,
    CASE
        WHEN clas_27 IN ('0008', '0007', '0003') AND estoque_base <= 2
        THEN 0
        ELSE estoque_30d
    END AS quantidade,
    ds_tamanho AS codtamanho,
    NULL::text AS "Código do depósito",
    ds_colecao AS nomecolecao,
    (CURRENT_DATE + 30) AS dataproduto,
    estoque_pronta AS quantidadeprontaentrega,
    cd_cor AS codcorbase,
    f_dic_prd_nivel(cd_produto, 'DS') AS nm_produto,
    ds_cor AS nomecor,
    f_dic_prd_codigobarra(cd_produto) AS ean13,
    NULL::text AS visualquantidadeproduto,
    NULL::text AS visualquantidadeproducao,
    cd_tamanho AS seqordenacaotamanho,
    CURRENT_TIMESTAMP AS dt_atualizacao
FROM produtos_calc
WHERE
    CASE
        WHEN clas_27 IN ('0008', '0007', '0003') AND estoque_base <= 2
        THEN 0
        ELSE estoque_30d
    END > 0

UNION ALL

-- ============================================================
-- UNION 2: 60 dias
-- ============================================================
SELECT
    1 AS codempresa,
    f_dic_prd_nivel(cd_produto, 'CD') AS cd_nivel,
    cd_produto AS codigoproduto,
    cd_tamanho AS seqtamanho,
    cd_cor AS seqsortimento,
    clas_21 AS colecao,
    1 AS estoquelimitado,
    CASE
        WHEN clas_27 IN ('0008', '0007', '0003') AND estoque_base <= 2
        THEN 0
        ELSE estoque_60d
    END AS quantidade,
    ds_tamanho AS codtamanho,
    NULL::text AS "Código do depósito",
    ds_colecao AS nomecolecao,
    (CURRENT_DATE + 60) AS dataproduto,
    estoque_pronta AS quantidadeprontaentrega,
    cd_cor AS codcorbase,
    f_dic_prd_nivel(cd_produto, 'DS') AS nm_produto,
    ds_cor AS nomecor,
    f_dic_prd_codigobarra(cd_produto) AS ean13,
    NULL::text AS visualquantidadeproduto,
    NULL::text AS visualquantidadeproducao,
    cd_tamanho AS seqordenacaotamanho,
    CURRENT_TIMESTAMP AS dt_atualizacao
FROM produtos_calc
WHERE estoque_60d > 0

UNION ALL

-- ============================================================
-- UNION 3: 90 dias
-- ============================================================
SELECT
    1 AS codempresa,
    f_dic_prd_nivel(cd_produto, 'CD') AS cd_nivel,
    cd_produto AS codigoproduto,
    cd_tamanho AS seqtamanho,
    cd_cor AS seqsortimento,
    clas_21 AS colecao,
    1 AS estoquelimitado,
    CASE
        WHEN clas_27 IN ('0008', '0007', '0003') AND estoque_base <= 2
        THEN 0
        ELSE estoque_90d
    END AS quantidade,
    ds_tamanho AS codtamanho,
    NULL::text AS "Código do depósito",
    ds_colecao AS nomecolecao,
    (CURRENT_DATE + 90) AS dataproduto,
    estoque_pronta AS quantidadeprontaentrega,
    cd_cor AS codcorbase,
    f_dic_prd_nivel(cd_produto, 'DS') AS nm_produto,
    ds_cor AS nomecor,
    f_dic_prd_codigobarra(cd_produto) AS ean13,
    NULL::text AS visualquantidadeproduto,
    NULL::text AS visualquantidadeproducao,
    cd_tamanho AS seqordenacaotamanho,
    CURRENT_TIMESTAMP AS dt_atualizacao
FROM produtos_calc
WHERE estoque_90d > 0

WITH DATA;

-- ============================================================
-- 3. CRIAR ÍNDICES PARA BUSCA RÁPIDA
-- ============================================================

-- Índice principal para busca por referência (cd_nivel)
CREATE INDEX idx_mv_geovendas_cd_nivel
ON mv_geovendas_estoque (cd_nivel);

-- Índice para busca por produto
CREATE INDEX idx_mv_geovendas_produto
ON mv_geovendas_estoque (codigoproduto);

-- Índice para busca por data
CREATE INDEX idx_mv_geovendas_data
ON mv_geovendas_estoque (dataproduto);

-- Índice composto para buscas combinadas
CREATE INDEX idx_mv_geovendas_nivel_data
ON mv_geovendas_estoque (cd_nivel, dataproduto);

-- Índice único para permitir REFRESH CONCURRENTLY
CREATE UNIQUE INDEX idx_mv_geovendas_unique
ON mv_geovendas_estoque (codigoproduto, seqtamanho, seqsortimento, dataproduto);

-- ============================================================
-- 4. COMANDOS ÚTEIS
-- ============================================================

-- Ver quando foi atualizada:
-- SELECT MAX(dt_atualizacao) FROM mv_geovendas_estoque;

-- Atualizar (bloqueia leituras durante refresh):
-- REFRESH MATERIALIZED VIEW mv_geovendas_estoque;

-- Atualizar sem bloquear (requer índice único):
-- REFRESH MATERIALIZED VIEW CONCURRENTLY mv_geovendas_estoque;

-- ============================================================
-- 5. CRIAR FUNÇÃO PARA REFRESH AUTOMÁTICO (OPCIONAL)
-- ============================================================

-- CREATE OR REPLACE FUNCTION refresh_mv_geovendas()
-- RETURNS void AS $$
-- BEGIN
--     REFRESH MATERIALIZED VIEW CONCURRENTLY mv_geovendas_estoque;
-- END;
-- $$ LANGUAGE plpgsql;

-- Para agendar (usar pg_cron ou cron do sistema):
-- SELECT cron.schedule('refresh_geovendas', '0 */2 * * *', 'SELECT refresh_mv_geovendas()');
-- (Atualiza a cada 2 horas)
