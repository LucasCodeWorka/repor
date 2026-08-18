BEGIN;

DELETE FROM reposicao_fora_regra
WHERE motivo = 'FABRICA_PERIODO_FORA_DA_BASE';

INSERT INTO reposicao_fora_regra (
    mes_recebimento,
    mes_lote,
    cd_loja,
    nome_loja,
    cd_produto,
    qt_entrada,
    nr_transacao,
    nr_transacaoori,
    dt_transacao,
    cd_empresaori,
    nome_origem,
    cd_lote,
    motivo,
    descricao_motivo
)
WITH meses AS (
    SELECT DISTINCT
        mes,
        (mes || '-01')::date AS inicio_mes,
        ((mes || '-01')::date + INTERVAL '1 month')::date AS fim_mes,
        to_char((mes || '-01')::date, 'YY.MM') || '%' AS lote_periodo
    FROM extrato_reposicao_loja_perm
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

base_demanda AS (
    SELECT
        m.mes,
        t.cd_empresa AS cd_loja,
        i.cd_produto
    FROM meses m
    JOIN vr_tra_transacao t
        ON TRUE
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
      AND i.dt_transacao >= m.inicio_mes - INTERVAL '3 months'
      AND i.dt_transacao < m.inicio_mes
      AND i.cd_compvend <> 1
      AND t.tp_situacao <> 6
      AND t.tp_modalidade::text IN ('3', '4')
    GROUP BY m.mes, t.cd_empresa, i.cd_produto
    HAVING SUM(
        i.qt_solicitada *
        CASE WHEN t.tp_modalidade::text = '3' THEN -1 ELSE 1 END
    ) > 0
)

SELECT
    m.mes AS mes_recebimento,
    m.mes AS mes_lote,
    t.cd_empresa AS cd_loja,
    emp.nm_grupoempresa AS nome_loja,
    i.cd_produto,
    i.qt_solicitada AS qt_entrada,
    t.nr_transacao,
    t.nr_transacaoori,
    i.dt_transacao,
    t.cd_empresaori,
    empori.nm_grupoempresa AS nome_origem,
    lote.cd_lote,
    'FABRICA_PERIODO_FORA_DA_BASE' AS motivo,
    'Lote do periodo, mas produto/loja nao estava na base de demanda' AS descricao_motivo
FROM meses m
JOIN vr_tra_transacao t
    ON TRUE
JOIN vr_tra_transitem i
    ON t.nr_transacao = i.nr_transacao
    AND t.cd_empresa = i.cd_empresa
JOIN vr_ger_empresa emp
    ON emp.cd_empresa = t.cd_empresa
LEFT JOIN vr_ger_empresa empori
    ON empori.cd_empresa = t.cd_empresaori
JOIN vr_ped_pedidotra ped
    ON ped.nr_transacao = t.nr_transacaoori
JOIN vr_ped_pedidoc2 lote
    ON ped.cd_emppedido = lote.cd_empresa
    AND ped.cd_pedido = lote.cd_pedido
    AND ped.cd_representant = lote.cd_representant
    AND lote.cd_lote LIKE m.lote_periodo
LEFT JOIN base_demanda b
    ON b.mes = m.mes
    AND b.cd_loja = t.cd_empresa
    AND b.cd_produto = i.cd_produto
WHERE t.cd_empresa > 1
  AND t.cd_empresa <> 4
  AND t.cd_empresaori = 1
  AND t.tp_operacao = 'E'
  AND t.tp_modalidade::text = '2'
  AND t.tp_situacao = 4
  AND i.dt_transacao >= m.inicio_mes
  AND i.dt_transacao < m.fim_mes
  AND b.cd_produto IS NULL;

COMMIT;
