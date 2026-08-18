-- ============================================================
-- MRP - Análise de Matéria-Prima para produtos 60/90 dias
-- ============================================================
-- LÓGICA:
-- 1. Produtos apenas 60/90 dias (sem estoque 30d) → define LISTA de MPs
-- 2. Necessidade considera TODOS os produtos que usam essas MPs (0-90 dias)
-- ============================================================

WITH
-- PASSO 1: Produtos que aparecem nos próximos 30 dias
produtos_30_dias AS (
    SELECT DISTINCT codigoproduto
    FROM mv_geo3
    WHERE dataproduto >= CURRENT_DATE
      AND dataproduto <= CURRENT_DATE + INTERVAL '30 days'
),

-- PASSO 2: Produtos que SÓ aparecem em 60/90 dias (não em 30)
-- Esses produtos definem quais MPs serão analisadas
produtos_apenas_60_90 AS (
    SELECT DISTINCT m.codigoproduto
    FROM mv_geo3 m
    WHERE m.dataproduto > CURRENT_DATE + INTERVAL '30 days'
      AND m.dataproduto <= CURRENT_DATE + INTERVAL '90 days'
      AND NOT EXISTS (
          SELECT 1 FROM produtos_30_dias p30
          WHERE p30.codigoproduto = m.codigoproduto
      )
),

-- PASSO 3: MPs utilizadas por esses produtos (LISTA INICIAL)
mps_selecionadas AS (
    SELECT DISTINCT c.cd_produtomp
    FROM vr_pcp_fcconsumo c
    WHERE c.cd_produtopa IN (SELECT codigoproduto FROM produtos_apenas_60_90)
),

-- PASSO 4: Quantidade máxima de TODOS os produtos (0-90 dias)
quantidade_todos_produtos AS (
    SELECT
        m.codigoproduto,
        MAX(m.quantidade) AS quantidade_maxima
    FROM mv_geo3 m
    WHERE m.dataproduto >= CURRENT_DATE
      AND m.dataproduto <= CURRENT_DATE + INTERVAL '90 days'
    GROUP BY m.codigoproduto
),

-- PASSO 5: Necessidade de MP considerando TODOS os produtos que usam as MPs selecionadas
necessidade_mp AS (
    SELECT
        c.cd_produtomp,
        SUM(c.qt_consumo * q.quantidade_maxima) AS qt_necessidade
    FROM vr_pcp_fcconsumo c
    JOIN quantidade_todos_produtos q ON q.codigoproduto = c.cd_produtopa
    WHERE c.cd_produtomp IN (SELECT cd_produtomp FROM mps_selecionadas)
    GROUP BY c.cd_produtomp
),

-- PASSO 6: Estoque atual de MP (cd_saldo IN 1, 2, 15)
estoque_mp AS (
    SELECT
        s.cd_produto,
        SUM(s.qt_saldo) AS qt_estoque
    FROM prd_prdsaldo s
    WHERE s.cd_empresa = 1
      AND s.cd_saldo IN (1, 2, 15)
    GROUP BY s.cd_produto
),

-- PASSO 7: Classificação (artigo) - tipoclas 111
classificacao_mp AS (
    SELECT
        pc.cd_produto,
        cl.ds_classificacao AS artigo
    FROM prd_produtoclas pc
    JOIN prd_classificacao cl ON cl.cd_tipoclas = pc.cd_tipoclas
                              AND cl.cd_classificacao = pc.cd_classificacao
    WHERE pc.cd_tipoclas = 111
)

-- RESULTADO FINAL
SELECT
    n.cd_produtomp AS codigo_mp,
    p.ds_produto AS descricao_mp,
    COALESCE(c.artigo, '-') AS artigo,
    ROUND(n.qt_necessidade, 2) AS necessidade,
    COALESCE(ROUND(e.qt_estoque, 2), 0) AS estoque,
    ROUND(n.qt_necessidade - COALESCE(e.qt_estoque, 0), 2) AS falta
FROM necessidade_mp n
JOIN prd_produto p ON p.cd_produto = n.cd_produtomp
LEFT JOIN estoque_mp e ON e.cd_produto = n.cd_produtomp
LEFT JOIN classificacao_mp c ON c.cd_produto = n.cd_produtomp
WHERE n.qt_necessidade > COALESCE(e.qt_estoque, 0)
  AND c.artigo IS NOT NULL
  AND c.artigo NOT IN ('EMBALAGEM', 'ETIQUETA COMPOSICAO', 'TAG')
ORDER BY falta DESC;


-- ============================================================
-- QUERY 2: PRODUTOS 60/90 IMPACTADOS PELA FALTA DE MP
-- ============================================================

WITH
produtos_30_dias AS (
    SELECT DISTINCT codigoproduto
    FROM mv_geo3
    WHERE dataproduto >= CURRENT_DATE
      AND dataproduto <= CURRENT_DATE + INTERVAL '30 days'
),
produtos_apenas_60_90 AS (
    SELECT DISTINCT m.codigoproduto
    FROM mv_geo3 m
    WHERE m.dataproduto > CURRENT_DATE + INTERVAL '30 days'
      AND m.dataproduto <= CURRENT_DATE + INTERVAL '90 days'
      AND NOT EXISTS (
          SELECT 1 FROM produtos_30_dias p30
          WHERE p30.codigoproduto = m.codigoproduto
      )
),
mps_selecionadas AS (
    SELECT DISTINCT c.cd_produtomp
    FROM vr_pcp_fcconsumo c
    WHERE c.cd_produtopa IN (SELECT codigoproduto FROM produtos_apenas_60_90)
),
quantidade_todos_produtos AS (
    SELECT
        m.codigoproduto,
        MAX(m.quantidade) AS quantidade_maxima
    FROM mv_geo3 m
    WHERE m.dataproduto >= CURRENT_DATE
      AND m.dataproduto <= CURRENT_DATE + INTERVAL '90 days'
    GROUP BY m.codigoproduto
),
necessidade_mp AS (
    SELECT
        c.cd_produtomp,
        SUM(c.qt_consumo * q.quantidade_maxima) AS qt_necessidade
    FROM vr_pcp_fcconsumo c
    JOIN quantidade_todos_produtos q ON q.codigoproduto = c.cd_produtopa
    WHERE c.cd_produtomp IN (SELECT cd_produtomp FROM mps_selecionadas)
    GROUP BY c.cd_produtomp
),
estoque_mp AS (
    SELECT
        s.cd_produto,
        SUM(s.qt_saldo) AS qt_estoque
    FROM prd_prdsaldo s
    WHERE s.cd_empresa = 1
      AND s.cd_saldo IN (1, 2, 15)
    GROUP BY s.cd_produto
),
classificacao_mp AS (
    SELECT
        pc.cd_produto,
        cl.ds_classificacao AS artigo
    FROM prd_produtoclas pc
    JOIN prd_classificacao cl ON cl.cd_tipoclas = pc.cd_tipoclas
                              AND cl.cd_classificacao = pc.cd_classificacao
    WHERE pc.cd_tipoclas = 111
),
-- MPs COM FALTA (filtradas)
mps_com_falta AS (
    SELECT
        n.cd_produtomp,
        COALESCE(c.artigo, '-') AS artigo,
        n.qt_necessidade,
        COALESCE(e.qt_estoque, 0) AS qt_estoque,
        n.qt_necessidade - COALESCE(e.qt_estoque, 0) AS falta
    FROM necessidade_mp n
    LEFT JOIN estoque_mp e ON e.cd_produto = n.cd_produtomp
    LEFT JOIN classificacao_mp c ON c.cd_produto = n.cd_produtomp
    WHERE n.qt_necessidade > COALESCE(e.qt_estoque, 0)
      AND c.artigo IS NOT NULL
      AND c.artigo NOT IN ('EMBALAGEM', 'ETIQUETA COMPOSICAO', 'TAG')
)

-- PRODUTOS 60/90 IMPACTADOS
SELECT
    pa.codigoproduto AS codigo_pa,
    p.ds_produto AS descricao_pa,
    mf.cd_produtomp AS codigo_mp,
    mp.ds_produto AS descricao_mp,
    mf.artigo,
    ROUND(mf.falta, 0) AS falta_mp
FROM produtos_apenas_60_90 pa
JOIN vr_pcp_fcconsumo fc ON fc.cd_produtopa = pa.codigoproduto
JOIN mps_com_falta mf ON mf.cd_produtomp = fc.cd_produtomp
JOIN prd_produto p ON p.cd_produto = pa.codigoproduto
JOIN prd_produto mp ON mp.cd_produto = fc.cd_produtomp
ORDER BY mf.falta DESC, pa.codigoproduto;


-- ============================================================
-- QUERY 3: PRODUTOS AGRUPADOS COM ARTIGOS FALTANTES
-- ============================================================

WITH
produtos_30_dias AS (
    SELECT DISTINCT codigoproduto
    FROM mv_geo3
    WHERE dataproduto >= CURRENT_DATE
      AND dataproduto <= CURRENT_DATE + INTERVAL '30 days'
),
produtos_apenas_60_90 AS (
    SELECT DISTINCT m.codigoproduto
    FROM mv_geo3 m
    WHERE m.dataproduto > CURRENT_DATE + INTERVAL '30 days'
      AND m.dataproduto <= CURRENT_DATE + INTERVAL '90 days'
      AND NOT EXISTS (
          SELECT 1 FROM produtos_30_dias p30
          WHERE p30.codigoproduto = m.codigoproduto
      )
),
mps_selecionadas AS (
    SELECT DISTINCT c.cd_produtomp
    FROM vr_pcp_fcconsumo c
    WHERE c.cd_produtopa IN (SELECT codigoproduto FROM produtos_apenas_60_90)
),
quantidade_todos_produtos AS (
    SELECT
        m.codigoproduto,
        MAX(m.quantidade) AS quantidade_maxima
    FROM mv_geo3 m
    WHERE m.dataproduto >= CURRENT_DATE
      AND m.dataproduto <= CURRENT_DATE + INTERVAL '90 days'
    GROUP BY m.codigoproduto
),
necessidade_mp AS (
    SELECT
        c.cd_produtomp,
        SUM(c.qt_consumo * q.quantidade_maxima) AS qt_necessidade
    FROM vr_pcp_fcconsumo c
    JOIN quantidade_todos_produtos q ON q.codigoproduto = c.cd_produtopa
    WHERE c.cd_produtomp IN (SELECT cd_produtomp FROM mps_selecionadas)
    GROUP BY c.cd_produtomp
),
estoque_mp AS (
    SELECT
        s.cd_produto,
        SUM(s.qt_saldo) AS qt_estoque
    FROM prd_prdsaldo s
    WHERE s.cd_empresa = 1
      AND s.cd_saldo IN (1, 2, 15)
    GROUP BY s.cd_produto
),
classificacao_mp AS (
    SELECT
        pc.cd_produto,
        cl.ds_classificacao AS artigo
    FROM prd_produtoclas pc
    JOIN prd_classificacao cl ON cl.cd_tipoclas = pc.cd_tipoclas
                              AND cl.cd_classificacao = pc.cd_classificacao
    WHERE pc.cd_tipoclas = 111
),
mps_com_falta AS (
    SELECT
        n.cd_produtomp,
        COALESCE(c.artigo, '-') AS artigo,
        n.qt_necessidade - COALESCE(e.qt_estoque, 0) AS falta
    FROM necessidade_mp n
    LEFT JOIN estoque_mp e ON e.cd_produto = n.cd_produtomp
    LEFT JOIN classificacao_mp c ON c.cd_produto = n.cd_produtomp
    WHERE n.qt_necessidade > COALESCE(e.qt_estoque, 0)
      AND c.artigo IS NOT NULL
      AND c.artigo NOT IN ('EMBALAGEM', 'ETIQUETA COMPOSICAO', 'TAG')
),
produtos_com_artigos AS (
    SELECT
        pa.codigoproduto,
        mf.artigo
    FROM produtos_apenas_60_90 pa
    JOIN vr_pcp_fcconsumo fc ON fc.cd_produtopa = pa.codigoproduto
    JOIN mps_com_falta mf ON mf.cd_produtomp = fc.cd_produtomp
)

-- RESULTADO AGRUPADO
SELECT
    f_dic_prd_nivel(pa.codigoproduto::bigint, 'DS'::char) AS nivel,
    pa.codigoproduto,
    p.ds_produto AS descricao,
    STRING_AGG(DISTINCT pca.artigo, ', ' ORDER BY pca.artigo) AS artigos_faltantes,
    COUNT(DISTINCT pca.artigo) AS qtd_mps_faltantes
FROM produtos_apenas_60_90 pa
JOIN prd_produto p ON p.cd_produto = pa.codigoproduto
JOIN produtos_com_artigos pca ON pca.codigoproduto = pa.codigoproduto
GROUP BY pa.codigoproduto, p.ds_produto
ORDER BY qtd_mps_faltantes DESC, pa.codigoproduto;
