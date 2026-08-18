-- =====================================================
-- ESTRUTURA FINAL - ANALISE DE REPOSICAO PERMANENTE
-- =====================================================
-- Duas tabelas principais:
-- 1. reposicao_dentro_regra: consolidado por mes/loja
-- 2. reposicao_fora_regra: detalhado por recebimento fora da regra
-- =====================================================

-- =====================================================
-- TABELA 1: DENTRO DA REGRA (consolidado por mes/loja)
-- =====================================================
DROP TABLE IF EXISTS reposicao_dentro_regra CASCADE;

CREATE TABLE reposicao_dentro_regra (
    mes VARCHAR(7) NOT NULL,                -- '2026-06'
    cd_loja INTEGER NOT NULL,
    nome_loja VARCHAR(100),

    -- Contexto
    skus_demanda INTEGER,                   -- SKUs com demanda (vendas 3m > 0)
    demanda_bruta NUMERIC(12,0),            -- estoque_minimo total
    saldo_inicial NUMERIC(12,0),            -- saldo total em 01 do mes
    pct_cobertura_inicial NUMERIC(5,1),     -- % saldo/demanda

    -- Necessidade
    necessidade NUMERIC(12,0),              -- MAX(0, est_min - saldo) por SKU

    -- Entradas
    entrada_periodo NUMERIC(12,0),          -- lote do mes, fabrica
    entrada_atrasada NUMERIC(12,0),         -- lote anterior, fabrica, com lote
    entrada_sem_lote NUMERIC(12,0),         -- fabrica sem lote
    entrada_nao_fabrica NUMERIC(12,0),      -- transferencias entre lojas
    entrada_total NUMERIC(12,0),            -- soma de todas

    -- Resultado
    faltou NUMERIC(12,0),                   -- soma dos gaps negativos por SKU
    sobra_periodo NUMERIC(12,0),            -- entrada_periodo - necessidade (se > 0)

    -- Status por SKU
    skus_ok INTEGER,                        -- entrada_periodo >= necessidade
    skus_parcial INTEGER,                   -- 0 < entrada_periodo < necessidade
    skus_zerados INTEGER,                   -- entrada_periodo = 0 e necessidade > 0
    pct_ok NUMERIC(5,1),                    -- % SKUs OK

    -- Curvas com problema
    curvas_com_falta VARCHAR(100),          -- 'CURVA A, CURVA B'

    PRIMARY KEY (mes, cd_loja)
);

-- =====================================================
-- TABELA 2: FORA DA REGRA (detalhado por recebimento)
-- =====================================================
DROP TABLE IF EXISTS reposicao_fora_regra CASCADE;

CREATE TABLE reposicao_fora_regra (
    id SERIAL PRIMARY KEY,
    mes_recebimento VARCHAR(7) NOT NULL,    -- mes que entrou fisicamente
    mes_lote VARCHAR(7),                    -- mes do lote (se existir)
    cd_loja INTEGER NOT NULL,
    nome_loja VARCHAR(100),
    cd_produto BIGINT NOT NULL,
    referencia VARCHAR(50),
    curva VARCHAR(20),
    qt_entrada NUMERIC(12,0),
    nr_transacao BIGINT,
    nr_transacaoori BIGINT,
    dt_transacao DATE,
    cd_empresaori INTEGER,
    nome_origem VARCHAR(100),
    cd_lote VARCHAR(20),

    -- Classificacao
    motivo VARCHAR(50) NOT NULL,
    -- Valores possiveis:
    -- 'FABRICA_ATRASADA_COM_LOTE' - veio da fabrica, lote preenchido mas de mes anterior
    -- 'FABRICA_SEM_LOTE' - veio da fabrica, sem lote definido
    -- 'NAO_FABRICA' - transferencia entre lojas
    -- 'PERIODO_FORA_BASE' - lote correto mas produto/loja nao tinha demanda

    descricao_motivo VARCHAR(200),

    -- Flag se estava na base de demanda
    na_base_demanda BOOLEAN DEFAULT FALSE
);

CREATE INDEX idx_fora_regra_mes ON reposicao_fora_regra(mes_recebimento);
CREATE INDEX idx_fora_regra_loja ON reposicao_fora_regra(cd_loja);
CREATE INDEX idx_fora_regra_motivo ON reposicao_fora_regra(motivo);

-- =====================================================
-- TABELA 3: BASE ANALITICA (opcional, para drill-down)
-- Apenas se precisar consultar por SKU
-- =====================================================
-- Esta tabela é PESADA (produto × loja × mes)
-- Criar sob demanda ou como view materializada por mes

-- CREATE TABLE reposicao_analitico_sku (
--     mes VARCHAR(7),
--     cd_loja INTEGER,
--     cd_produto BIGINT,
--     referencia VARCHAR(50),
--     curva VARCHAR(20),
--     vendas_3m NUMERIC(12,0),
--     estoque_minimo NUMERIC(12,0),
--     saldo_inicial NUMERIC(12,0),
--     necessidade NUMERIC(12,0),
--     entrada_periodo NUMERIC(12,0),
--     entrada_atrasada NUMERIC(12,0),
--     entrada_total NUMERIC(12,0),
--     gap NUMERIC(12,0),
--     status VARCHAR(20),
--     PRIMARY KEY (mes, cd_loja, cd_produto)
-- );

-- =====================================================
-- VIEWS PARA POWER BI
-- =====================================================

-- View consolidada por mes (todas as lojas)
CREATE OR REPLACE VIEW vw_reposicao_resumo_mes AS
SELECT
    mes,
    COUNT(*) AS qtd_lojas,
    SUM(skus_demanda) AS total_skus,
    SUM(demanda_bruta) AS demanda_bruta,
    SUM(saldo_inicial) AS saldo_inicial,
    ROUND(100.0 * SUM(saldo_inicial) / NULLIF(SUM(demanda_bruta), 0), 1) AS pct_cobertura,
    SUM(necessidade) AS necessidade,
    SUM(entrada_periodo) AS entrada_periodo,
    SUM(entrada_atrasada) AS entrada_atrasada,
    SUM(entrada_sem_lote) AS entrada_sem_lote,
    SUM(entrada_nao_fabrica) AS entrada_nao_fabrica,
    SUM(entrada_total) AS entrada_total,
    SUM(faltou) AS faltou,
    SUM(skus_ok) AS skus_ok,
    SUM(skus_parcial) AS skus_parcial,
    SUM(skus_zerados) AS skus_zerados,
    ROUND(100.0 * SUM(skus_ok) / NULLIF(SUM(skus_demanda), 0), 1) AS pct_ok_geral
FROM reposicao_dentro_regra
GROUP BY mes
ORDER BY mes;

-- View fora da regra agregado por motivo/mes
CREATE OR REPLACE VIEW vw_reposicao_fora_regra_resumo AS
SELECT
    mes_recebimento,
    motivo,
    COUNT(*) AS qtd_registros,
    COUNT(DISTINCT cd_loja) AS qtd_lojas,
    SUM(qt_entrada) AS total_pecas
FROM reposicao_fora_regra
GROUP BY mes_recebimento, motivo
ORDER BY mes_recebimento, motivo;
