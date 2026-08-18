BEGIN;

DROP TABLE IF EXISTS reposicao_fora_regra;

CREATE TABLE reposicao_fora_regra AS
WITH meses AS (
    SELECT DISTINCT
        mes,
        (mes || '-01')::date AS inicio_mes,
        ((mes || '-01')::date + INTERVAL '1 month')::date AS fim_mes,
        to_char((mes || '-01')::date, 'YY.MM') || '%' AS lote_periodo
    FROM extrato_reposicao_loja_perm
),

entradas_recebidas AS (
    SELECT
        m.mes AS mes_recebimento,
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
        CASE
            WHEN lote.cd_lote ~ '^[0-9]{2}\.[0-9]{2}' THEN '20' || replace(substring(lote.cd_lote from 1 for 5), '.', '-')
            ELSE NULL
        END AS mes_lote,
        CASE
            WHEN t.cd_empresaori <> 1 THEN 'NAO_FABRICA'
            WHEN lote.cd_lote IS NULL THEN 'FABRICA_SEM_LOTE'
            WHEN lote.cd_lote NOT LIKE m.lote_periodo THEN 'FABRICA_ATRASADA_COM_LOTE'
            ELSE 'DENTRO_REGRA'
        END AS motivo
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
      AND i.dt_transacao >= m.inicio_mes
      AND i.dt_transacao < m.fim_mes
)

SELECT
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
    CASE
        WHEN motivo = 'NAO_FABRICA' THEN 'Origem diferente da fabrica'
        WHEN motivo = 'FABRICA_SEM_LOTE' THEN 'Entrada da fabrica sem lote vinculado'
        WHEN motivo = 'FABRICA_ATRASADA_COM_LOTE' THEN 'Entrada da fabrica com lote de outro mes'
        ELSE 'Dentro da regra'
    END AS descricao_motivo
FROM entradas_recebidas
WHERE motivo <> 'DENTRO_REGRA';

CREATE INDEX idx_reposicao_fora_regra_mes_motivo
    ON reposicao_fora_regra (mes_recebimento, motivo);

CREATE INDEX idx_reposicao_fora_regra_produto
    ON reposicao_fora_regra (cd_produto);

COMMIT;

-- Validacao:
-- SELECT mes_recebimento, motivo, SUM(qt_entrada)
-- FROM reposicao_fora_regra
-- GROUP BY mes_recebimento, motivo
-- ORDER BY mes_recebimento, motivo;
