-- Cria tabelas praticas para auditar a reposicao com a regra atual.
--
-- reposicao_dentro_regra:
--   consolidado por mes + loja, vindo da tabela ja calculada
--   extrato_reposicao_loja_perm.
--
-- reposicao_fora_regra:
--   detalhe dos recebimentos que nao podem entrar como reposicao valida:
--     origem nao fabrica;
--     fabrica sem lote;
--     fabrica com lote atrasado;
--     fabrica com lote do periodo, mas produto/loja fora da base de demanda do mes.

BEGIN;

DROP TABLE IF EXISTS reposicao_dentro_regra;
DROP TABLE IF EXISTS reposicao_fora_regra;

CREATE TABLE reposicao_dentro_regra AS
SELECT
    mes,
    cd_loja,
    nome_loja,
    necessidade,
    entrada_periodo,
    entrada_atrasada,
    0::double precision AS entrada_sem_lote,
    entrada_total,
    faltou,
    skus_demanda,
    skus_ok,
    skus_parcial,
    skus_zerados,
    pct_ok,
    curvas_com_falta,
    GREATEST(0, entrada_periodo - necessidade) AS sobra_periodo
FROM extrato_reposicao_loja_perm;

CREATE TABLE reposicao_fora_regra AS
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
),

entradas_recebidas AS (
    SELECT
        m.mes AS mes_recebimento,
        t.cd_empresa AS cd_loja,
        emp.nm_grupoempresa AS nome_loja,
        i.cd_produto,
        f_dic_prd_nivel(i.cd_produto, 'CD'::bpchar) AS referencia,
        f_dic_prd_nivel(i.cd_produto, 'DS'::bpchar) AS descricao_produto,
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
            WHEN b.cd_produto IS NULL THEN 'FABRICA_PERIODO_FORA_DA_BASE'
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
    LEFT JOIN base_demanda b
        ON b.mes = m.mes
        AND b.cd_loja = t.cd_empresa
        AND b.cd_produto = i.cd_produto
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
    referencia,
    descricao_produto,
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
        WHEN motivo = 'FABRICA_PERIODO_FORA_DA_BASE' THEN 'Lote do periodo, mas produto/loja nao estava na base de demanda'
        ELSE 'Dentro da regra'
    END AS descricao_motivo
FROM entradas_recebidas
WHERE motivo <> 'DENTRO_REGRA';

CREATE INDEX idx_reposicao_dentro_regra_mes_loja
    ON reposicao_dentro_regra (mes, cd_loja);

CREATE INDEX idx_reposicao_fora_regra_mes_motivo
    ON reposicao_fora_regra (mes_recebimento, motivo);

CREATE INDEX idx_reposicao_fora_regra_produto
    ON reposicao_fora_regra (cd_produto);

COMMIT;

-- Validacoes:
--
-- SELECT
--     mes,
--     SUM(necessidade) AS necessidade,
--     SUM(entrada_periodo) AS entrada_periodo,
--     SUM(entrada_atrasada) AS entrada_atrasada,
--     SUM(entrada_sem_lote) AS entrada_sem_lote,
--     SUM(faltou) AS faltou
-- FROM reposicao_dentro_regra
-- GROUP BY mes
-- ORDER BY mes;
--
-- SELECT
--     mes_recebimento,
--     motivo,
--     COUNT(DISTINCT cd_loja) AS lojas,
--     COUNT(DISTINCT cd_loja || '-' || cd_produto) AS loja_skus,
--     SUM(qt_entrada) AS pecas
-- FROM reposicao_fora_regra
-- GROUP BY mes_recebimento, motivo
-- ORDER BY mes_recebimento, motivo;
