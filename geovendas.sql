 SELECT 1 AS codempresa,
    f_dic_prd_nivel(a.cd_produto, 'CD'::bpchar) AS cd_nivel,
    a.cd_produto AS codigoproduto,
    a.cd_tamanho AS seqtamanho,
    a.cd_cor AS seqsortimento,
    f_dic_prd_classificacao(a.cd_produto, 'CD'::text, (21)::bigint) AS colecao,
    1 AS estoquelimitado,is
    
        CASE
            WHEN (((f_dic_prd_classificacao(a.cd_produto, 'CD'::text, (27)::bigint))::text = ANY (ARRAY[('0008'::character varying)::text, ('0007'::character varying)::text, ('0003'::character varying)::text])) AND (((COALESCE(f_prd_saldo_produto((1)::bigint, (1)::bigint, a.cd_produto, NULL::timestamp without time zone), (0)::double precision) - COALESCE(( SELECT COALESCE(sum(aaa.qt_pendente), (0)::double precision) AS sum
               FROM vr_ped_pedidoi aaa
              WHERE ((aaa.cd_produto = a.cd_produto) AND (aaa.cd_operacao <> (44)::bigint) AND (aaa.cd_empresa = (1)::bigint) AND (aaa.tp_situacao <> (6)::bigint))), (0)::double precision)) + f_prd_saldo_produto((1)::bigint, (7)::bigint, a.cd_produto, NULL::timestamp without time zone)) <= (2)::double precision)) THEN (0)::double precision
            ELSE (((COALESCE(f_prd_saldo_produto((1)::bigint, (1)::bigint, a.cd_produto, NULL::timestamp without time zone), (0)::double precision) - COALESCE(( SELECT COALESCE(sum(aaa.qt_pendente), (0)::double precision) AS sum
               FROM vr_ped_pedidoi aaa
              WHERE ((aaa.cd_produto = a.cd_produto) AND (aaa.cd_operacao <> (44)::bigint) AND (aaa.cd_empresa = (1)::bigint) AND (aaa.tp_situacao <> (6)::bigint))), (0)::double precision)) + f_prd_saldo_produto((1)::bigint, (7)::bigint, a.cd_produto, NULL::timestamp without time zone)) + COALESCE(( SELECT sum((COALESCE(aa.qt_real, (0)::double precision) - COALESCE(aa.qt_finalizada, (0)::double precision))) AS sum
               FROM vr_pcp_opi aa,
                vr_pcp_opc bb
              WHERE ((aa.cd_empresa = 1) AND (aa.cd_produto = a.cd_produto) AND (((f_dic_prd_classificacao(a.cd_produto, 'CD'::text, (124)::bigint))::text = ANY (ARRAY[('001'::character varying)::text, ('002'::character varying)::text, ('004'::character varying)::text, ('005'::character varying)::text])) OR (f_dic_prd_classificacao(a.cd_produto, 'CD'::text, (124)::bigint) IS NULL)) AND (aa.cd_empresa = bb.cd_empresa) AND (aa.nr_ciclo = bb.nr_ciclo) AND (aa.nr_op = bb.nr_op) AND (COALESCE(bb.cd_categoria, (0)::bigint) <> 15) AND (aa.tp_situacao = ANY (ARRAY[(5)::bigint, (10)::bigint, (15)::bigint, (20)::bigint])))), (0)::double precision))
        END AS quantidade,
    a.ds_tamanho AS codtamanho,
    NULL::text AS "Código do depósito",
    f_dic_prd_classificacao(a.cd_produto, 'DS'::text, (21)::bigint) AS nomecolecao,
    (CURRENT_DATE + 30) AS dataproduto,
    (((COALESCE(f_prd_saldo_produto((1)::bigint, (1)::bigint, a.cd_produto, NULL::timestamp without time zone), (0)::double precision) - COALESCE(( SELECT COALESCE(sum(aaa.qt_pendente), (0)::double precision) AS sum
           FROM vr_ped_pedidoi aaa
          WHERE ((aaa.cd_produto = a.cd_produto) AND (aaa.cd_operacao <> (44)::bigint) AND (aaa.cd_empresa = (1)::bigint) AND (aaa.tp_situacao <> (6)::bigint))), (0)::double precision)) + f_prd_saldo_produto((1)::bigint, (7)::bigint, a.cd_produto, NULL::timestamp without time zone)) + COALESCE(( SELECT sum((COALESCE(aa.qt_real, (0)::double precision) - COALESCE(aa.qt_finalizada, (0)::double precision))) AS sum
           FROM vr_pcp_opi aa,
            vr_pcp_opc bb,
            prd_produtoclas cc
          WHERE ((aa.cd_empresa = 1) AND (bb.dt_inclusao <= '2026-05-19 00:00:00'::timestamp without time zone) AND (aa.cd_produto = cc.cd_produto) AND (cc.cd_tipoclas = 802) AND ((cc.cd_classificacao)::text = '2         '::text) AND (aa.cd_produto = a.cd_produto) AND (((f_dic_prd_classificacao(a.cd_produto, 'CD'::text, (124)::bigint))::text = ANY (ARRAY[('001'::character varying)::text, ('002'::character varying)::text, ('004'::character varying)::text, ('005'::character varying)::text])) OR (f_dic_prd_classificacao(a.cd_produto, 'CD'::text, (124)::bigint) IS NULL)) AND (aa.cd_empresa = bb.cd_empresa) AND (aa.nr_ciclo = bb.nr_ciclo) AND (aa.nr_op = bb.nr_op) AND (COALESCE(bb.cd_categoria, (0)::bigint) <> 15) AND (aa.tp_situacao = ANY (ARRAY[(5)::bigint, (10)::bigint, (15)::bigint, (20)::bigint])))), (0)::double precision)) AS quantidadeprontaentrega,
    a.cd_cor AS codcorbase,
    f_dic_prd_nivel(a.cd_produto, 'DS'::bpchar) AS nm_produto,
    a.ds_cor AS nomecor,
    f_dic_prd_codigobarra(a.cd_produto) AS ean13,
    NULL::text AS visualquantidadeproduto,
    NULL::text AS visualquantidadeproducao,
    a.cd_tamanho AS seqordenacaotamanho
   FROM vr_prd_prdgrade a,
    vr_prd_prdinfo b
  WHERE ((b.cd_produto = a.cd_produto) AND (((f_dic_prd_classificacao(a.cd_produto, 'CD'::text, (124)::bigint))::text = ANY (ARRAY[('001'::character varying)::text, ('002'::character varying)::text, ('007'::character varying)::text, ('004'::character varying)::text, ('005'::character varying)::text])) OR (f_dic_prd_classificacao(a.cd_produto, 'CD'::text, (124)::bigint) IS NULL)) AND ((b.in_inativo)::text = 'F'::text) AND ((a.cd_cor)::text <> 'LF        '::text) AND (b.cd_empresa = 1) AND (b.cd_produto = a.cd_produto) AND ((f_dic_prd_classificacao(a.cd_produto, 'CD'::text, (20)::bigint))::text = ANY (ARRAY[('0001'::character varying)::text, ('0002'::character varying)::text, ('0003'::character varying)::text, ('0020'::character varying)::text, ('0009'::character varying)::text])) AND ((a.cd_produto < 1000000) OR (a.cd_produto = ANY (ARRAY[(5001609)::bigint, (5001610)::bigint, (5001319)::bigint, (5001611)::bigint]))) AND (
        CASE
            WHEN (((f_dic_prd_classificacao(a.cd_produto, 'CD'::text, (27)::bigint))::text = ANY (ARRAY[('0008'::character varying)::text, ('0007'::character varying)::text, ('0003'::character varying)::text])) AND (((COALESCE(f_prd_saldo_produto((1)::bigint, (1)::bigint, a.cd_produto, NULL::timestamp without time zone), (0)::double precision) - COALESCE(( SELECT COALESCE(sum(aaa.qt_pendente), (0)::double precision) AS sum
               FROM vr_ped_pedidoi aaa
              WHERE ((aaa.cd_produto = a.cd_produto) AND (aaa.cd_operacao <> (44)::bigint) AND (aaa.cd_empresa = (1)::bigint) AND (aaa.tp_situacao <> (6)::bigint))), (0)::double precision)) + f_prd_saldo_produto((1)::bigint, (7)::bigint, a.cd_produto, NULL::timestamp without time zone)) <= (2)::double precision)) THEN (0)::double precision
            ELSE (((((COALESCE(f_prd_saldo_produto((1)::bigint, (1)::bigint, a.cd_produto, NULL::timestamp without time zone), (0)::double precision) - COALESCE(( SELECT COALESCE(sum(aaa.qt_pendente), (0)::double precision) AS sum
               FROM vr_ped_pedidoi aaa
              WHERE ((aaa.cd_produto = a.cd_produto) AND (aaa.cd_operacao <> (44)::bigint) AND (aaa.cd_empresa = (1)::bigint) AND (aaa.tp_situacao <> (6)::bigint))), (0)::double precision)) + f_prd_saldo_produto((1)::bigint, (7)::bigint, a.cd_produto, NULL::timestamp without time zone)) + COALESCE(( SELECT sum((COALESCE(aa.qt_real, (0)::double precision) - COALESCE(aa.qt_finalizada, (0)::double precision))) AS sum
               FROM vr_pcp_opi aa,
                vr_pcp_opc bb
              WHERE ((aa.cd_empresa = 1) AND (aa.cd_produto = a.cd_produto) AND (((f_dic_prd_classificacao(a.cd_produto, 'CD'::text, (124)::bigint))::text = ANY (ARRAY[('001'::character varying)::text, ('002'::character varying)::text, ('004'::character varying)::text, ('005'::character varying)::text])) OR (f_dic_prd_classificacao(a.cd_produto, 'CD'::text, (124)::bigint) IS NULL)) AND (aa.cd_empresa = bb.cd_empresa) AND (aa.nr_ciclo = bb.nr_ciclo) AND (aa.nr_op = bb.nr_op) AND (COALESCE(bb.cd_categoria, (0)::bigint) <> 15) AND (aa.tp_situacao = ANY (ARRAY[(5)::bigint, (10)::bigint, (15)::bigint, (20)::bigint])))), (0)::double precision)) + COALESCE(( SELECT COALESCE(sum(GREATEST((b_1.qt_lote - COALESCE(b_1.qt_gerouop, (0)::double precision)), (0)::double precision)), (0)::double precision) AS sum
               FROM (vr_pcp_lotepl2 b_1
                 LEFT JOIN pcp_lotepv p ON ((b_1.nr_lote = p.nr_lote)))
              WHERE (((p.cd_auxiliar)::text = ANY (ARRAY['MA'::text, 'MG'::text])) AND (b_1.cd_produto = a.cd_produto))), (0)::double precision)) + COALESCE(( SELECT COALESCE(sum(GREATEST((b_1.qt_lote - COALESCE(b_1.qt_gerouop, (0)::double precision)), (0)::double precision)), (0)::double precision) AS sum
               FROM (vr_pcp_lotepl2 b_1
                 LEFT JOIN pcp_lotepv p ON ((b_1.nr_lote = p.nr_lote)))
              WHERE (((p.cd_auxiliar)::text = ANY (ARRAY['PX'::text])) AND (b_1.cd_produto = a.cd_produto))), (0)::double precision))
        END > (0)::double precision))
UNION ALL
 SELECT 1 AS codempresa,
    f_dic_prd_nivel(a.cd_produto, 'CD'::bpchar) AS cd_nivel,
    a.cd_produto AS codigoproduto,
    a.cd_tamanho AS seqtamanho,
    a.cd_cor AS seqsortimento,
    f_dic_prd_classificacao(a.cd_produto, 'CD'::text, (21)::bigint) AS colecao,
    1 AS estoquelimitado,
        CASE
            WHEN (((f_dic_prd_classificacao(a.cd_produto, 'CD'::text, (27)::bigint))::text = ANY (ARRAY[('0008'::character varying)::text, ('0007'::character varying)::text, ('0003'::character varying)::text])) AND (((COALESCE(f_prd_saldo_produto((1)::bigint, (1)::bigint, a.cd_produto, NULL::timestamp without time zone), (0)::double precision) - COALESCE(( SELECT COALESCE(sum(aaa.qt_pendente), (0)::double precision) AS sum
               FROM vr_ped_pedidoi aaa
              WHERE ((aaa.cd_produto = a.cd_produto) AND (aaa.cd_operacao <> (44)::bigint) AND (aaa.cd_empresa = (1)::bigint) AND (aaa.tp_situacao <> (6)::bigint))), (0)::double precision)) + f_prd_saldo_produto((1)::bigint, (7)::bigint, a.cd_produto, NULL::timestamp without time zone)) <= (2)::double precision)) THEN (0)::double precision
            ELSE (((((COALESCE(f_prd_saldo_produto((1)::bigint, (1)::bigint, a.cd_produto, NULL::timestamp without time zone), (0)::double precision) - COALESCE(( SELECT COALESCE(sum(aaa.qt_pendente), (0)::double precision) AS sum
               FROM vr_ped_pedidoi aaa
              WHERE ((aaa.cd_produto = a.cd_produto) AND (aaa.cd_operacao <> (44)::bigint) AND (aaa.cd_empresa = (1)::bigint) AND (aaa.tp_situacao <> (6)::bigint))), (0)::double precision)) + f_prd_saldo_produto((1)::bigint, (7)::bigint, a.cd_produto, NULL::timestamp without time zone)) + COALESCE(( SELECT sum((COALESCE(aa.qt_real, (0)::double precision) - COALESCE(aa.qt_finalizada, (0)::double precision))) AS sum
               FROM vr_pcp_opi aa,
                vr_pcp_opc bb
              WHERE ((aa.cd_empresa = 1) AND (aa.cd_produto = a.cd_produto) AND (((f_dic_prd_classificacao(a.cd_produto, 'CD'::text, (124)::bigint))::text = ANY (ARRAY[('001'::character varying)::text, ('002'::character varying)::text, ('004'::character varying)::text, ('005'::character varying)::text])) OR (f_dic_prd_classificacao(a.cd_produto, 'CD'::text, (124)::bigint) IS NULL)) AND (aa.cd_empresa = bb.cd_empresa) AND (aa.nr_ciclo = bb.nr_ciclo) AND (aa.nr_op = bb.nr_op) AND (COALESCE(bb.cd_categoria, (0)::bigint) <> 15) AND (aa.tp_situacao = ANY (ARRAY[(5)::bigint, (10)::bigint, (15)::bigint, (20)::bigint])))), (0)::double precision)) + COALESCE(( SELECT COALESCE(sum(GREATEST((b_1.qt_lote - COALESCE(b_1.qt_gerouop, (0)::double precision)), (0)::double precision)), (0)::double precision) AS sum
               FROM (vr_pcp_lotepl2 b_1
                 LEFT JOIN pcp_lotepv p ON ((b_1.nr_lote = p.nr_lote)))
              WHERE (((p.cd_auxiliar)::text = ANY (ARRAY['MA'::text, 'MG'::text])) AND (b_1.cd_produto = a.cd_produto))), (0)::double precision)) + COALESCE(( SELECT COALESCE(sum(GREATEST((b_1.qt_lote - COALESCE(b_1.qt_gerouop, (0)::double precision)), (0)::double precision)), (0)::double precision) AS sum
               FROM (vr_pcp_lotepl2 b_1
                 LEFT JOIN pcp_lotepv p ON ((b_1.nr_lote = p.nr_lote)))
              WHERE (((p.cd_auxiliar)::text = 'PX'::text) AND (b_1.cd_produto = a.cd_produto))), (0)::double precision))
        END AS quantidade,
    a.ds_tamanho AS codtamanho,
    NULL::text AS "Código do depósito",
    f_dic_prd_classificacao(a.cd_produto, 'DS'::text, (21)::bigint) AS nomecolecao,
    (CURRENT_DATE + 60) AS dataproduto,
    (((COALESCE(f_prd_saldo_produto((1)::bigint, (1)::bigint, a.cd_produto, NULL::timestamp without time zone), (0)::double precision) - COALESCE(( SELECT COALESCE(sum(aaa.qt_pendente), (0)::double precision) AS sum
           FROM vr_ped_pedidoi aaa
          WHERE ((aaa.cd_produto = a.cd_produto) AND (aaa.cd_operacao <> (44)::bigint) AND (aaa.cd_empresa = (1)::bigint) AND (aaa.tp_situacao <> (6)::bigint))), (0)::double precision)) + f_prd_saldo_produto((1)::bigint, (7)::bigint, a.cd_produto, NULL::timestamp without time zone)) + COALESCE(( SELECT sum((COALESCE(aa.qt_real, (0)::double precision) - COALESCE(aa.qt_finalizada, (0)::double precision))) AS sum
           FROM vr_pcp_opi aa,
            vr_pcp_opc bb,
            prd_produtoclas cc
          WHERE ((aa.cd_empresa = 1) AND (bb.dt_inclusao <= '2026-05-19 00:00:00'::timestamp without time zone) AND (aa.cd_produto = cc.cd_produto) AND (cc.cd_tipoclas = 802) AND ((cc.cd_classificacao)::text = '2         '::text) AND (aa.cd_produto = a.cd_produto) AND (((f_dic_prd_classificacao(a.cd_produto, 'CD'::text, (124)::bigint))::text = ANY (ARRAY[('001'::character varying)::text, ('002'::character varying)::text, ('004'::character varying)::text, ('005'::character varying)::text])) OR (f_dic_prd_classificacao(a.cd_produto, 'CD'::text, (124)::bigint) IS NULL)) AND (aa.cd_empresa = bb.cd_empresa) AND (aa.nr_ciclo = bb.nr_ciclo) AND (aa.nr_op = bb.nr_op) AND (COALESCE(bb.cd_categoria, (0)::bigint) <> 15) AND (aa.tp_situacao = ANY (ARRAY[(5)::bigint, (10)::bigint, (15)::bigint, (20)::bigint])))), (0)::double precision)) AS quantidadeprontaentrega,
    a.cd_cor AS codcorbase,
    f_dic_prd_nivel(a.cd_produto, 'DS'::bpchar) AS nm_produto,
    a.ds_cor AS nomecor,
    f_dic_prd_codigobarra(a.cd_produto) AS ean13,
    NULL::text AS visualquantidadeproduto,
    NULL::text AS visualquantidadeproducao,
    a.cd_tamanho AS seqordenacaotamanho
   FROM vr_prd_prdgrade a,
    vr_prd_prdinfo b
  WHERE ((b.cd_produto = a.cd_produto) AND (((f_dic_prd_classificacao(a.cd_produto, 'CD'::text, (124)::bigint))::text = ANY (ARRAY[('001'::character varying)::text, ('002'::character varying)::text, ('007'::character varying)::text, ('004'::character varying)::text, ('005'::character varying)::text])) OR (f_dic_prd_classificacao(a.cd_produto, 'CD'::text, (124)::bigint) IS NULL)) AND ((b.in_inativo)::text = 'F'::text) AND ((a.cd_cor)::text <> 'LF        '::text) AND (b.cd_empresa = 1) AND (b.cd_produto = a.cd_produto) AND ((f_dic_prd_classificacao(a.cd_produto, 'CD'::text, (20)::bigint))::text = ANY (ARRAY[('0001'::character varying)::text, ('0002'::character varying)::text, ('0003'::character varying)::text, ('0020'::character varying)::text, ('0009'::character varying)::text])) AND ((a.cd_produto < 1000000) OR (a.cd_produto = ANY (ARRAY[(5001609)::bigint, (5001610)::bigint, (5001319)::bigint, (5001611)::bigint]))) AND ((((((COALESCE(f_prd_saldo_produto((1)::bigint, (1)::bigint, a.cd_produto, NULL::timestamp without time zone), (0)::double precision) - COALESCE(( SELECT COALESCE(sum(aaa.qt_pendente), (0)::double precision) AS sum
           FROM vr_ped_pedidoi aaa
          WHERE ((aaa.cd_produto = a.cd_produto) AND (aaa.cd_operacao <> (44)::bigint) AND (aaa.cd_empresa = (1)::bigint) AND (aaa.tp_situacao <> (6)::bigint))), (0)::double precision)) + f_prd_saldo_produto((1)::bigint, (7)::bigint, a.cd_produto, NULL::timestamp without time zone)) + COALESCE(( SELECT sum((COALESCE(aa.qt_real, (0)::double precision) - COALESCE(aa.qt_finalizada, (0)::double precision))) AS sum
           FROM vr_pcp_opi aa,
            vr_pcp_opc bb
          WHERE ((aa.cd_empresa = 1) AND (aa.cd_produto = a.cd_produto) AND (((f_dic_prd_classificacao(a.cd_produto, 'CD'::text, (124)::bigint))::text = ANY (ARRAY[('001'::character varying)::text, ('002'::character varying)::text, ('004'::character varying)::text, ('005'::character varying)::text])) OR (f_dic_prd_classificacao(a.cd_produto, 'CD'::text, (124)::bigint) IS NULL)) AND (aa.cd_empresa = bb.cd_empresa) AND (aa.nr_ciclo = bb.nr_ciclo) AND (aa.nr_op = bb.nr_op) AND (COALESCE(bb.cd_categoria, (0)::bigint) <> 15) AND (aa.tp_situacao = ANY (ARRAY[(5)::bigint, (10)::bigint, (15)::bigint, (20)::bigint])))), (0)::double precision)) + COALESCE(( SELECT COALESCE(sum(GREATEST((b_1.qt_lote - COALESCE(b_1.qt_gerouop, (0)::double precision)), (0)::double precision)), (0)::double precision) AS sum
           FROM (vr_pcp_lotepl2 b_1
             LEFT JOIN pcp_lotepv p ON ((b_1.nr_lote = p.nr_lote)))
          WHERE (((p.cd_auxiliar)::text = ANY (ARRAY['MA'::text, 'MG'::text])) AND (b_1.cd_produto = a.cd_produto))), (0)::double precision)) + COALESCE(( SELECT COALESCE(sum(GREATEST((b_1.qt_lote - COALESCE(b_1.qt_gerouop, (0)::double precision)), (0)::double precision)), (0)::double precision) AS sum
           FROM (vr_pcp_lotepl2 b_1
             LEFT JOIN pcp_lotepv p ON ((b_1.nr_lote = p.nr_lote)))
          WHERE (((p.cd_auxiliar)::text = 'PX'::text) AND (b_1.cd_produto = a.cd_produto))), (0)::double precision)) > (0)::double precision))
UNION ALL
 SELECT 1 AS codempresa,
    f_dic_prd_nivel(a.cd_produto, 'CD'::bpchar) AS cd_nivel,
    a.cd_produto AS codigoproduto,
    a.cd_tamanho AS seqtamanho,
    a.cd_cor AS seqsortimento,
    f_dic_prd_classificacao(a.cd_produto, 'CD'::text, (21)::bigint) AS colecao,
    1 AS estoquelimitado,
        CASE
            WHEN (((f_dic_prd_classificacao(a.cd_produto, 'CD'::text, (27)::bigint))::text = ANY (ARRAY[('0008'::character varying)::text, ('0007'::character varying)::text, ('0003'::character varying)::text])) AND (((COALESCE(f_prd_saldo_produto((1)::bigint, (1)::bigint, a.cd_produto, NULL::timestamp without time zone), (0)::double precision) - COALESCE(( SELECT COALESCE(sum(aaa.qt_pendente), (0)::double precision) AS sum
               FROM vr_ped_pedidoi aaa
              WHERE ((aaa.cd_produto = a.cd_produto) AND (aaa.cd_operacao <> (44)::bigint) AND (aaa.cd_empresa = (1)::bigint) AND (aaa.tp_situacao <> (6)::bigint))), (0)::double precision)) + f_prd_saldo_produto((1)::bigint, (7)::bigint, a.cd_produto, NULL::timestamp without time zone)) <= (2)::double precision)) THEN (0)::double precision
            ELSE ((((((COALESCE(f_prd_saldo_produto((1)::bigint, (1)::bigint, a.cd_produto, NULL::timestamp without time zone), (0)::double precision) - COALESCE(( SELECT COALESCE(sum(aaa.qt_pendente), (0)::double precision) AS sum
               FROM vr_ped_pedidoi aaa
              WHERE ((aaa.cd_produto = a.cd_produto) AND (aaa.cd_operacao <> (44)::bigint) AND (aaa.cd_empresa = (1)::bigint) AND (aaa.tp_situacao <> (6)::bigint))), (0)::double precision)) + f_prd_saldo_produto((1)::bigint, (7)::bigint, a.cd_produto, NULL::timestamp without time zone)) + COALESCE(( SELECT sum((COALESCE(aa.qt_real, (0)::double precision) - COALESCE(aa.qt_finalizada, (0)::double precision))) AS sum
               FROM vr_pcp_opi aa,
                vr_pcp_opc bb
              WHERE ((aa.cd_empresa = 1) AND (aa.cd_produto = a.cd_produto) AND (((f_dic_prd_classificacao(a.cd_produto, 'CD'::text, (124)::bigint))::text = ANY (ARRAY[('001'::character varying)::text, ('002'::character varying)::text, ('004'::character varying)::text, ('005'::character varying)::text])) OR (f_dic_prd_classificacao(a.cd_produto, 'CD'::text, (124)::bigint) IS NULL)) AND (aa.cd_empresa = bb.cd_empresa) AND (aa.nr_ciclo = bb.nr_ciclo) AND (aa.nr_op = bb.nr_op) AND (COALESCE(bb.cd_categoria, (0)::bigint) <> 15) AND (aa.tp_situacao = ANY (ARRAY[(5)::bigint, (10)::bigint, (15)::bigint, (20)::bigint])))), (0)::double precision)) + COALESCE(( SELECT COALESCE(sum(GREATEST((b_1.qt_lote - COALESCE(b_1.qt_gerouop, (0)::double precision)), (0)::double precision)), (0)::double precision) AS sum
               FROM (vr_pcp_lotepl2 b_1
                 LEFT JOIN pcp_lotepv p ON ((b_1.nr_lote = p.nr_lote)))
              WHERE (((p.cd_auxiliar)::text = ANY (ARRAY['MA'::text, 'MG'::text])) AND (b_1.cd_produto = a.cd_produto))), (0)::double precision)) + COALESCE(( SELECT COALESCE(sum(GREATEST((b_1.qt_lote - COALESCE(b_1.qt_gerouop, (0)::double precision)), (0)::double precision)), (0)::double precision) AS sum
               FROM (vr_pcp_lotepl2 b_1
                 LEFT JOIN pcp_lotepv p ON ((b_1.nr_lote = p.nr_lote)))
              WHERE (((p.cd_auxiliar)::text = 'PX'::text) AND (b_1.cd_produto = a.cd_produto))), (0)::double precision)) + COALESCE(( SELECT COALESCE(sum(GREATEST((b_1.qt_lote - COALESCE(b_1.qt_gerouop, (0)::double precision)), (0)::double precision)), (0)::double precision) AS sum
               FROM (vr_pcp_lotepl2 b_1
                 LEFT JOIN pcp_lotepv p ON ((b_1.nr_lote = p.nr_lote)))
              WHERE (((p.cd_auxiliar)::text = 'UL'::text) AND (b_1.cd_produto = a.cd_produto))), (0)::double precision))
        END AS quantidade,
    a.ds_tamanho AS codtamanho,
    NULL::text AS "Código do depósito",
    f_dic_prd_classificacao(a.cd_produto, 'DS'::text, (21)::bigint) AS nomecolecao,
    (CURRENT_DATE + 90) AS dataproduto,
    (((COALESCE(f_prd_saldo_produto((1)::bigint, (1)::bigint, a.cd_produto, NULL::timestamp without time zone), (0)::double precision) - COALESCE(( SELECT COALESCE(sum(aaa.qt_pendente), (0)::double precision) AS sum
           FROM vr_ped_pedidoi aaa
          WHERE ((aaa.cd_produto = a.cd_produto) AND (aaa.cd_operacao <> (44)::bigint) AND (aaa.cd_empresa = (1)::bigint) AND (aaa.tp_situacao <> (6)::bigint))), (0)::double precision)) + f_prd_saldo_produto((1)::bigint, (7)::bigint, a.cd_produto, NULL::timestamp without time zone)) + COALESCE(( SELECT sum((COALESCE(aa.qt_real, (0)::double precision) - COALESCE(aa.qt_finalizada, (0)::double precision))) AS sum
           FROM vr_pcp_opi aa,
            vr_pcp_opc bb,
            prd_produtoclas cc
          WHERE ((aa.cd_empresa = 1) AND (bb.dt_inclusao <= '2026-05-19 00:00:00'::timestamp without time zone) AND (aa.cd_produto = cc.cd_produto) AND (cc.cd_tipoclas = 802) AND ((cc.cd_classificacao)::text = '2         '::text) AND (aa.cd_produto = a.cd_produto) AND (((f_dic_prd_classificacao(a.cd_produto, 'CD'::text, (124)::bigint))::text = ANY (ARRAY[('001'::character varying)::text, ('002'::character varying)::text, ('004'::character varying)::text, ('005'::character varying)::text])) OR (f_dic_prd_classificacao(a.cd_produto, 'CD'::text, (124)::bigint) IS NULL)) AND (aa.cd_empresa = bb.cd_empresa) AND (aa.nr_ciclo = bb.nr_ciclo) AND (aa.nr_op = bb.nr_op) AND (COALESCE(bb.cd_categoria, (0)::bigint) <> 15) AND (aa.tp_situacao = ANY (ARRAY[(5)::bigint, (10)::bigint, (15)::bigint, (20)::bigint])))), (0)::double precision)) AS quantidadeprontaentrega,
    a.cd_cor AS codcorbase,
    f_dic_prd_nivel(a.cd_produto, 'DS'::bpchar) AS nm_produto,
    a.ds_cor AS nomecor,
    f_dic_prd_codigobarra(a.cd_produto) AS ean13,
    NULL::text AS visualquantidadeproduto,
    NULL::text AS visualquantidadeproducao,
    a.cd_tamanho AS seqordenacaotamanho
   FROM vr_prd_prdgrade a,
    vr_prd_prdinfo b
  WHERE ((b.cd_produto = a.cd_produto) AND (((f_dic_prd_classificacao(a.cd_produto, 'CD'::text, (124)::bigint))::text = ANY (ARRAY[('001'::character varying)::text, ('002'::character varying)::text, ('007'::character varying)::text, ('004'::character varying)::text, ('005'::character varying)::text])) OR (f_dic_prd_classificacao(a.cd_produto, 'CD'::text, (124)::bigint) IS NULL)) AND ((b.in_inativo)::text = 'F'::text) AND ((a.cd_cor)::text <> 'LF        '::text) AND (b.cd_empresa = 1) AND (b.cd_produto = a.cd_produto) AND ((f_dic_prd_classificacao(a.cd_produto, 'CD'::text, (20)::bigint))::text = ANY (ARRAY[('0001'::character varying)::text, ('0002'::character varying)::text, ('0003'::character varying)::text, ('0020'::character varying)::text, ('0009'::character varying)::text])) AND ((a.cd_produto < 1000000) OR (a.cd_produto = ANY (ARRAY[(5001609)::bigint, (5001610)::bigint, (5001319)::bigint, (5001611)::bigint]))) AND (((((((COALESCE(f_prd_saldo_produto((1)::bigint, (1)::bigint, a.cd_produto, NULL::timestamp without time zone), (0)::double precision) - COALESCE(( SELECT COALESCE(sum(aaa.qt_pendente), (0)::double precision) AS sum
           FROM vr_ped_pedidoi aaa
          WHERE ((aaa.cd_produto = a.cd_produto) AND (aaa.cd_operacao <> (44)::bigint) AND (aaa.cd_empresa = (1)::bigint) AND (aaa.tp_situacao <> (6)::bigint))), (0)::double precision)) + f_prd_saldo_produto((1)::bigint, (7)::bigint, a.cd_produto, NULL::timestamp without time zone)) + COALESCE(( SELECT sum((COALESCE(aa.qt_real, (0)::double precision) - COALESCE(aa.qt_finalizada, (0)::double precision))) AS sum
           FROM vr_pcp_opi aa,
            vr_pcp_opc bb
          WHERE ((aa.cd_empresa = 1) AND (aa.cd_produto = a.cd_produto) AND (((f_dic_prd_classificacao(a.cd_produto, 'CD'::text, (124)::bigint))::text = ANY (ARRAY[('001'::character varying)::text, ('002'::character varying)::text, ('004'::character varying)::text, ('005'::character varying)::text])) OR (f_dic_prd_classificacao(a.cd_produto, 'CD'::text, (124)::bigint) IS NULL)) AND (aa.cd_empresa = bb.cd_empresa) AND (aa.nr_ciclo = bb.nr_ciclo) AND (aa.nr_op = bb.nr_op) AND (COALESCE(bb.cd_categoria, (0)::bigint) <> 15) AND (aa.tp_situacao = ANY (ARRAY[(5)::bigint, (10)::bigint, (15)::bigint, (20)::bigint])))), (0)::double precision)) + COALESCE(( SELECT COALESCE(sum(GREATEST((b_1.qt_lote - COALESCE(b_1.qt_gerouop, (0)::double precision)), (0)::double precision)), (0)::double precision) AS sum
           FROM (vr_pcp_lotepl2 b_1
             LEFT JOIN pcp_lotepv p ON ((b_1.nr_lote = p.nr_lote)))
          WHERE (((p.cd_auxiliar)::text = ANY (ARRAY['MA'::text, 'MG'::text])) AND (b_1.cd_produto = a.cd_produto))), (0)::double precision)) + COALESCE(( SELECT COALESCE(sum(GREATEST((b_1.qt_lote - COALESCE(b_1.qt_gerouop, (0)::double precision)), (0)::double precision)), (0)::double precision) AS sum
           FROM (vr_pcp_lotepl2 b_1
             LEFT JOIN pcp_lotepv p ON ((b_1.nr_lote = p.nr_lote)))
          WHERE (((p.cd_auxiliar)::text = 'PX'::text) AND (b_1.cd_produto = a.cd_produto))), (0)::double precision)) + COALESCE(( SELECT COALESCE(sum(GREATEST((b_1.qt_lote - COALESCE(b_1.qt_gerouop, (0)::double precision)), (0)::double precision)), (0)::double precision) AS sum
           FROM (vr_pcp_lotepl2 b_1
             LEFT JOIN pcp_lotepv p ON ((b_1.nr_lote = p.nr_lote)))
          WHERE (((p.cd_auxiliar)::text = 'UL'::text) AND (b_1.cd_produto = a.cd_produto))), (0)::double precision)) > (0)::double precision))