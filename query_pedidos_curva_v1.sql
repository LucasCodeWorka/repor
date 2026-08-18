-- VERSAO 1: Query de pedidos com % Curva A/AA e Lead Time
-- Salva em: 2026-08-04

WITH pedidos_base AS (
    SELECT
        ped.cd_emppedido,
        ped.cd_representant,
        ped.cd_pedido,
        ped.nr_transacao,
        ped.dt_inclusao,
        ped.dt_transacao,
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
        AND ped.cd_emppedido = 1
        AND ped.cd_representant = 32098
),
pedidos_com_curva AS (
    SELECT
        pb.*,
        abc.curva_completa
    FROM pedidos_base AS pb
    LEFT JOIN curva_abc AS abc
        ON abc.referencia = pb.referencia
),
percentual_curva AS (
    SELECT
        cd_emppedido,
        cd_representant,
        cd_pedido,
        nr_transacao,
        dt_inclusao,
        dt_transacao,
        (dt_transacao::date - dt_inclusao::date) AS lead_time_dias,
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
        cd_lote
)
SELECT
    cd_emppedido,
    cd_representant,
    cd_pedido,
    nr_transacao,
    dt_inclusao,
    dt_transacao,
    lead_time_dias,
    cd_lote,
    total_itens,
    itens_curva_a,
    pct_curva_a
FROM percentual_curva
WHERE pct_curva_a >= 80
ORDER BY dt_inclusao DESC;
