-- ============================================================
-- vw_cmv_fab_v2 - versao otimizada de vw_cmv_fab
--
-- Achado principal: vr_tra_transitem (view base usada pelo original)
-- deriva a coluna tp_modalidade chamando f_dic_ger_operacao(...) por
-- LINHA (ate ~2,5 milhoes de chamadas antes mesmo do filtro reduzir
-- para as ~1,16 milhao de linhas da CMV). Essa funcao internamente so
-- faz JOIN tra_transacao -> ger_operacao por cd_operacao. Aqui a gente
-- bypassa vr_tra_transitem e faz esse JOIN direto (mesma logica, sem
-- chamar funcao por linha).
--
-- Tambem mantem a mesma logica de cd_seqgrupo (f_dic_verifica_itemservnf
-- + f_dic_prd_cd_seqgrupo), so eliminando a chamada duplicada de
-- itemservnf que existe no original, e chamando f_dic_prd_cd_seqgrupo
-- apenas por produto distinto.
--
-- E as mesmas f_dic_prd_classificacao / f_prd_valor_produto2 do
-- vw_cmv_fab original, tambem chamadas so por valor distinto.
-- ============================================================
CREATE OR REPLACE VIEW vw_cmv_fab_v2 AS
WITH base_raw AS (
    SELECT
        i.cd_empresa,
        i.nr_transacao,
        i.dt_transacao,
        i.nr_item,
        i.cd_produto,
        i.cd_empfat,
        i.qt_solicitada,
        c.tp_situacao,
        c.tp_operacao,
        go.tp_modalidade
    FROM tra_transitem i
    LEFT JOIN tra_transacao c
           ON i.cd_empresa = c.cd_empresa
          AND i.nr_transacao = c.nr_transacao
          AND i.dt_transacao = c.dt_transacao
    LEFT JOIN ger_operacao go
           ON go.cd_operacao = c.cd_operacao
    WHERE i.cd_empfat = 1
      AND i.dt_transacao > '2025-01-01 00:00:00'::timestamp
      AND i.dt_transacao <= '2026-12-31 00:00:00'::timestamp
      AND i.cd_produto < 5000000
),
base_filtrado AS (
    SELECT
        b.dt_transacao::date AS data,
        b.cd_empfat AS idcentrocusto,
        b.nr_transacao,
        b.cd_produto AS idproduto,
        b.qt_solicitada AS qtd,
        b.cd_empresa,
        b.nr_item,
        f_dic_verifica_itemservnf(b.cd_empresa, b.nr_transacao, b.dt_transacao, b.nr_item, b.cd_produto) AS in_servico
    FROM base_raw b
    WHERE b.tp_situacao = 4
      AND b.tp_operacao::text = 'S'::text
      AND b.tp_modalidade::text = ANY (ARRAY['4', '8']::text[])
),
seqgrupo_unico AS (
    SELECT DISTINCT idproduto AS cd_produto,
           f_dic_prd_cd_seqgrupo(idproduto) AS cd_seqgrupo
    FROM base_filtrado
    WHERE in_servico = 'N'
),
classif_unica AS (
    SELECT DISTINCT idproduto AS cd_produto,
           f_dic_prd_classificacao(idproduto, 'CD'::text, 20::bigint) AS idmarca
    FROM base_filtrado
),
base AS (
    SELECT
        bf.data, bf.idcentrocusto, bf.nr_transacao, bf.idproduto, bf.qtd,
        CASE WHEN bf.in_servico = 'N' THEN sg.cd_seqgrupo ELSE NULL::bigint END AS cd_seqgrupo,
        c.idmarca
    FROM base_filtrado bf
    LEFT JOIN seqgrupo_unico sg ON sg.cd_produto = bf.idproduto
    LEFT JOIN classif_unica c ON c.cd_produto = bf.idproduto
),
valor_mp_unico AS (
    SELECT DISTINCT cd_produtomp,
           f_prd_valor_produto2(1::bigint, 1::bigint, 'C'::bpchar, 2::bigint, cd_produtomp, NULL::timestamp) AS valor
    FROM vr_pcp_fcconsumo
),
custos_mp AS (
    SELECT mp.cd_produtopa,
           sum(v.valor * mp.qt_consumo) AS customp
    FROM vr_pcp_fcconsumo mp
    JOIN valor_mp_unico v ON v.cd_produtomp = mp.cd_produtomp
    GROUP BY mp.cd_produtopa
),
custos_operacao AS (
    SELECT
        so.cd_seqgrupopa,
        sum((so.qt_operacao::numeric *
            CASE op.cd_tipooperacao
                WHEN 1 THEN 0.69
                WHEN 3 THEN 0.69
                WHEN 4 THEN 0.69
                ELSE 0::numeric
            END)::double precision *
            CASE
                WHEN so.hr_tempo > 0::numeric THEN so.hr_tempo::double precision
                ELSE op.hr_tempopadrao * 1440::double precision
            END) AS custoope,
        sum((so.qt_operacao::numeric *
            CASE op.cd_tipooperacao
                WHEN 2 THEN 0.1779
                WHEN 6 THEN 2.66
                ELSE 0::numeric
            END)::double precision *
            CASE
                WHEN so.hr_tempo > 0::numeric THEN so.hr_tempo::double precision
                ELSE op.hr_tempopadrao * 1440::double precision
            END) AS custocorte
    FROM vr_cdf_seqope so
    JOIN vr_cdf_operac op ON so.cd_operacao = op.cd_operacao
    GROUP BY so.cd_seqgrupopa
),
calc AS (
    SELECT
        b.data, b.idcentrocusto, b.nr_transacao, b.idproduto, b.qtd, b.cd_seqgrupo, b.idmarca,
        COALESCE(mp.customp, 0::double precision) AS customp,
        COALESCE(op.custoope, 0::double precision) AS custoope,
        COALESCE(op.custocorte, 0::double precision) AS custocorte
    FROM base b
    LEFT JOIN custos_mp mp ON mp.cd_produtopa = b.idproduto
    LEFT JOIN custos_operacao op ON op.cd_seqgrupopa = b.cd_seqgrupo
)
SELECT
    calc.data,
    calc.idcentrocusto,
    calc.nr_transacao,
    calc.idproduto,
    calc.idmarca,
    CASE calc.idmarca
        WHEN '0001'::text THEN '04.02.01'::text
        WHEN '0002'::text THEN '04.02.01'::text
        WHEN '0009'::text THEN '04.02.01'::text
        ELSE '04.02.02'::text
    END AS idconta,
    unp.tipo AS atributo,
    unp.valor * '-1'::integer::double precision AS valor
FROM calc
CROSS JOIN LATERAL (
    VALUES
        ('04.02.01.01'::text, calc.qtd * calc.customp),
        ('04.02.01.02'::text, calc.qtd * calc.custoope),
        ('04.02.01.03'::text, calc.qtd * calc.custocorte)
) unp(tipo, valor)
ORDER BY calc.data DESC;
