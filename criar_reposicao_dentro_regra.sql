BEGIN;

DROP TABLE IF EXISTS reposicao_dentro_regra;

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

CREATE INDEX idx_reposicao_dentro_regra_mes_loja
    ON reposicao_dentro_regra (mes, cd_loja);

COMMIT;

-- Validacao:
-- SELECT mes, SUM(necessidade), SUM(entrada_periodo), SUM(faltou)
-- FROM reposicao_dentro_regra
-- GROUP BY mes
-- ORDER BY mes;
