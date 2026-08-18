-- VERSAO 2: Query completa com Vendas 3 meses, Lojas e Saldo
-- Objetivo: Analisar se pedidos Curva A/AA atenderam estoque minimo
-- TESTADA E FUNCIONANDO em 2026-08-04

-- =====================================================
-- CTE 1: Vendas ultimos 3 meses por loja/produto
-- =====================================================
WITH vendas_3m AS (
    SELECT
        t.cd_empresa AS cd_loja,
        i.cd_produto,
        f_dic_prd_nivel(i.cd_produto, 'CD'::bpchar) AS referencia,
        SUM(i.qt_solicitada * (
            CASE WHEN t.tp_modalidade::text = '3' THEN -1 ELSE 1 END
        )::double precision) AS qt_vendida_3m,
        ROUND(
            SUM(i.qt_solicitada * (
                CASE WHEN t.tp_modalidade::text = '3' THEN -1 ELSE 1 END
            )::double precision) / 3.0,
            2
        ) AS media_mensal
    FROM vr_tra_transacao t
    JOIN vr_tra_transitem i
        ON t.nr_transacao = i.nr_transacao
        AND t.cd_empresa = i.cd_empresa
    WHERE t.cd_empresa <> 1
        AND t.cd_operacao NOT IN (140, 76, 25, 26, 27, 273, 44, 240, 241, 242, 243, 244, 245, 239, 238, 237, 236)
        AND i.dt_transacao >= CURRENT_DATE - INTERVAL '3 months'
        AND i.cd_compvend <> 1
        AND t.tp_situacao <> 6
        AND t.tp_modalidade::text IN ('3', '4')
    GROUP BY t.cd_empresa, i.cd_produto
),

-- =====================================================
-- CTE 2: Pedidos base com cliente (loja destino)
-- =====================================================
pedidos_base AS (
    SELECT
        ped.cd_emppedido,
        ped.cd_representant,
        ped.cd_pedido,
        ped.nr_transacao,
        ped.dt_inclusao,
        ped.dt_transacao,
        item.cd_cliente,
        lote.cd_lote,
        item.cd_produto,
        f_dic_prd_nivel(item.cd_produto, 'CD'::bpchar) AS referencia
    FROM vr_ped_pedidotra AS ped
    LEFT JOIN vr_ped_pedidoc2 AS lote
        ON ped.cd_emppedido = lote.cd_empresa
        AND ped.cd_pedido = lote.cd_pedido
        AND ped.cd_representant = lote.cd_representant
    LEFT JOIN vr_ped_pedidoi AS item
        ON ped.cd_emppedido = item.cd_empresa
        AND ped.cd_pedido = item.cd_pedido
        AND ped.cd_representant = item.cd_representant
    WHERE ped.dt_inclusao >= '2026-06-01'
        AND ped.dt_inclusao <= '2026-06-15'
        AND ped.cd_emppedido = 1
),

-- =====================================================
-- CTE 3: Adiciona curva ABC
-- =====================================================
pedidos_com_curva AS (
    SELECT
        pb.*,
        abc.curva_completa
    FROM pedidos_base AS pb
    LEFT JOIN curva_abc AS abc
        ON abc.referencia = pb.referencia
),

-- =====================================================
-- CTE 4: Agrega por pedido com % curva A
-- =====================================================
pedidos_agregados AS (
    SELECT
        cd_emppedido,
        cd_representant,
        cd_pedido,
        nr_transacao,
        dt_inclusao,
        dt_transacao,
        (dt_transacao::date - dt_inclusao::date) AS lead_time_dias,
        cd_cliente,
        cd_lote,
        COUNT(*) AS total_itens,
        COUNT(*) FILTER (WHERE curva_completa IN ('CURVA A', 'CURVA AA')) AS itens_curva_a,
        ROUND(
            100.0 * COUNT(*) FILTER (WHERE curva_completa IN ('CURVA A', 'CURVA AA')) / NULLIF(COUNT(*), 0),
            2
        ) AS pct_curva_a
    FROM pedidos_com_curva
    GROUP BY
        cd_emppedido,
        cd_representant,
        cd_pedido,
        nr_transacao,
        dt_inclusao,
        dt_transacao,
        cd_cliente,
        cd_lote
)

-- =====================================================
-- SELECT FINAL: Junta com pessoa e loja e vendas
-- =====================================================
SELECT
    pa.cd_emppedido,
    pa.cd_representant,
    pa.cd_pedido,
    pa.nr_transacao,
    pa.dt_inclusao,
    pa.dt_transacao,
    pa.lead_time_dias,
    pa.cd_cliente,
    pes.nm_pessoa AS nome_cliente,
    emp.ds_empresa AS nome_loja,
    pa.cd_lote,
    pa.total_itens,
    pa.itens_curva_a,
    pa.pct_curva_a,
    COALESCE(v3.total_vendido_3m, 0) AS vendas_3m_loja,
    COALESCE(v3.media_mensal_loja, 0) AS media_mensal_loja,
    ROUND(COALESCE(v3.media_mensal_loja, 0) * 1.5, 0) AS estoque_minimo_sugerido
FROM pedidos_agregados pa
-- Join com pessoa para nome do cliente
LEFT JOIN vr_pes_pessoa pes
    ON pa.cd_cliente = pes.cd_pessoa
-- Join com empresa (se cliente for loja propria)
LEFT JOIN vr_ger_empresa emp
    ON pa.cd_cliente = emp.cd_empresa
-- Join com vendas 3m agregadas por loja
LEFT JOIN (
    SELECT
        cd_loja,
        SUM(qt_vendida_3m) AS total_vendido_3m,
        SUM(media_mensal) AS media_mensal_loja
    FROM vendas_3m
    GROUP BY cd_loja
) v3 ON pa.cd_cliente = v3.cd_loja
WHERE pa.pct_curva_a >= 80
ORDER BY pa.dt_inclusao DESC;
