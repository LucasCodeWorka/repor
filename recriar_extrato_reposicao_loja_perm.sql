-- Recria o extrato de reposicao permanente por loja separando entrada do periodo
-- de entrada atrasada.
--
-- Regra:
--   entrada_periodo = entrada da fabrica com lote do mes analisado (ex.: 26.06%)
--   entrada_atrasada = entrada da fabrica com lote preenchido diferente do mes
--   entrada_sem_lote = entrada da fabrica sem lote identificado
--   entradas de origem diferente da fabrica ficam fora da conta
--
-- Para outro mes, ajuste somente a CTE parametros.

BEGIN;

DROP TABLE IF EXISTS extrato_reposicao_loja_perm;

CREATE TABLE extrato_reposicao_loja_perm AS
WITH parametros AS (
    SELECT
        '2026-06'::text AS mes,
        '2026-06-01'::date AS inicio_mes,
        '2026-07-01'::date AS fim_mes,
        '26.06%'::text AS lote_periodo
),

produtos_permanente AS (
    SELECT DISTINCT pc.cd_produto
    FROM prd_produtoclas pc
    JOIN prd_classificacao c
        ON pc.cd_classificacao = c.cd_classificacao
        AND pc.cd_tipoclas = c.cd_tipoclas
    WHERE pc.cd_tipoclas = 802
      AND c.ds_classificacao IN ('PERMANENTE', 'PERMANENTE COR NOVA')
),

entradas_mes AS (
    SELECT
        p.mes,
        t.cd_empresa AS cd_loja,
        i.cd_produto,
        i.qt_solicitada AS qt_entrada,
        lote.cd_lote,
        CASE
            WHEN lote.cd_lote LIKE p.lote_periodo THEN 'PERIODO'
            WHEN lote.cd_lote IS NULL THEN 'SEM_LOTE'
            ELSE 'ATRASADA'
        END AS tipo_entrada
    FROM parametros p
    JOIN vr_tra_transacao t
        ON TRUE
    JOIN vr_tra_transitem i
        ON t.nr_transacao = i.nr_transacao
        AND t.cd_empresa = i.cd_empresa
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
      AND t.cd_empresaori = 1
      AND i.dt_transacao >= p.inicio_mes
      AND i.dt_transacao < p.fim_mes
),

entradas_agregadas AS (
    SELECT
        mes,
        cd_loja,
        cd_produto,
        COALESCE(SUM(qt_entrada) FILTER (WHERE tipo_entrada = 'PERIODO'), 0) AS entrada_periodo,
        COALESCE(SUM(qt_entrada) FILTER (WHERE tipo_entrada = 'ATRASADA'), 0) AS entrada_atrasada,
        COALESCE(SUM(qt_entrada) FILTER (WHERE tipo_entrada = 'SEM_LOTE'), 0) AS entrada_sem_lote,
        COALESCE(SUM(qt_entrada), 0) AS entrada_total
    FROM entradas_mes
    GROUP BY mes, cd_loja, cd_produto
),

vendas_3m AS (
    SELECT
        p.mes,
        p.inicio_mes,
        t.cd_empresa AS cd_loja,
        i.cd_produto,
        SUM(
            i.qt_solicitada *
            CASE WHEN t.tp_modalidade::text = '3' THEN -1 ELSE 1 END
        ) AS vendas_3m
    FROM parametros p
    JOIN vr_tra_transacao t
        ON TRUE
    JOIN vr_tra_transitem i
        ON t.nr_transacao = i.nr_transacao
        AND t.cd_empresa = i.cd_empresa
    WHERE t.cd_empresa > 1
      AND t.cd_empresa <> 4
      AND t.cd_operacao NOT IN (
          140, 76, 25, 26, 27, 273, 44,
          240, 241, 242, 243, 244, 245,
          239, 238, 237, 236
      )
      AND i.dt_transacao >= p.inicio_mes - INTERVAL '3 months'
      AND i.dt_transacao < p.inicio_mes
      AND i.cd_compvend <> 1
      AND t.tp_situacao <> 6
      AND t.tp_modalidade::text IN ('3', '4')
    GROUP BY p.mes, p.inicio_mes, t.cd_empresa, i.cd_produto
    HAVING SUM(
        i.qt_solicitada *
        CASE WHEN t.tp_modalidade::text = '3' THEN -1 ELSE 1 END
    ) > 0
),

base_sem_curva AS (
    SELECT
        v.mes,
        v.cd_loja,
        emp.nm_grupoempresa AS nome_loja,
        v.cd_produto,
        f_dic_prd_nivel(v.cd_produto, 'CD'::bpchar) AS referencia,
        ROUND(v.vendas_3m / 3.0 * 1.5, 0) AS estoque_minimo,
        COALESCE(
            f_prd_saldo_produto(
                v.cd_loja,
                1::bigint,
                v.cd_produto,
                v.inicio_mes
            ),
            0
        ) AS saldo_inicial
    FROM vendas_3m v
    JOIN vr_ger_empresa emp
        ON v.cd_loja = emp.cd_empresa
    JOIN produtos_permanente pp
        ON v.cd_produto = pp.cd_produto
),

base AS (
    SELECT
        b.*,
        COALESCE(abc.curva_completa, 'SEM CURVA') AS curva_completa
    FROM base_sem_curva b
    LEFT JOIN curva_abc abc
        ON abc.referencia = b.referencia
),

analise AS (
    SELECT
        b.*,
        GREATEST(0, b.estoque_minimo - b.saldo_inicial) AS necessidade,
        COALESCE(e.entrada_periodo, 0) AS entrada_periodo,
        COALESCE(e.entrada_atrasada, 0) AS entrada_atrasada,
        COALESCE(e.entrada_sem_lote, 0) AS entrada_sem_lote,
        COALESCE(e.entrada_total, 0) AS entrada_total
    FROM base b
    LEFT JOIN entradas_agregadas e
        ON b.mes = e.mes
        AND b.cd_loja = e.cd_loja
        AND b.cd_produto = e.cd_produto
)

SELECT
    mes,
    cd_loja,
    nome_loja,
    SUM(necessidade) AS necessidade,
    SUM(entrada_periodo) AS entrada_periodo,
    SUM(entrada_atrasada) AS entrada_atrasada,
    SUM(entrada_sem_lote) AS entrada_sem_lote,
    SUM(entrada_total) AS entrada_total,
    SUM(GREATEST(0, necessidade - entrada_periodo)) AS faltou,
    COUNT(*) FILTER (WHERE necessidade > 0) AS skus_demanda,
    COUNT(*) FILTER (WHERE entrada_periodo >= necessidade AND necessidade > 0) AS skus_ok,
    COUNT(*) FILTER (WHERE entrada_periodo > 0 AND entrada_periodo < necessidade) AS skus_parcial,
    COUNT(*) FILTER (WHERE entrada_periodo = 0 AND necessidade > 0) AS skus_zerados,
    ROUND(
        100.0 *
        COUNT(*) FILTER (WHERE entrada_periodo >= necessidade AND necessidade > 0) /
        NULLIF(COUNT(*) FILTER (WHERE necessidade > 0), 0),
        1
    ) AS pct_ok,
    STRING_AGG(DISTINCT curva_completa, ', ' ORDER BY curva_completa)
        FILTER (WHERE necessidade > entrada_periodo) AS curvas_com_falta
FROM analise
GROUP BY mes, cd_loja, nome_loja
ORDER BY mes, cd_loja;

COMMIT;

-- Validacao rapida:
-- SELECT * FROM extrato_reposicao_loja_perm ORDER BY mes, cd_loja;
-- SELECT
--     mes,
--     SUM(necessidade) AS necessidade,
--     SUM(entrada_periodo) AS entrada_periodo,
--     SUM(entrada_atrasada) AS entrada_atrasada,
--     SUM(entrada_sem_lote) AS entrada_sem_lote,
--     SUM(entrada_total) AS entrada_total
-- FROM extrato_reposicao_loja_perm
-- GROUP BY mes;
