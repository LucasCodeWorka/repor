-- ============================================================
-- VIEW DE ESTOQUE GEOVENDAS - VERSÃO OTIMIZADA
-- ============================================================
-- Mudanças:
-- 1. Usa JOINs com prd_produtoclas ao invés de múltiplas chamadas f_dic_prd_classificacao
-- 2. Usa CTE para calcular subqueries repetidas uma única vez
-- 3. Mantém a mesma lógica de negócio
-- ============================================================

WITH
-- Pré-calcula classificações por produto (evita múltiplas chamadas de função)
classificacoes AS (
    SELECT
        pc.cd_produto,
        MAX(CASE WHEN pc.cd_tipoclas = 20 THEN pc.cd_classificacao END) AS clas_20_cd,   -- Família
        MAX(CASE WHEN pc.cd_tipoclas = 21 THEN pc.cd_classificacao END) AS clas_21_cd,   -- Coleção
        MAX(CASE WHEN pc.cd_tipoclas = 27 THEN pc.cd_classificacao END) AS clas_27_cd,   -- Status
        MAX(CASE WHEN pc.cd_tipoclas = 124 THEN pc.cd_classificacao END) AS clas_124_cd  -- Prazo
    FROM prd_produtoclas pc
    WHERE pc.cd_tipoclas IN (20, 21, 27, 124)
    GROUP BY pc.cd_produto
),

-- Descrição da coleção (tipo 21)
colecao_desc AS (
    SELECT cd_classificacao, ds_classificacao
    FROM prd_classificacao
    WHERE cd_tipoclas = 21
),

-- Pedidos pendentes por produto
pedidos_pendentes AS (
    SELECT
        cd_produto,
        COALESCE(SUM(qt_pendente), 0) AS qt_pendente_total
    FROM vr_ped_pedidoi
    WHERE cd_operacao <> 44
      AND cd_empresa = 1
      AND tp_situacao <> 6
    GROUP BY cd_produto
),

-- OPs em produção por produto
ops_producao AS (
    SELECT
        aa.cd_produto,
        SUM(COALESCE(aa.qt_real, 0) - COALESCE(aa.qt_finalizada, 0)) AS qt_op_pendente
    FROM vr_pcp_opi aa
    JOIN vr_pcp_opc bb ON aa.cd_empresa = bb.cd_empresa
                       AND aa.nr_ciclo = bb.nr_ciclo
                       AND aa.nr_op = bb.nr_op
    WHERE aa.cd_empresa = 1
      AND COALESCE(bb.cd_categoria, 0) <> 15
      AND aa.tp_situacao IN (5, 10, 15, 20)
    GROUP BY aa.cd_produto
),

-- OPs em produção com filtro de data (para pronta entrega)
ops_producao_pronta AS (
    SELECT
        aa.cd_produto,
        SUM(COALESCE(aa.qt_real, 0) - COALESCE(aa.qt_finalizada, 0)) AS qt_op_pronta
    FROM vr_pcp_opi aa
    JOIN vr_pcp_opc bb ON aa.cd_empresa = bb.cd_empresa
                       AND aa.nr_ciclo = bb.nr_ciclo
                       AND aa.nr_op = bb.nr_op
    JOIN prd_produtoclas cc ON aa.cd_produto = cc.cd_produto
                            AND cc.cd_tipoclas = 802
                            AND cc.cd_classificacao = '2         '
    WHERE aa.cd_empresa = 1
      AND bb.dt_inclusao <= '2026-05-19 00:00:00'
      AND COALESCE(bb.cd_categoria, 0) <> 15
      AND aa.tp_situacao IN (5, 10, 15, 20)
    GROUP BY aa.cd_produto
),

-- Lotes planejados MA/MG
lotes_ma_mg AS (
    SELECT
        b.cd_produto,
        COALESCE(SUM(GREATEST(b.qt_lote - COALESCE(b.qt_gerouop, 0), 0)), 0) AS qt_lote
    FROM vr_pcp_lotepl2 b
    LEFT JOIN pcp_lotepv p ON b.nr_lote = p.nr_lote
    WHERE p.cd_auxiliar IN ('MA', 'MG')
    GROUP BY b.cd_produto
),

-- Lotes planejados PX
lotes_px AS (
    SELECT
        b.cd_produto,
        COALESCE(SUM(GREATEST(b.qt_lote - COALESCE(b.qt_gerouop, 0), 0)), 0) AS qt_lote
    FROM vr_pcp_lotepl2 b
    LEFT JOIN pcp_lotepv p ON b.nr_lote = p.nr_lote
    WHERE p.cd_auxiliar = 'PX'
    GROUP BY b.cd_produto
),

-- Lotes planejados UL
lotes_ul AS (
    SELECT
        b.cd_produto,
        COALESCE(SUM(GREATEST(b.qt_lote - COALESCE(b.qt_gerouop, 0), 0)), 0) AS qt_lote
    FROM vr_pcp_lotepl2 b
    LEFT JOIN pcp_lotepv p ON b.nr_lote = p.nr_lote
    WHERE p.cd_auxiliar = 'UL'
    GROUP BY b.cd_produto
),

-- Base de produtos (grade + info + classificações)
produtos_base AS (
    SELECT
        a.cd_produto,
        a.cd_tamanho,
        a.cd_cor,
        a.ds_tamanho,
        a.ds_cor,
        c.clas_20_cd,
        c.clas_21_cd,
        c.clas_27_cd,
        c.clas_124_cd,
        cd.ds_classificacao AS ds_colecao,
        -- Saldos
        COALESCE(f_prd_saldo_produto(1, 1, a.cd_produto, NULL), 0) AS saldo_dep1,
        COALESCE(f_prd_saldo_produto(1, 7, a.cd_produto, NULL), 0) AS saldo_dep7,
        -- Pedidos pendentes
        COALESCE(pp.qt_pendente_total, 0) AS qt_pendente,
        -- OPs
        COALESCE(op.qt_op_pendente, 0) AS qt_op,
        COALESCE(opp.qt_op_pronta, 0) AS qt_op_pronta,
        -- Lotes
        COALESCE(lmg.qt_lote, 0) AS qt_lote_ma_mg,
        COALESCE(lpx.qt_lote, 0) AS qt_lote_px,
        COALESCE(lul.qt_lote, 0) AS qt_lote_ul
    FROM vr_prd_prdgrade a
    JOIN vr_prd_prdinfo b ON b.cd_produto = a.cd_produto AND b.cd_empresa = 1
    LEFT JOIN classificacoes c ON c.cd_produto = a.cd_produto
    LEFT JOIN colecao_desc cd ON cd.cd_classificacao = c.clas_21_cd
    LEFT JOIN pedidos_pendentes pp ON pp.cd_produto = a.cd_produto
    LEFT JOIN ops_producao op ON op.cd_produto = a.cd_produto
    LEFT JOIN ops_producao_pronta opp ON opp.cd_produto = a.cd_produto
    LEFT JOIN lotes_ma_mg lmg ON lmg.cd_produto = a.cd_produto
    LEFT JOIN lotes_px lpx ON lpx.cd_produto = a.cd_produto
    LEFT JOIN lotes_ul lul ON lul.cd_produto = a.cd_produto
    WHERE b.in_inativo = 'F'
      AND a.cd_cor <> 'LF        '
      -- Filtro família (tipo 20)
      AND (c.clas_20_cd IN ('0001', '0002', '0003', '0020', '0009'))
      -- Filtro tipo 124
      AND (c.clas_124_cd IN ('001', '002', '007', '004', '005') OR c.clas_124_cd IS NULL)
      -- Filtro código produto
      AND (a.cd_produto < 1000000 OR a.cd_produto IN (5001609, 5001610, 5001319, 5001611))
),

-- Calcula estoques intermediários
produtos_calc AS (
    SELECT
        p.*,
        -- Estoque base (saldo - pendentes + dep7)
        (p.saldo_dep1 - p.qt_pendente + p.saldo_dep7) AS estoque_base,
        -- Estoque com OP (apenas para tipos 124 permitidos)
        CASE
            WHEN p.clas_124_cd IN ('001', '002', '004', '005') OR p.clas_124_cd IS NULL
            THEN p.qt_op
            ELSE 0
        END AS qt_op_filtrada
    FROM produtos_base p
)

-- ============================================================
-- UNION 1: Disponível em 30 dias (ESTOQUE + OP)
-- ============================================================
SELECT
    1 AS codempresa,
    f_dic_prd_nivel(cd_produto, 'CD') AS cd_nivel,
    cd_produto AS codigoproduto,
    cd_tamanho AS seqtamanho,
    cd_cor AS seqsortimento,
    clas_21_cd AS colecao,
    1 AS estoquelimitado,
    -- Quantidade: ESTOQUE + OP
    CASE
        WHEN clas_27_cd IN ('0008', '0007', '0003')
             AND (estoque_base <= 2)
        THEN 0
        ELSE (estoque_base + qt_op_filtrada)
    END AS quantidade,
    ds_tamanho AS codtamanho,
    NULL::text AS "Código do depósito",
    ds_colecao AS nomecolecao,
    (CURRENT_DATE + 30) AS dataproduto,
    -- Quantidade pronta entrega
    (estoque_base + qt_op_pronta) AS quantidadeprontaentrega,
    cd_cor AS codcorbase,
    f_dic_prd_nivel(cd_produto, 'DS') AS nm_produto,
    ds_cor AS nomecor,
    f_dic_prd_codigobarra(cd_produto) AS ean13,
    NULL::text AS visualquantidadeproduto,
    NULL::text AS visualquantidadeproducao,
    cd_tamanho AS seqordenacaotamanho
FROM produtos_calc
WHERE
    -- Filtro: ESTOQUE + OP > 0
    CASE
        WHEN clas_27_cd IN ('0008', '0007', '0003')
             AND (estoque_base <= 2)
        THEN 0
        ELSE (estoque_base + qt_op_filtrada)
    END > 0

UNION ALL

-- ============================================================
-- UNION 2: Disponível em 60 dias (ESTOQUE + OP + MA/MG + PX)
-- Acumula: planos de produção MA/MG e PX
-- ============================================================
SELECT
    1 AS codempresa,
    f_dic_prd_nivel(cd_produto, 'CD') AS cd_nivel,
    cd_produto AS codigoproduto,
    cd_tamanho AS seqtamanho,
    cd_cor AS seqsortimento,
    clas_21_cd AS colecao,
    1 AS estoquelimitado,
    CASE
        WHEN clas_27_cd IN ('0008', '0007', '0003')
             AND (estoque_base <= 2)
        THEN 0
        ELSE (estoque_base + qt_op_filtrada + qt_lote_ma_mg + qt_lote_px)
    END AS quantidade,
    ds_tamanho AS codtamanho,
    NULL::text AS "Código do depósito",
    ds_colecao AS nomecolecao,
    (CURRENT_DATE + 60) AS dataproduto,
    (estoque_base + qt_op_pronta) AS quantidadeprontaentrega,
    cd_cor AS codcorbase,
    f_dic_prd_nivel(cd_produto, 'DS') AS nm_produto,
    ds_cor AS nomecor,
    f_dic_prd_codigobarra(cd_produto) AS ean13,
    NULL::text AS visualquantidadeproduto,
    NULL::text AS visualquantidadeproducao,
    cd_tamanho AS seqordenacaotamanho
FROM produtos_calc
WHERE
    (estoque_base + qt_op_filtrada + qt_lote_ma_mg + qt_lote_px) > 0

UNION ALL

-- ============================================================
-- UNION 3: Disponível em 90 dias (ESTOQUE + OP + MA/MG + PX + UL)
-- Acumula: todos os planos de produção incluindo UL
-- ============================================================
SELECT
    1 AS codempresa,
    f_dic_prd_nivel(cd_produto, 'CD') AS cd_nivel,
    cd_produto AS codigoproduto,
    cd_tamanho AS seqtamanho,
    cd_cor AS seqsortimento,
    clas_21_cd AS colecao,
    1 AS estoquelimitado,
    CASE
        WHEN clas_27_cd IN ('0008', '0007', '0003')
             AND (estoque_base <= 2)
        THEN 0
        ELSE (estoque_base + qt_op_filtrada + qt_lote_ma_mg + qt_lote_px + qt_lote_ul)
    END AS quantidade,
    ds_tamanho AS codtamanho,
    NULL::text AS "Código do depósito",
    ds_colecao AS nomecolecao,
    (CURRENT_DATE + 90) AS dataproduto,
    (estoque_base + qt_op_pronta) AS quantidadeprontaentrega,
    cd_cor AS codcorbase,
    f_dic_prd_nivel(cd_produto, 'DS') AS nm_produto,
    ds_cor AS nomecor,
    f_dic_prd_codigobarra(cd_produto) AS ean13,
    NULL::text AS visualquantidadeproduto,
    NULL::text AS visualquantidadeproducao,
    cd_tamanho AS seqordenacaotamanho
FROM produtos_calc
WHERE
    (estoque_base + qt_op_filtrada + qt_lote_ma_mg + qt_lote_px + qt_lote_ul) > 0;
