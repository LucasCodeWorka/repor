-- Auditoria de recebimentos de junho/2026 para validar a base de reposicao.
--
-- Objetivo:
--   1. separar origem fabrica de origem nao fabrica;
--   2. separar lote do periodo, lote atrasado e sem lote;
--   3. identificar recebimento que nao estava na base de demanda do mes.

WITH produtos_permanente AS (
    SELECT DISTINCT pc.cd_produto
    FROM prd_produtoclas pc
    JOIN prd_classificacao c
        ON pc.cd_classificacao = c.cd_classificacao
        AND pc.cd_tipoclas = c.cd_tipoclas
    WHERE pc.cd_tipoclas = 802
      AND c.ds_classificacao IN ('PERMANENTE', 'PERMANENTE COR NOVA')
),

base_demanda_junho AS (
    SELECT
        t.cd_empresa AS cd_loja,
        i.cd_produto,
        SUM(
            i.qt_solicitada *
            CASE WHEN t.tp_modalidade::text = '3' THEN -1 ELSE 1 END
        ) AS vendas_3m
    FROM vr_tra_transacao t
    JOIN vr_tra_transitem i
        ON t.nr_transacao = i.nr_transacao
        AND t.cd_empresa = i.cd_empresa
    JOIN produtos_permanente pp
        ON pp.cd_produto = i.cd_produto
    WHERE t.cd_empresa > 1
      AND t.cd_empresa <> 4
      AND t.cd_operacao NOT IN (
          140, 76, 25, 26, 27, 273, 44,
          240, 241, 242, 243, 244, 245,
          239, 238, 237, 236
      )
      AND i.dt_transacao >= '2026-03-01'
      AND i.dt_transacao < '2026-06-01'
      AND i.cd_compvend <> 1
      AND t.tp_situacao <> 6
      AND t.tp_modalidade::text IN ('3', '4')
    GROUP BY t.cd_empresa, i.cd_produto
    HAVING SUM(
        i.qt_solicitada *
        CASE WHEN t.tp_modalidade::text = '3' THEN -1 ELSE 1 END
    ) > 0
),

entradas_junho AS (
    SELECT
        t.cd_empresa AS cd_loja,
        emp.nm_grupoempresa AS nome_loja,
        i.cd_produto,
        f_dic_prd_nivel(i.cd_produto, 'CD'::bpchar) AS referencia,
        i.qt_solicitada AS qt_entrada,
        t.cd_empresaori,
        lote.cd_lote,
        CASE
            WHEN t.cd_empresaori <> 1 THEN 'NAO_FABRICA'
            WHEN lote.cd_lote LIKE '26.06%' THEN 'FABRICA_PERIODO'
            WHEN lote.cd_lote IS NULL THEN 'FABRICA_SEM_LOTE'
            ELSE 'FABRICA_ATRASADA_COM_LOTE'
        END AS tipo_entrada
    FROM vr_tra_transacao t
    JOIN vr_tra_transitem i
        ON t.nr_transacao = i.nr_transacao
        AND t.cd_empresa = i.cd_empresa
    JOIN vr_ger_empresa emp
        ON emp.cd_empresa = t.cd_empresa
    LEFT JOIN vr_ped_pedidotra ped
        ON ped.nr_transacao = t.nr_transacaoori
    LEFT JOIN vr_ped_pedidoc2 lote
        ON ped.cd_emppedido = lote.cd_empresa
        AND ped.cd_pedido = lote.cd_pedido
        AND ped.cd_representant = lote.cd_representant
    WHERE t.cd_empresa > 1
      AND t.cd_empresa <> 4
      AND t.tp_operacao = 'E'
      AND t.tp_modalidade::text = '2'
      AND t.tp_situacao = 4
      AND i.dt_transacao >= '2026-06-01'
      AND i.dt_transacao < '2026-07-01'
)

SELECT
    tipo_entrada,
    CASE
        WHEN b.cd_produto IS NULL THEN 'FORA_DA_BASE_JUNHO'
        ELSE 'NA_BASE_JUNHO'
    END AS status_base,
    COUNT(DISTINCT e.cd_loja) AS lojas,
    COUNT(DISTINCT e.cd_loja || '-' || e.cd_produto) AS loja_skus,
    COUNT(DISTINCT e.cd_produto) AS skus,
    SUM(e.qt_entrada) AS pecas
FROM entradas_junho e
LEFT JOIN base_demanda_junho b
    ON b.cd_loja = e.cd_loja
    AND b.cd_produto = e.cd_produto
GROUP BY tipo_entrada, status_base
ORDER BY tipo_entrada, status_base;

-- Detalhe dos principais lotes atrasados com lote preenchido:
--
-- SELECT
--     cd_lote,
--     COUNT(DISTINCT cd_loja) AS lojas,
--     COUNT(DISTINCT cd_produto) AS skus,
--     SUM(qt_entrada) AS pecas
-- FROM entradas_junho
-- WHERE tipo_entrada = 'FABRICA_ATRASADA_COM_LOTE'
-- GROUP BY cd_lote
-- ORDER BY pecas DESC;
