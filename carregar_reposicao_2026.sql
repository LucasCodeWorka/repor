-- =====================================================
-- CARREGAR REPOSICAO 2026 - TODOS OS MESES
-- Executa mes a mes para evitar timeout
-- =====================================================

-- Parametro: mes no formato 'YYYY-MM'
-- Exemplo: SELECT carregar_reposicao_mes('2026-06');

-- =====================================================
-- FUNCAO PARA CARREGAR UM MES
-- =====================================================
CREATE OR REPLACE FUNCTION carregar_reposicao_mes(p_mes VARCHAR(7))
RETURNS void AS $$
DECLARE
    v_ano INTEGER;
    v_mes_num INTEGER;
    v_inicio_mes DATE;
    v_fim_mes DATE;
    v_inicio_vendas DATE;
    v_lote_pattern VARCHAR(10);
BEGIN
    -- Extrair ano e mes
    v_ano := SUBSTRING(p_mes FROM 1 FOR 4)::INTEGER;
    v_mes_num := SUBSTRING(p_mes FROM 6 FOR 2)::INTEGER;

    -- Datas
    v_inicio_mes := (p_mes || '-01')::DATE;
    v_fim_mes := (v_inicio_mes + INTERVAL '1 month')::DATE;
    v_inicio_vendas := (v_inicio_mes - INTERVAL '3 months')::DATE;

    -- Pattern do lote (ex: '26.06%' para junho/2026)
    v_lote_pattern := SUBSTRING(v_ano::TEXT FROM 3 FOR 2) || '.' || LPAD(v_mes_num::TEXT, 2, '0') || '%';

    RAISE NOTICE 'Carregando mes: % (lote: %)', p_mes, v_lote_pattern;
    RAISE NOTICE 'Vendas de % a %', v_inicio_vendas, v_inicio_mes;

    -- Limpar dados anteriores do mes
    DELETE FROM reposicao_dentro_regra WHERE mes = p_mes;
    DELETE FROM reposicao_fora_regra WHERE mes_recebimento = p_mes;

    -- =====================================================
    -- INSERIR DENTRO DA REGRA
    -- =====================================================
    INSERT INTO reposicao_dentro_regra (
        mes, cd_loja, nome_loja,
        skus_demanda, demanda_bruta, saldo_inicial, pct_cobertura_inicial,
        necessidade,
        entrada_periodo, entrada_atrasada, entrada_sem_lote, entrada_nao_fabrica, entrada_total,
        faltou, sobra_periodo,
        skus_ok, skus_parcial, skus_zerados, pct_ok,
        curvas_com_falta
    )
    WITH produtos_permanente AS (
        SELECT DISTINCT pc.cd_produto
        FROM prd_produtoclas pc
        JOIN prd_classificacao c ON pc.cd_classificacao = c.cd_classificacao AND pc.cd_tipoclas = c.cd_tipoclas
        WHERE pc.cd_tipoclas = 802
          AND c.ds_classificacao IN ('PERMANENTE', 'PERMANENTE COR NOVA')
    ),

    -- Vendas 3 meses anteriores
    vendas_3m AS (
        SELECT
            t.cd_empresa AS cd_loja,
            i.cd_produto,
            SUM(i.qt_solicitada * CASE WHEN t.tp_modalidade::text = '3' THEN -1 ELSE 1 END) AS vendas_3m
        FROM vr_tra_transacao t
        JOIN vr_tra_transitem i ON t.nr_transacao = i.nr_transacao AND t.cd_empresa = i.cd_empresa
        WHERE t.cd_empresa > 1
            AND t.cd_empresa <> 4
            AND t.cd_operacao NOT IN (140, 76, 25, 26, 27, 273, 44, 240, 241, 242, 243, 244, 245, 239, 238, 237, 236)
            AND i.dt_transacao >= v_inicio_vendas
            AND i.dt_transacao < v_inicio_mes
            AND i.cd_compvend <> 1
            AND t.tp_situacao <> 6
            AND t.tp_modalidade::text IN ('3', '4')
        GROUP BY t.cd_empresa, i.cd_produto
        HAVING SUM(i.qt_solicitada * CASE WHEN t.tp_modalidade::text = '3' THEN -1 ELSE 1 END) > 0
    ),

    -- Entradas no mes classificadas
    entradas_mes AS (
        SELECT
            t.cd_empresa AS cd_loja,
            i.cd_produto,
            i.qt_solicitada AS qt_entrada,
            t.cd_empresaori,
            lote.cd_lote,
            CASE
                WHEN t.cd_empresaori <> 1 THEN 'NAO_FABRICA'
                WHEN lote.cd_lote IS NULL THEN 'SEM_LOTE'
                WHEN lote.cd_lote LIKE v_lote_pattern THEN 'PERIODO'
                ELSE 'ATRASADA'
            END AS tipo_entrada
        FROM vr_tra_transacao t
        JOIN vr_tra_transitem i ON t.nr_transacao = i.nr_transacao AND t.cd_empresa = i.cd_empresa
        LEFT JOIN vr_ped_pedidotra ped ON ped.nr_transacao = t.nr_transacaoori
        LEFT JOIN vr_ped_pedidoc2 lote
            ON ped.cd_emppedido = lote.cd_empresa
            AND ped.cd_pedido = lote.cd_pedido
            AND ped.cd_representant = lote.cd_representant
        WHERE t.cd_empresa > 1
            AND t.cd_empresa <> 4
            AND t.tp_operacao = 'E'
            AND t.tp_modalidade::text = '2'
            AND t.tp_situacao = 4
            AND i.dt_transacao >= v_inicio_mes
            AND i.dt_transacao < v_fim_mes
    ),

    entradas_agregadas AS (
        SELECT
            cd_loja,
            cd_produto,
            SUM(qt_entrada) FILTER (WHERE tipo_entrada = 'PERIODO') AS entrada_periodo,
            SUM(qt_entrada) FILTER (WHERE tipo_entrada = 'ATRASADA') AS entrada_atrasada,
            SUM(qt_entrada) FILTER (WHERE tipo_entrada = 'SEM_LOTE') AS entrada_sem_lote,
            SUM(qt_entrada) FILTER (WHERE tipo_entrada = 'NAO_FABRICA') AS entrada_nao_fabrica
        FROM entradas_mes
        GROUP BY cd_loja, cd_produto
    ),

    -- Base com calculo de necessidade
    base AS (
        SELECT
            v.cd_loja,
            emp.nm_grupoempresa AS nome_loja,
            v.cd_produto,
            abc.curva_completa AS curva,
            v.vendas_3m,
            ROUND(v.vendas_3m / 3.0 * 1.5, 0) AS estoque_minimo,
            COALESCE(f_prd_saldo_produto(v.cd_loja, 1::bigint, v.cd_produto, v_inicio_mes), 0) AS saldo_inicial,
            GREATEST(0, ROUND(v.vendas_3m / 3.0 * 1.5, 0) - COALESCE(f_prd_saldo_produto(v.cd_loja, 1::bigint, v.cd_produto, v_inicio_mes), 0)) AS necessidade,
            COALESCE(e.entrada_periodo, 0) AS entrada_periodo,
            COALESCE(e.entrada_atrasada, 0) AS entrada_atrasada,
            COALESCE(e.entrada_sem_lote, 0) AS entrada_sem_lote,
            COALESCE(e.entrada_nao_fabrica, 0) AS entrada_nao_fabrica
        FROM vendas_3m v
        JOIN vr_ger_empresa emp ON v.cd_loja = emp.cd_empresa
        JOIN produtos_permanente pp ON v.cd_produto = pp.cd_produto
        LEFT JOIN curva_abc abc ON abc.referencia = f_dic_prd_nivel(v.cd_produto, 'CD'::bpchar)
        LEFT JOIN entradas_agregadas e ON v.cd_loja = e.cd_loja AND v.cd_produto = e.cd_produto
    ),

    analise AS (
        SELECT
            *,
            entrada_periodo - necessidade AS gap,
            CASE
                WHEN necessidade = 0 THEN 'JA_TINHA'
                WHEN entrada_periodo >= necessidade THEN 'OK'
                WHEN entrada_periodo > 0 THEN 'PARCIAL'
                ELSE 'ZERADO'
            END AS status
        FROM base
    )

    SELECT
        p_mes AS mes,
        cd_loja,
        nome_loja,
        COUNT(*) FILTER (WHERE necessidade > 0) AS skus_demanda,
        SUM(estoque_minimo) AS demanda_bruta,
        SUM(saldo_inicial) AS saldo_inicial,
        ROUND(100.0 * SUM(saldo_inicial) / NULLIF(SUM(estoque_minimo), 0), 1) AS pct_cobertura_inicial,
        SUM(necessidade) AS necessidade,
        SUM(entrada_periodo) AS entrada_periodo,
        SUM(entrada_atrasada) AS entrada_atrasada,
        SUM(entrada_sem_lote) AS entrada_sem_lote,
        SUM(entrada_nao_fabrica) AS entrada_nao_fabrica,
        SUM(entrada_periodo) + SUM(entrada_atrasada) + SUM(entrada_sem_lote) + SUM(entrada_nao_fabrica) AS entrada_total,
        ABS(SUM(gap) FILTER (WHERE gap < 0)) AS faltou,
        GREATEST(0, SUM(entrada_periodo) - SUM(necessidade)) AS sobra_periodo,
        COUNT(*) FILTER (WHERE status = 'OK') AS skus_ok,
        COUNT(*) FILTER (WHERE status = 'PARCIAL') AS skus_parcial,
        COUNT(*) FILTER (WHERE status = 'ZERADO') AS skus_zerados,
        ROUND(100.0 * COUNT(*) FILTER (WHERE status = 'OK') / NULLIF(COUNT(*) FILTER (WHERE necessidade > 0), 0), 1) AS pct_ok,
        STRING_AGG(DISTINCT curva, ', ' ORDER BY curva) FILTER (WHERE status IN ('PARCIAL', 'ZERADO')) AS curvas_com_falta
    FROM analise
    GROUP BY cd_loja, nome_loja;

    RAISE NOTICE 'Dentro da regra inserido: % linhas', (SELECT COUNT(*) FROM reposicao_dentro_regra WHERE mes = p_mes);

    -- =====================================================
    -- INSERIR FORA DA REGRA
    -- =====================================================
    INSERT INTO reposicao_fora_regra (
        mes_recebimento, mes_lote, cd_loja, nome_loja,
        cd_produto, referencia, curva, qt_entrada,
        nr_transacao, nr_transacaoori, dt_transacao,
        cd_empresaori, nome_origem, cd_lote,
        motivo, descricao_motivo, na_base_demanda
    )
    WITH produtos_permanente AS (
        SELECT DISTINCT pc.cd_produto
        FROM prd_produtoclas pc
        JOIN prd_classificacao c ON pc.cd_classificacao = c.cd_classificacao AND pc.cd_tipoclas = c.cd_tipoclas
        WHERE pc.cd_tipoclas = 802
          AND c.ds_classificacao IN ('PERMANENTE', 'PERMANENTE COR NOVA')
    ),

    base_demanda AS (
        SELECT DISTINCT cd_empresa AS cd_loja, cd_produto
        FROM (
            SELECT
                t.cd_empresa,
                i.cd_produto,
                SUM(i.qt_solicitada * CASE WHEN t.tp_modalidade::text = '3' THEN -1 ELSE 1 END) AS vendas
            FROM vr_tra_transacao t
            JOIN vr_tra_transitem i ON t.nr_transacao = i.nr_transacao AND t.cd_empresa = i.cd_empresa
            WHERE t.cd_empresa > 1
                AND t.cd_empresa <> 4
                AND t.cd_operacao NOT IN (140, 76, 25, 26, 27, 273, 44, 240, 241, 242, 243, 244, 245, 239, 238, 237, 236)
                AND i.dt_transacao >= v_inicio_vendas
                AND i.dt_transacao < v_inicio_mes
                AND i.cd_compvend <> 1
                AND t.tp_situacao <> 6
                AND t.tp_modalidade::text IN ('3', '4')
            GROUP BY t.cd_empresa, i.cd_produto
            HAVING SUM(i.qt_solicitada * CASE WHEN t.tp_modalidade::text = '3' THEN -1 ELSE 1 END) > 0
        ) v
        JOIN produtos_permanente pp ON v.cd_produto = pp.cd_produto
    ),

    entradas_fora AS (
        SELECT
            t.cd_empresa AS cd_loja,
            emp.nm_grupoempresa AS nome_loja,
            i.cd_produto,
            f_dic_prd_nivel(i.cd_produto, 'CD'::bpchar) AS referencia,
            abc.curva_completa AS curva,
            i.qt_solicitada AS qt_entrada,
            t.nr_transacao,
            t.nr_transacaoori,
            i.dt_transacao::date AS dt_transacao,
            t.cd_empresaori,
            orig.nm_grupoempresa AS nome_origem,
            lote.cd_lote,
            CASE
                WHEN t.cd_empresaori <> 1 THEN 'NAO_FABRICA'
                WHEN lote.cd_lote IS NULL THEN 'FABRICA_SEM_LOTE'
                WHEN lote.cd_lote LIKE v_lote_pattern THEN 'PERIODO_FORA_BASE'
                ELSE 'FABRICA_ATRASADA_COM_LOTE'
            END AS motivo,
            bd.cd_loja IS NOT NULL AS na_base_demanda
        FROM vr_tra_transacao t
        JOIN vr_tra_transitem i ON t.nr_transacao = i.nr_transacao AND t.cd_empresa = i.cd_empresa
        JOIN vr_ger_empresa emp ON t.cd_empresa = emp.cd_empresa
        LEFT JOIN vr_ger_empresa orig ON t.cd_empresaori = orig.cd_empresa
        LEFT JOIN vr_ped_pedidotra ped ON ped.nr_transacao = t.nr_transacaoori
        LEFT JOIN vr_ped_pedidoc2 lote
            ON ped.cd_emppedido = lote.cd_empresa
            AND ped.cd_pedido = lote.cd_pedido
            AND ped.cd_representant = lote.cd_representant
        LEFT JOIN curva_abc abc ON abc.referencia = f_dic_prd_nivel(i.cd_produto, 'CD'::bpchar)
        LEFT JOIN base_demanda bd ON t.cd_empresa = bd.cd_loja AND i.cd_produto = bd.cd_produto
        WHERE t.cd_empresa > 1
            AND t.cd_empresa <> 4
            AND t.tp_operacao = 'E'
            AND t.tp_modalidade::text = '2'
            AND t.tp_situacao = 4
            AND i.dt_transacao >= v_inicio_mes
            AND i.dt_transacao < v_fim_mes
            -- Excluir o que e do periodo E esta na base (isso vai em dentro_regra)
            AND NOT (
                t.cd_empresaori = 1
                AND lote.cd_lote LIKE v_lote_pattern
                AND bd.cd_loja IS NOT NULL
            )
    )

    SELECT
        p_mes AS mes_recebimento,
        CASE
            WHEN cd_lote IS NOT NULL THEN '20' || SUBSTRING(cd_lote FROM 1 FOR 2) || '-' || SUBSTRING(cd_lote FROM 4 FOR 2)
            ELSE NULL
        END AS mes_lote,
        cd_loja,
        nome_loja,
        cd_produto,
        referencia,
        curva,
        qt_entrada,
        nr_transacao,
        nr_transacaoori,
        dt_transacao,
        cd_empresaori,
        nome_origem,
        cd_lote,
        motivo,
        CASE motivo
            WHEN 'NAO_FABRICA' THEN 'Transferencia de ' || COALESCE(nome_origem, 'outra loja')
            WHEN 'FABRICA_SEM_LOTE' THEN 'Fabrica sem lote definido'
            WHEN 'FABRICA_ATRASADA_COM_LOTE' THEN 'Lote ' || COALESCE(cd_lote, '?') || ' (atrasado)'
            WHEN 'PERIODO_FORA_BASE' THEN 'Lote correto mas sem demanda no periodo'
            ELSE motivo
        END AS descricao_motivo,
        na_base_demanda
    FROM entradas_fora;

    RAISE NOTICE 'Fora da regra inserido: % linhas', (SELECT COUNT(*) FROM reposicao_fora_regra WHERE mes_recebimento = p_mes);

END;
$$ LANGUAGE plpgsql;

-- =====================================================
-- EXECUTAR PARA CADA MES DE 2026
-- =====================================================
-- ATENÇÃO: Cada mes demora ~2-3 minutos por causa do f_prd_saldo_produto
-- Execute um por vez para monitorar

-- SELECT carregar_reposicao_mes('2026-01');
-- SELECT carregar_reposicao_mes('2026-02');
-- SELECT carregar_reposicao_mes('2026-03');
-- SELECT carregar_reposicao_mes('2026-04');
-- SELECT carregar_reposicao_mes('2026-05');
-- SELECT carregar_reposicao_mes('2026-06');
-- SELECT carregar_reposicao_mes('2026-07');
