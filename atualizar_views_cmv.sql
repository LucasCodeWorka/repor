-- ============================================================
-- ATUALIZAÇÃO DAS VIEWS CMV - Range 2025 a 2026
-- ============================================================
-- Execute esses comandos no banco de dados
-- ============================================================

-- 1. vw_cmv_fab
CREATE OR REPLACE VIEW vw_cmv_fab AS
WITH base AS (
    SELECT
        g.dt_transacao::date AS data,
        g.cd_empfat AS idcentrocusto,
        g.nr_transacao,
        g.cd_produto AS idproduto,
        g.qt_solicitada AS qtd,
        g.cd_seqgrupo,
        f_dic_prd_classificacao(g.cd_produto, 'CD'::text, 20::bigint) AS idmarca
    FROM vr_tra_transitem g
    WHERE g.cd_empfat = 1
      AND g.dt_transacao > '2025-01-01 00:00:00'::timestamp  -- ALTERADO: era 2026
      AND g.dt_transacao <= '2026-12-31 00:00:00'::timestamp
      AND g.tp_situacao = 4
      AND g.tp_modalidade::text = ANY (ARRAY['4', '8']::text[])
      AND g.tp_operacao::text = 'S'::text
      AND g.cd_produto < 5000000
),
custos_mp AS (
    SELECT
        mp.cd_produtopa,
        sum(f_prd_valor_produto2(1::bigint, 1::bigint, 'P'::bpchar, 2::bigint, mp.cd_produtomp, NULL::timestamp) * mp.qt_consumo) AS customp
    FROM vr_pcp_fcconsumo mp
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
        b.data,
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


-- 2. vw_cmv_lojas
CREATE OR REPLACE VIEW vw_cmv_lojas AS
WITH base AS (
    SELECT
        t.cd_empresa AS idcentrodecusto,
        t.nr_transacao,
        t.dt_transacao AS data,
        i.qt_solicitada,
        i.cd_produto AS idproduto,
        t.tp_operacao,
        f_dic_prd_classificacao(i.cd_produto, 'CD'::text, 20::bigint) AS idmarca,
        f_dic_prd_classificacao(i.cd_produto, 'CD'::text, 27::bigint) AS idstatus,
        CASE
            WHEN f_dic_prd_classificacao(i.cd_produto, 'CD'::text, 20::bigint)::text = ANY (ARRAY['0001', '0002', '0009']::text[]) THEN
                CASE
                    WHEN f_prd_valor_produto2(1::bigint, 1::bigint, 'P'::bpchar, 1::bigint, i.cd_produto, t.dt_transacao) >= 0.1
                     AND f_prd_valor_produto2(1::bigint, 1::bigint, 'P'::bpchar, 1::bigint, i.cd_produto, t.dt_transacao) <= 1000
                    THEN f_prd_valor_produto2(1::bigint, 1::bigint, 'P'::bpchar, 1::bigint, i.cd_produto, t.dt_transacao)
                    WHEN f_prd_valor_produto2(1::bigint, 1::bigint, 'P'::bpchar, 1::bigint, i.cd_produto, NULL::timestamp) >= 1000
                      OR f_prd_valor_produto2(1::bigint, 1::bigint, 'P'::bpchar, 1::bigint, i.cd_produto, NULL::timestamp) <= 0.1
                    THEN 21.9
                    ELSE f_prd_valor_produto2(1::bigint, 1::bigint, 'P'::bpchar, 1::bigint, i.cd_produto, NULL::timestamp)
                END
            ELSE
                CASE
                    WHEN f_prd_valor_produto2(1::bigint, 1::bigint, 'C'::bpchar, 2::bigint, i.cd_produto, t.dt_transacao) >= 0.1
                     AND f_prd_valor_produto2(1::bigint, 1::bigint, 'C'::bpchar, 2::bigint, i.cd_produto, t.dt_transacao) <= 1000
                    THEN f_prd_valor_produto2(1::bigint, 1::bigint, 'C'::bpchar, 2::bigint, i.cd_produto, t.dt_transacao)
                    WHEN f_prd_valor_produto2(1::bigint, 1::bigint, 'C'::bpchar, 2::bigint, i.cd_produto, NULL::timestamp) >= 1000
                      OR f_prd_valor_produto2(1::bigint, 1::bigint, 'C'::bpchar, 2::bigint, i.cd_produto, NULL::timestamp) <= 0.1
                    THEN 21.9
                    ELSE f_prd_valor_produto2(1::bigint, 1::bigint, 'C'::bpchar, 2::bigint, i.cd_produto, NULL::timestamp)
                END
        END AS valor_unitario
    FROM vr_tra_transacao t
    JOIN vr_tra_transitem i ON t.nr_transacao = i.nr_transacao AND t.cd_empresa = i.cd_empresa
    WHERE (
            (t.tp_modalidade::text = ANY (ARRAY['4', '8']::text[]) AND t.tp_operacao::text = 'S')
            OR (t.tp_modalidade::text = '3' AND t.tp_operacao::text = 'E')
          )
      AND t.dt_transacao >= '2025-01-01 00:00:00'::timestamp  -- ALTERADO: era 2026
      AND t.dt_transacao <= '2026-12-31 00:00:00'::timestamp  -- ALTERADO: era 2026-01-31
      AND t.cd_empresa <> ALL (ARRAY[1::bigint, 50::bigint])
      AND t.tp_situacao = 4
),
calc1 AS (
    SELECT
        base.idcentrodecusto,
        base.nr_transacao,
        base.data,
        base.qt_solicitada,
        base.idproduto,
        base.tp_operacao,
        base.idmarca,
        base.idstatus,
        base.valor_unitario,
        base.qt_solicitada * base.valor_unitario *
            CASE WHEN base.tp_operacao::text = 'S' THEN -1 ELSE 1 END::double precision AS valor_mov
    FROM base
    WHERE base.idmarca IS NOT NULL AND base.idmarca::text <> ''
),
calc2 AS (
    SELECT
        calc1.idcentrodecusto,
        calc1.nr_transacao,
        calc1.data,
        calc1.qt_solicitada,
        calc1.idproduto,
        calc1.tp_operacao,
        calc1.idmarca,
        calc1.idstatus,
        calc1.valor_unitario,
        calc1.valor_mov,
        CASE WHEN calc1.idmarca::text = ANY (ARRAY['0001', '0002', '0009']::text[]) THEN '04.02.01' ELSE '04.02.02' END AS idconta,
        CASE WHEN calc1.idcentrodecusto = 2 THEN 1 ELSE 2 END AS emp,
        CASE
            WHEN calc1.idstatus::text = ANY (ARRAY['0001', '0002', '0004', '0006', '0009', '0011']::text[]) THEN 1
            WHEN calc1.idstatus::text = '0010' THEN 3
            ELSE 2
        END AS st
    FROM calc1
),
calc3 AS (
    SELECT
        calc2.*,
        calc2.emp::text || calc2.st::text AS var
    FROM calc2
)
SELECT
    calc3.idconta,
    calc3.idcentrodecusto,
    calc3.data,
    calc3.valor_mov *
        CASE WHEN calc3.var = ANY (ARRAY['11', '12', '13']::text[]) THEN 0.7 ELSE 0.8 END::double precision AS valor
FROM calc3;


-- 3. vr_cmv_lojas
CREATE OR REPLACE VIEW vr_cmv_lojas AS
WITH base AS (
    SELECT
        t.cd_empresa AS idcentrodecusto,
        t.nr_transacao,
        t.dt_transacao AS data,
        i.qt_solicitada,
        i.cd_produto AS idproduto,
        t.tp_operacao,
        f_dic_prd_classificacao(i.cd_produto, 'CD'::text, 20::bigint) AS idmarca,
        f_dic_prd_classificacao(i.cd_produto, 'CD'::text, 27::bigint) AS idstatus,
        CASE
            WHEN f_dic_prd_classificacao(i.cd_produto, 'CD'::text, 20::bigint)::text = ANY (ARRAY['0001', '0002', '0009']::text[]) THEN
                CASE
                    WHEN f_prd_valor_produto2(1::bigint, 1::bigint, 'P'::bpchar, 1::bigint, i.cd_produto, t.dt_transacao) >= 0.1
                     AND f_prd_valor_produto2(1::bigint, 1::bigint, 'P'::bpchar, 1::bigint, i.cd_produto, t.dt_transacao) <= 1000
                    THEN f_prd_valor_produto2(1::bigint, 1::bigint, 'P'::bpchar, 1::bigint, i.cd_produto, t.dt_transacao)
                    WHEN f_prd_valor_produto2(1::bigint, 1::bigint, 'P'::bpchar, 1::bigint, i.cd_produto, NULL::timestamp) >= 1000
                      OR f_prd_valor_produto2(1::bigint, 1::bigint, 'P'::bpchar, 1::bigint, i.cd_produto, NULL::timestamp) <= 0.1
                    THEN 21.9
                    ELSE f_prd_valor_produto2(1::bigint, 1::bigint, 'P'::bpchar, 1::bigint, i.cd_produto, NULL::timestamp)
                END
            ELSE
                CASE
                    WHEN f_prd_valor_produto2(1::bigint, 1::bigint, 'C'::bpchar, 2::bigint, i.cd_produto, t.dt_transacao) >= 0.1
                     AND f_prd_valor_produto2(1::bigint, 1::bigint, 'C'::bpchar, 2::bigint, i.cd_produto, t.dt_transacao) <= 1000
                    THEN f_prd_valor_produto2(1::bigint, 1::bigint, 'C'::bpchar, 2::bigint, i.cd_produto, t.dt_transacao)
                    WHEN f_prd_valor_produto2(1::bigint, 1::bigint, 'C'::bpchar, 2::bigint, i.cd_produto, NULL::timestamp) >= 1000
                      OR f_prd_valor_produto2(1::bigint, 1::bigint, 'C'::bpchar, 2::bigint, i.cd_produto, NULL::timestamp) <= 0.1
                    THEN 21.9
                    ELSE f_prd_valor_produto2(1::bigint, 1::bigint, 'C'::bpchar, 2::bigint, i.cd_produto, NULL::timestamp)
                END
        END AS valor_unitario
    FROM vr_tra_transacao t
    JOIN vr_tra_transitem i ON t.nr_transacao = i.nr_transacao AND t.cd_empresa = i.cd_empresa
    WHERE (
            (t.tp_modalidade::text = ANY (ARRAY['4', '8']::text[]) AND t.tp_operacao::text = 'S')
            OR (t.tp_modalidade::text = '3' AND t.tp_operacao::text = 'E')
          )
      AND t.dt_transacao >= '2025-01-01 00:00:00'::timestamp  -- ALTERADO: era 2026
      AND t.dt_transacao <= '2026-12-31 00:00:00'::timestamp
      AND t.cd_empresa <> ALL (ARRAY[1::bigint, 50::bigint])
      AND t.tp_situacao = 4
),
calc1 AS (
    SELECT
        base.idcentrodecusto,
        base.nr_transacao,
        base.data,
        base.qt_solicitada,
        base.idproduto,
        base.tp_operacao,
        base.idmarca,
        base.idstatus,
        base.valor_unitario,
        base.qt_solicitada * base.valor_unitario *
            CASE WHEN base.tp_operacao::text = 'S' THEN -1 ELSE 1 END::double precision AS valor_mov
    FROM base
    WHERE base.idmarca IS NOT NULL AND base.idmarca::text <> ''
),
calc2 AS (
    SELECT
        calc1.idcentrodecusto,
        calc1.nr_transacao,
        calc1.data,
        calc1.qt_solicitada,
        calc1.idproduto,
        calc1.tp_operacao,
        calc1.idmarca,
        calc1.idstatus,
        calc1.valor_unitario,
        calc1.valor_mov,
        CASE WHEN calc1.idmarca::text = ANY (ARRAY['0001', '0002', '0009']::text[]) THEN '04.02.01' ELSE '04.02.02' END AS idconta,
        CASE WHEN calc1.idcentrodecusto = 2 THEN 1 ELSE 2 END AS emp,
        CASE
            WHEN calc1.idstatus::text = ANY (ARRAY['0001', '0002', '0004', '0006', '0009', '0011']::text[]) THEN 1
            WHEN calc1.idstatus::text = '0010' THEN 3
            ELSE 2
        END AS st
    FROM calc1
),
calc3 AS (
    SELECT
        calc2.*,
        calc2.emp::text || calc2.st::text AS var
    FROM calc2
)
SELECT
    calc3.idconta,
    calc3.idcentrodecusto,
    calc3.data,
    calc3.valor_mov *
        CASE WHEN calc3.var = ANY (ARRAY['11', '12', '13']::text[]) THEN 0.7 ELSE 0.8 END::double precision AS valor
FROM calc3;
