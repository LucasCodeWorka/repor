"""
Query de vw_cmv_fab com janela de data parametrizavel, usada tanto pela
migracao (criar_tabela_cmv_fab.py) quanto pelo refresh incremental
(refresh_cmv_fab.py).

Diferenca pra view original: alem do %(corte)s no filtro de data, os CTEs
de custo (custos_mp / custos_operacao) sao restritos aos produtos/seqgrupos
que aparecem na janela. Na view eles agregavam a base inteira de
vr_pcp_fcconsumo / vr_cdf_seqope a cada execucao -- com f_prd_valor_produto2
chamada por linha, era isso que fazia o REFRESH levar ~6h. Como os dois
entram por LEFT JOIN nessas mesmas chaves, restringir nao muda o resultado.
"""

CMV_FAB_SQL = """
WITH base AS (
    SELECT g.dt_transacao::date AS data,
        g.cd_empfat AS idcentrocusto,
        g.nr_transacao,
        g.cd_produto AS idproduto,
        g.qt_solicitada AS qtd,
        g.cd_seqgrupo,
        f_dic_prd_classificacao(g.cd_produto, 'CD'::text, 20::bigint) AS idmarca
    FROM vr_tra_transitem g
    WHERE g.cd_empfat = 1
      AND g.dt_transacao >= %(corte)s::timestamp
      AND g.dt_transacao <= '2026-12-31 00:00:00'::timestamp
      AND g.tp_situacao = 4
      AND g.tp_modalidade::text = ANY (ARRAY['4'::text, '8'::text])
      AND g.tp_operacao::text = 'S'::text
      AND g.cd_produto < 5000000
), custos_mp AS (
    SELECT mp.cd_produtopa,
        sum(f_prd_valor_produto2(1::bigint, 1::bigint, 'C'::bpchar, 2::bigint, mp.cd_produtomp, NULL::timestamp without time zone) * mp.qt_consumo) AS customp
    FROM vr_pcp_fcconsumo mp
    WHERE mp.cd_produtopa IN (SELECT DISTINCT idproduto FROM base)
    GROUP BY mp.cd_produtopa
), custos_operacao AS (
    SELECT so.cd_seqgrupopa,
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
    WHERE so.cd_seqgrupopa IN (SELECT DISTINCT cd_seqgrupo FROM base)
    GROUP BY so.cd_seqgrupopa
), calc AS (
    SELECT b.data,
        b.idcentrocusto,
        b.nr_transacao,
        b.idproduto,
        b.qtd,
        b.cd_seqgrupo,
        b.idmarca,
        COALESCE(mp.customp, 0::double precision) AS customp,
        COALESCE(op.custoope, 0::double precision) AS custoope,
        COALESCE(op.custocorte, 0::double precision) AS custocorte
    FROM base b
    LEFT JOIN custos_mp mp ON mp.cd_produtopa = b.idproduto
    LEFT JOIN custos_operacao op ON op.cd_seqgrupopa = b.cd_seqgrupo
)
SELECT calc.data,
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
CROSS JOIN LATERAL ( VALUES
    ('04.02.01.01'::text, calc.qtd * calc.customp),
    ('04.02.01.02'::text, calc.qtd * calc.custoope),
    ('04.02.01.03'::text, calc.qtd * calc.custocorte)
) unp(tipo, valor)
"""
