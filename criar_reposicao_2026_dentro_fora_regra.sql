-- Cria duas tabelas para auditar a reposicao permanente de 2026.
--
-- Tabela 1: reposicao_2026_dentro_regra
--   Grao: mes + loja + produto da base de demanda.
--   Mede somente o que deveria contar para reposicao do periodo:
--     origem fabrica (cd_empresaori = 1) + lote do proprio mes.
--
-- Tabela 2: reposicao_2026_fora_regra
--   Grao: recebimento + loja + produto.
--   Lista tudo que nao deve cumprir a regra principal:
--     origem nao fabrica, fabrica sem lote, fabrica atrasada com lote antigo,
--     ou fabrica do periodo recebida para produto/loja fora da base de demanda.

BEGIN;

DROP TABLE IF EXISTS reposicao_2026_dentro_regra;
DROP TABLE IF EXISTS reposicao_2026_fora_regra;

CREATE TABLE reposicao_2026_dentro_regra AS
WITH meses AS (
    SELECT
        to_char(mes_inicio, 'YYYY-MM') AS mes,
        mes_inicio::date AS inicio_mes,
        (mes_inicio + INTERVAL '1 month')::date AS fim_mes,
        to_char(mes_inicio, 'YY.MM') || '%' AS lote_periodo
    FROM generate_series(
        '2026-01-01'::date,
        '2026-12-01'::date,
        INTERVAL '1 month'
    ) AS mes_inicio
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

vendas_3m AS (
    SELECT
        m.mes,
        m.inicio_mes,
        m.lote_periodo,
        t.cd_empresa AS cd_loja,
        i.cd_produto,
        SUM(
            i.qt_solicitada *
            CASE WHEN t.tp_modalidade::text = '3' THEN -1 ELSE 1 END
        ) AS vendas_3m
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
    GROUP BY m.mes, m.inicio_mes, m.lote_periodo, t.cd_empresa, i.cd_produto
    HAVING SUM(
        i.qt_solicitada *
        CASE WHEN t.tp_modalidade::text = '3' THEN -1 ELSE 1 END
    ) > 0
),

base_demanda_sem_saldo AS (
    SELECT
        v.mes,
        v.inicio_mes,
        v.lote_periodo,
        v.cd_loja,
        emp.nm_grupoempresa AS nome_loja,
        v.cd_produto,
        f_dic_prd_nivel(v.cd_produto, 'CD'::bpchar) AS referencia,
        f_dic_prd_nivel(v.cd_produto, 'DS'::bpchar) AS descricao_produto,
        v.vendas_3m,
        ROUND(v.vendas_3m / 3.0, 2) AS media_mensal,
        ROUND(v.vendas_3m / 3.0 * 1.5, 0) AS estoque_minimo
    FROM vendas_3m v
    JOIN vr_ger_empresa emp
        ON emp.cd_empresa = v.cd_loja
),

saldos_iniciais AS (
    SELECT DISTINCT ON (b.mes, b.cd_loja, b.cd_produto)
        b.mes,
        b.cd_loja,
        b.cd_produto,
        COALESCE(s.qt_saldo, 0) AS saldo_inicial
    FROM base_demanda_sem_saldo b
    LEFT JOIN prd_prdsaldo s
        ON s.cd_empresa = b.cd_loja
        AND s.cd_produto = b.cd_produto
        AND s.cd_saldo = 1
        AND s.dt_saldo <= b.inicio_mes
    ORDER BY b.mes, b.cd_loja, b.cd_produto, s.dt_saldo DESC
),

base_demanda AS (
    SELECT
        b.*,
        COALESCE(abc.curva_completa, 'SEM CURVA') AS curva_completa,
        COALESCE(s.saldo_inicial, 0) AS saldo_inicial
    FROM base_demanda_sem_saldo b
    LEFT JOIN saldos_iniciais s
        ON s.mes = b.mes
        AND s.cd_loja = b.cd_loja
        AND s.cd_produto = b.cd_produto
    LEFT JOIN curva_abc abc
        ON abc.referencia = b.referencia
),

entradas_validas AS (
    SELECT
        m.mes,
        t.cd_empresa AS cd_loja,
        i.cd_produto,
        SUM(i.qt_solicitada) AS entrada_periodo,
        COUNT(DISTINCT t.nr_transacao) AS qtd_transacoes_periodo,
        MIN(i.dt_transacao) AS primeira_entrada_periodo,
        MAX(i.dt_transacao) AS ultima_entrada_periodo,
        STRING_AGG(DISTINCT lote.cd_lote, ', ' ORDER BY lote.cd_lote) AS lotes_periodo
    FROM meses m
    JOIN vr_tra_transacao t
        ON TRUE
    JOIN vr_tra_transitem i
        ON t.nr_transacao = i.nr_transacao
        AND t.cd_empresa = i.cd_empresa
    JOIN vr_ped_pedidotra ped
        ON ped.nr_transacao = t.nr_transacaoori
    JOIN vr_ped_pedidoc2 lote
        ON ped.cd_emppedido = lote.cd_empresa
        AND ped.cd_pedido = lote.cd_pedido
        AND ped.cd_representant = lote.cd_representant
        AND lote.cd_lote LIKE m.lote_periodo
    WHERE t.cd_empresa > 1
      AND t.cd_empresa <> 4
      AND t.cd_empresaori = 1
      AND t.tp_operacao = 'E'
      AND t.tp_modalidade::text = '2'
      AND t.tp_situacao = 4
      AND i.dt_transacao >= m.inicio_mes
      AND i.dt_transacao < m.fim_mes
    GROUP BY m.mes, t.cd_empresa, i.cd_produto
)

SELECT
    b.mes,
    b.cd_loja,
    b.nome_loja,
    b.cd_produto,
    b.referencia,
    b.descricao_produto,
    b.curva_completa,
    b.vendas_3m,
    b.media_mensal,
    b.estoque_minimo,
    b.saldo_inicial,
    GREATEST(0, b.estoque_minimo - b.saldo_inicial) AS necessidade,
    COALESCE(e.entrada_periodo, 0) AS entrada_periodo,
    GREATEST(0, GREATEST(0, b.estoque_minimo - b.saldo_inicial) - COALESCE(e.entrada_periodo, 0)) AS faltou_periodo,
    GREATEST(0, COALESCE(e.entrada_periodo, 0) - GREATEST(0, b.estoque_minimo - b.saldo_inicial)) AS sobra_periodo,
    COALESCE(e.qtd_transacoes_periodo, 0) AS qtd_transacoes_periodo,
    e.primeira_entrada_periodo,
    e.ultima_entrada_periodo,
    e.lotes_periodo,
    CASE
        WHEN GREATEST(0, b.estoque_minimo - b.saldo_inicial) <= 0 THEN 'SEM NECESSIDADE'
        WHEN COALESCE(e.entrada_periodo, 0) >= GREATEST(0, b.estoque_minimo - b.saldo_inicial) THEN 'OK'
        WHEN COALESCE(e.entrada_periodo, 0) > 0 THEN 'PARCIAL'
        ELSE 'ZERADO'
    END AS status_reposicao
FROM base_demanda b
LEFT JOIN entradas_validas e
    ON b.mes = e.mes
    AND b.cd_loja = e.cd_loja
    AND b.cd_produto = e.cd_produto;

CREATE TABLE reposicao_2026_fora_regra AS
WITH meses AS (
    SELECT
        to_char(mes_inicio, 'YYYY-MM') AS mes,
        mes_inicio::date AS inicio_mes,
        (mes_inicio + INTERVAL '1 month')::date AS fim_mes,
        to_char(mes_inicio, 'YY.MM') || '%' AS lote_periodo
    FROM generate_series(
        '2026-01-01'::date,
        '2026-12-01'::date,
        INTERVAL '1 month'
    ) AS mes_inicio
),

base_demanda AS (
    SELECT DISTINCT mes, cd_loja, cd_produto
    FROM reposicao_2026_dentro_regra
),

entradas_recebidas AS (
    SELECT
        m.mes AS mes_recebimento,
        m.lote_periodo,
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

CREATE INDEX idx_reposicao_2026_dentro_mes_loja
    ON reposicao_2026_dentro_regra (mes, cd_loja);

CREATE INDEX idx_reposicao_2026_dentro_produto
    ON reposicao_2026_dentro_regra (cd_produto);

CREATE INDEX idx_reposicao_2026_fora_mes_motivo
    ON reposicao_2026_fora_regra (mes_recebimento, motivo);

CREATE INDEX idx_reposicao_2026_fora_produto
    ON reposicao_2026_fora_regra (cd_produto);

COMMIT;

-- Validacoes:
--
-- SELECT
--     mes,
--     SUM(necessidade) AS necessidade,
--     SUM(entrada_periodo) AS entrada_periodo,
--     SUM(faltou_periodo) AS faltou_periodo
-- FROM reposicao_2026_dentro_regra
-- GROUP BY mes
-- ORDER BY mes;
--
-- SELECT
--     mes_recebimento,
--     motivo,
--     COUNT(DISTINCT cd_loja) AS lojas,
--     COUNT(DISTINCT cd_loja || '-' || cd_produto) AS loja_skus,
--     SUM(qt_entrada) AS pecas
-- FROM reposicao_2026_fora_regra
-- GROUP BY mes_recebimento, motivo
-- ORDER BY mes_recebimento, motivo;
