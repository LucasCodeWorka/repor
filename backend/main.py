import json
import os
from contextlib import contextmanager
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import psycopg2
import psycopg2.extras
from dotenv import load_dotenv
from fastapi import Body, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from backend.totvs_moda import (
    TotvsModaClient,
    TotvsModaError,
    build_order_payload,
    missing_totvs_settings,
    totvs_settings,
)


load_dotenv(Path(__file__).resolve().parents[1] / ".env")

app = FastAPI(title="Reposicao Permanente 2026 API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
        "http://localhost:3002",
        "http://127.0.0.1:3002",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def json_safe(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return value


def rows_to_dicts(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [{key: json_safe(value) for key, value in row.items()} for row in rows]


@contextmanager
def get_connection():
    conn = psycopg2.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
    )
    try:
        yield conn
    finally:
        conn.close()


def fetch_all(query: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    try:
        with get_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(query, params or {})
                return rows_to_dicts(cur.fetchall())
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


def fetch_one(query: str, params: dict[str, Any] | None = None) -> dict[str, Any] | None:
    rows = fetch_all(query, params)
    return rows[0] if rows else None


def execute_transaction(
    statements: list[tuple[str, dict[str, Any] | None]],
) -> list[list[dict[str, Any]]]:
    results: list[list[dict[str, Any]]] = []
    try:
        with get_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                for query, params in statements:
                    cur.execute(query, params or {})
                    if cur.description:
                        results.append(rows_to_dicts(cur.fetchall()))
                    else:
                        results.append([])
            conn.commit()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return results


def relation_exists(table_name: str) -> bool:
    row = fetch_one("SELECT to_regclass(%(table_name)s) AS relation", {"table_name": table_name})
    return bool(row and row["relation"])


def column_exists(table_name: str, column_name: str) -> bool:
    row = fetch_one(
        """
        SELECT 1 AS exists
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = %(table_name)s
          AND column_name = %(column_name)s
        LIMIT 1;
        """,
        {"table_name": table_name, "column_name": column_name},
    )
    return bool(row)


CLASSIFICATION_TYPES = {
    "familia": 20,
    "linha": 21,
    "status_produto": 27,
    "continuidade": 124,
}


def product_classification_filter_sql(
    alias: str,
    status_produto: str | None = None,
    continuidade: str | None = None,
    linha: str | None = None,
    familia: str | None = None,
) -> tuple[str, dict[str, Any]]:
    filters = {
        "status_produto": status_produto,
        "continuidade": continuidade,
        "linha": linha,
        "familia": familia,
    }
    clauses: list[str] = []
    params: dict[str, Any] = {}
    for name, value in filters.items():
        if not value or value == "TODOS":
            continue
        params[name] = value
        params[f"{name}_tipoclas"] = CLASSIFICATION_TYPES[name]
        clauses.append(
            f"""
            AND EXISTS (
                SELECT 1
                FROM prd_produtoclas pc_{name}
                JOIN prd_classificacao c_{name}
                    ON c_{name}.cd_tipoclas = pc_{name}.cd_tipoclas
                   AND c_{name}.cd_classificacao = pc_{name}.cd_classificacao
                WHERE pc_{name}.cd_produto = {alias}.cd_produto
                  AND pc_{name}.cd_tipoclas = %({name}_tipoclas)s
                  AND c_{name}.ds_classificacao = %({name})s
            )
            """
        )
    return "\n".join(clauses), params


def product_classification_column_filter_sql(
    alias: str,
    status_produto: str | None = None,
    continuidade: str | None = None,
    linha: str | None = None,
    familia: str | None = None,
) -> tuple[str, dict[str, Any]]:
    filters = {
        "status_produto": status_produto,
        "continuidade": continuidade,
        "linha": linha,
        "familia": familia,
    }
    clauses: list[str] = []
    params: dict[str, Any] = {}
    for name, value in filters.items():
        if not value or value == "TODOS":
            continue
        params[name] = value
        clauses.append(f"AND {alias}.{name} = %({name})s")
    return "\n".join(clauses), params


def product_classification_select(alias: str) -> str:
    return f"""
        (
            SELECT c.ds_classificacao
            FROM prd_produtoclas pc
            JOIN prd_classificacao c
                ON c.cd_tipoclas = pc.cd_tipoclas
               AND c.cd_classificacao = pc.cd_classificacao
            WHERE pc.cd_produto = {alias}.cd_produto
              AND pc.cd_tipoclas = {CLASSIFICATION_TYPES["status_produto"]}
            LIMIT 1
        ) AS status_produto,
        (
            SELECT c.ds_classificacao
            FROM prd_produtoclas pc
            JOIN prd_classificacao c
                ON c.cd_tipoclas = pc.cd_tipoclas
               AND c.cd_classificacao = pc.cd_classificacao
            WHERE pc.cd_produto = {alias}.cd_produto
              AND pc.cd_tipoclas = {CLASSIFICATION_TYPES["continuidade"]}
            LIMIT 1
        ) AS continuidade,
        (
            SELECT c.ds_classificacao
            FROM prd_produtoclas pc
            JOIN prd_classificacao c
                ON c.cd_tipoclas = pc.cd_tipoclas
               AND c.cd_classificacao = pc.cd_classificacao
            WHERE pc.cd_produto = {alias}.cd_produto
              AND pc.cd_tipoclas = {CLASSIFICATION_TYPES["linha"]}
            LIMIT 1
        ) AS linha,
        (
            SELECT c.ds_classificacao
            FROM prd_produtoclas pc
            JOIN prd_classificacao c
                ON c.cd_tipoclas = pc.cd_tipoclas
               AND c.cd_classificacao = pc.cd_classificacao
            WHERE pc.cd_produto = {alias}.cd_produto
              AND pc.cd_tipoclas = {CLASSIFICATION_TYPES["familia"]}
            LIMIT 1
        ) AS familia
    """


def source_summary_table(product_filter_sql: str = "", analytic_table: str | None = None) -> str:
    table = analytic_table or source_analytic_table()
    if relation_exists(f"public.{table}"):
        return """
        (
            SELECT
                a.mes,
                a.cd_loja,
                MAX(a.nome_loja) AS nome_loja,
                COUNT(*)::integer AS qtd_skus,
                COUNT(*) FILTER (WHERE a.necessidade > 0)::integer AS qtd_skus_demanda,
                COUNT(*) FILTER (WHERE a.necessidade > 0 AND a.entrada_total >= a.necessidade)::integer AS skus_atendidos,
                COUNT(*) FILTER (WHERE a.necessidade > 0 AND a.entrada_total < a.necessidade)::integer AS skus_faltantes,
                COUNT(*) FILTER (WHERE a.necessidade > 0 AND a.entrada_periodo > 0)::integer AS skus_entrada_periodo,
                COUNT(*) FILTER (WHERE a.necessidade > 0 AND a.entrada_atrasada > 0)::integer AS skus_entrada_atrasada,
                COUNT(*) FILTER (WHERE a.necessidade > 0 AND a.entrada_sem_lote > 0)::integer AS skus_entrada_sem_lote,
                SUM(a.estoque_minimo)::numeric AS estoque_minimo_total,
                SUM(a.saldo_inicial)::numeric AS saldo_inicial_total,
                SUM(a.necessidade)::numeric AS necessidade_total,
                SUM(a.entrada_periodo)::numeric AS entrada_periodo,
                SUM(a.entrada_atrasada)::numeric AS entrada_atrasada,
                SUM(a.entrada_sem_lote)::numeric AS entrada_sem_lote,
                SUM(a.entrada_total)::numeric AS entrada_total,
                SUM(CASE WHEN a.necessidade <= 0 THEN a.entrada_total ELSE 0 END)::numeric AS entrada_sem_necessidade,
                COUNT(*) FILTER (WHERE a.necessidade <= 0 AND a.entrada_total > 0)::integer AS skus_entrada_sem_necessidade,
                SUM(GREATEST(0, a.necessidade - a.entrada_total))::numeric AS faltou,
                CASE
                    WHEN COUNT(*) FILTER (WHERE a.necessidade > 0) > 0
                    THEN ROUND(
                        COUNT(*) FILTER (WHERE a.necessidade > 0 AND a.entrada_total >= a.necessidade)::numeric
                        / COUNT(*) FILTER (WHERE a.necessidade > 0)::numeric * 100,
                        1
                    )
                    ELSE 100
                END AS taxa_atendimento,
                COUNT(*) FILTER (WHERE a.necessidade > 0 AND a.entrada_total >= a.necessidade)::integer AS skus_ok,
                COUNT(*) FILTER (WHERE a.necessidade > 0 AND a.entrada_total > 0 AND a.entrada_total < a.necessidade)::integer AS skus_parcial,
                COUNT(*) FILTER (WHERE a.necessidade > 0 AND a.entrada_total = 0)::integer AS skus_zerados,
                COUNT(*) FILTER (WHERE a.status_reposicao = 'SEM NECESSIDADE')::integer AS skus_sem_necessidade,
                NULL::timestamp AS atualizado_em
            FROM SOURCE_ANALYTIC_TABLE a
            WHERE 1 = 1
              PRODUCT_FILTER_SQL
            GROUP BY a.mes, a.cd_loja
        ) AS resumo_source
    """.replace("SOURCE_ANALYTIC_TABLE", table).replace("PRODUCT_FILTER_SQL", product_filter_sql)
    if relation_exists("public.cache_reposicao_resumo"):
        row = fetch_one("SELECT COUNT(*) AS total FROM cache_reposicao_resumo;")
        if row and row["total"]:
            return "cache_reposicao_resumo"
    raise HTTPException(
        status_code=503,
        detail="Tabela extrato_reposicao_loja_perm_analitico ainda nao existe.",
    )


def cache_summary_table() -> str:
    if relation_exists("public.cache_reposicao_resumo"):
        return "cache_reposicao_resumo"
    raise HTTPException(status_code=503, detail="Cache ainda nao foi criado.")


def source_analytic_table() -> str:
    if relation_exists("public.cache_reposicao_analitico_classificado"):
        row = fetch_one("SELECT COUNT(*) AS total FROM cache_reposicao_analitico_classificado;")
        if row and row["total"]:
            return "cache_reposicao_analitico_classificado"
    if relation_exists("public.extrato_reposicao_loja_perm_analitico"):
        return "extrato_reposicao_loja_perm_analitico"
    raise HTTPException(
        status_code=503,
        detail="Tabela extrato_reposicao_loja_perm_analitico ainda nao existe.",
    )


def scope_filter_sql(
    alias: str,
    *,
    cd_loja: int | None = None,
    referencia: str | None = None,
    somente_entrada_sem_necessidade: bool | None = None,
) -> tuple[str, dict[str, Any]]:
    filters: list[str] = []
    params: dict[str, Any] = {}
    if cd_loja is not None:
        filters.append(f"AND {alias}.cd_loja = %(cd_loja)s")
        params["cd_loja"] = cd_loja
    if referencia:
        filters.append(f"AND {alias}.referencia ILIKE %(referencia)s")
        params["referencia"] = f"%{referencia.strip()}%"
    if somente_entrada_sem_necessidade:
        filters.append(f"AND {alias}.necessidade <= 0 AND {alias}.entrada_total > 0")
    return "\n".join(filters), params


MONTHS_YEAR_CTE = """
WITH meses AS (
    SELECT
        to_char(mes_inicio, 'YYYY-MM') AS mes,
        mes_inicio::date AS inicio_mes,
        (mes_inicio + INTERVAL '1 month')::date AS fim_mes,
        to_char(mes_inicio, 'YY.MM') || '%%' AS lote_periodo
    FROM generate_series(
        make_date(%(year)s, 1, 1),
        make_date(%(year)s, 12, 1),
        INTERVAL '1 month'
    ) AS mes_inicio
)
"""

MONTHS_SINGLE_CTE = """
WITH meses AS (
    SELECT
        %(month)s::text AS mes,
        (%(month)s::text || '-01')::date AS inicio_mes,
        ((%(month)s::text || '-01')::date + INTERVAL '1 month')::date AS fim_mes,
        to_char((%(month)s::text || '-01')::date, 'YY.MM') || '%%' AS lote_periodo
)
"""

BASE_ANALITICA_REST = """
,
produtos_permanente AS (
    SELECT DISTINCT pc.cd_produto
    FROM prd_produtoclas pc
    JOIN prd_classificacao c
        ON pc.cd_classificacao = c.cd_classificacao
        AND pc.cd_tipoclas = c.cd_tipoclas
    WHERE pc.cd_tipoclas = 802
      AND c.ds_classificacao IN ('PERMANENTE', 'PERMANENTE COR NOVA')
),
entradas_mes AS (
    SELECT
        m.mes,
        t.cd_empresa AS cd_loja,
        i.cd_produto,
        i.qt_solicitada AS qt_entrada,
        t.nr_transacao,
        i.dt_transacao,
        lote.cd_lote,
        CASE
            WHEN t.cd_empresaori <> 1 THEN 'PERIODO'
            WHEN lote.cd_lote LIKE m.lote_periodo THEN 'PERIODO'
            ELSE 'ATRASADA'
        END AS tipo_entrada
    FROM meses m
    JOIN vr_tra_transacao t
        ON TRUE
    JOIN vr_tra_transitem i
        ON t.nr_transacao = i.nr_transacao
        AND t.cd_empresa = i.cd_empresa
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
),
entradas_agregadas AS (
    SELECT
        mes,
        cd_loja,
        cd_produto,
        COALESCE(SUM(qt_entrada) FILTER (WHERE tipo_entrada = 'PERIODO'), 0) AS entrada_periodo,
        COALESCE(SUM(qt_entrada) FILTER (WHERE tipo_entrada = 'ATRASADA'), 0) AS entrada_atrasada,
        COALESCE(SUM(qt_entrada), 0) AS entrada_total,
        COUNT(DISTINCT nr_transacao) FILTER (WHERE tipo_entrada = 'PERIODO') AS qtd_transacoes_periodo,
        COUNT(DISTINCT nr_transacao) FILTER (WHERE tipo_entrada = 'ATRASADA') AS qtd_transacoes_atrasadas,
        MIN(dt_transacao) AS primeira_entrada,
        MAX(dt_transacao) AS ultima_entrada,
        STRING_AGG(DISTINCT cd_lote, ', ' ORDER BY cd_lote) AS lotes_entrada
    FROM entradas_mes
    GROUP BY mes, cd_loja, cd_produto
),
vendas_3m AS (
    SELECT
        m.mes,
        m.inicio_mes,
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
    GROUP BY m.mes, m.inicio_mes, t.cd_empresa, i.cd_produto
    HAVING SUM(
        i.qt_solicitada *
        CASE WHEN t.tp_modalidade::text = '3' THEN -1 ELSE 1 END
    ) > 0
),
base_sem_curva AS (
    SELECT
        v.mes,
        v.inicio_mes,
        v.cd_loja,
        emp.nm_grupoempresa AS nome_loja,
        v.cd_produto,
        f_dic_prd_nivel(v.cd_produto, 'CD'::bpchar) AS referencia,
        f_dic_prd_nivel(v.cd_produto, 'DS'::bpchar) AS descricao_produto,
        v.vendas_3m,
        ROUND(v.vendas_3m / 3.0, 2) AS media_mensal,
        ROUND(v.vendas_3m / 3.0 * 1.5, 0) AS estoque_minimo,
        COALESCE(
            f_prd_saldo_produto(
                v.cd_loja,
                1::bigint,
                v.cd_produto,
                v.inicio_mes
            ),
            0
        ) AS saldo_inicial
    FROM vendas_3m v
    JOIN vr_ger_empresa emp
        ON v.cd_loja = emp.cd_empresa
    JOIN produtos_permanente pp
        ON v.cd_produto = pp.cd_produto
),
base AS (
    SELECT
        b.*,
        COALESCE(abc.curva_completa, 'SEM CURVA') AS curva_completa
    FROM base_sem_curva b
    LEFT JOIN curva_abc abc
        ON abc.referencia = b.referencia
),
analitico AS (
    SELECT
        b.mes,
        b.inicio_mes,
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
        COALESCE(e.entrada_atrasada, 0) AS entrada_atrasada,
        COALESCE(e.entrada_total, 0) AS entrada_total,
        COALESCE(e.qtd_transacoes_periodo, 0) AS qtd_transacoes_periodo,
        COALESCE(e.qtd_transacoes_atrasadas, 0) AS qtd_transacoes_atrasadas,
        e.primeira_entrada,
        e.ultima_entrada,
        e.lotes_entrada
    FROM base b
    LEFT JOIN entradas_agregadas e
        ON b.mes = e.mes
        AND b.cd_loja = e.cd_loja
        AND b.cd_produto = e.cd_produto
),
analitico_status AS (
    SELECT
        *,
        GREATEST(0, necessidade - entrada_periodo) AS faltou_periodo,
        GREATEST(0, entrada_periodo - necessidade) AS sobra_periodo,
        CASE
            WHEN necessidade <= 0 THEN 'SEM NECESSIDADE'
            WHEN entrada_periodo >= necessidade THEN 'OK'
            WHEN entrada_periodo > 0 THEN 'PARCIAL'
            ELSE 'ZERADO'
        END AS status_reposicao,
        CASE
            WHEN entrada_atrasada > 0 AND entrada_periodo > 0 THEN 'PERIODO + ATRASADA'
            WHEN entrada_atrasada > 0 THEN 'SOMENTE ATRASADA'
            WHEN entrada_periodo > 0 THEN 'SOMENTE PERIODO'
            ELSE 'SEM ENTRADA'
        END AS status_entrada
    FROM analitico
)
"""


def analysis_cte(month_scoped: bool = False) -> str:
    return (MONTHS_SINGLE_CTE if month_scoped else MONTHS_YEAR_CTE) + BASE_ANALITICA_REST


LIGHT_ANALITICA_REST = """
,
produtos_permanente AS (
    SELECT DISTINCT pc.cd_produto
    FROM prd_produtoclas pc
    JOIN prd_classificacao c
        ON pc.cd_classificacao = c.cd_classificacao
        AND pc.cd_tipoclas = c.cd_tipoclas
    WHERE pc.cd_tipoclas = 802
      AND c.ds_classificacao IN ('PERMANENTE', 'PERMANENTE COR NOVA')
),
entradas_mes AS (
    SELECT
        m.mes,
        t.cd_empresa AS cd_loja,
        i.cd_produto,
        i.qt_solicitada AS qt_entrada,
        CASE
            WHEN t.cd_empresaori <> 1 THEN 'PERIODO'
            WHEN lote.cd_lote LIKE m.lote_periodo THEN 'PERIODO'
            ELSE 'ATRASADA'
        END AS tipo_entrada
    FROM meses m
    JOIN vr_tra_transacao t
        ON TRUE
    JOIN vr_tra_transitem i
        ON t.nr_transacao = i.nr_transacao
        AND t.cd_empresa = i.cd_empresa
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
),
entradas_agregadas AS (
    SELECT
        mes,
        cd_loja,
        cd_produto,
        COALESCE(SUM(qt_entrada) FILTER (WHERE tipo_entrada = 'PERIODO'), 0) AS entrada_periodo,
        COALESCE(SUM(qt_entrada) FILTER (WHERE tipo_entrada = 'ATRASADA'), 0) AS entrada_atrasada,
        COALESCE(SUM(qt_entrada), 0) AS entrada_total
    FROM entradas_mes
    GROUP BY mes, cd_loja, cd_produto
),
vendas_3m AS (
    SELECT
        m.mes,
        m.inicio_mes,
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
    GROUP BY m.mes, m.inicio_mes, t.cd_empresa, i.cd_produto
    HAVING SUM(
        i.qt_solicitada *
        CASE WHEN t.tp_modalidade::text = '3' THEN -1 ELSE 1 END
    ) > 0
),
saldos_iniciais AS (
    SELECT DISTINCT ON (v.mes, v.cd_loja, v.cd_produto)
        v.mes,
        v.cd_loja,
        v.cd_produto,
        s.qt_saldo AS saldo_inicial
    FROM vendas_3m v
    JOIN prd_prdsaldo s
        ON s.cd_empresa = v.cd_loja
        AND s.cd_produto = v.cd_produto
        AND s.cd_saldo = 1
        AND s.dt_saldo <= v.inicio_mes
    ORDER BY v.mes, v.cd_loja, v.cd_produto, s.dt_saldo DESC
),
analitico_base AS (
    SELECT
        v.mes,
        v.cd_loja,
        emp.nm_grupoempresa AS nome_loja,
        v.cd_produto,
        GREATEST(
            0,
            ROUND(v.vendas_3m / 3.0 * 1.5, 0) -
            COALESCE(si.saldo_inicial, 0)
        ) AS necessidade,
        COALESCE(e.entrada_periodo, 0) AS entrada_periodo,
        COALESCE(e.entrada_atrasada, 0) AS entrada_atrasada,
        COALESCE(e.entrada_total, 0) AS entrada_total
    FROM vendas_3m v
    JOIN vr_ger_empresa emp
        ON v.cd_loja = emp.cd_empresa
    JOIN produtos_permanente pp
        ON v.cd_produto = pp.cd_produto
    LEFT JOIN entradas_agregadas e
        ON v.mes = e.mes
        AND v.cd_loja = e.cd_loja
        AND v.cd_produto = e.cd_produto
    LEFT JOIN saldos_iniciais si
        ON v.mes = si.mes
        AND v.cd_loja = si.cd_loja
        AND v.cd_produto = si.cd_produto
),
analitico_status AS (
    SELECT
        *,
        GREATEST(0, necessidade - entrada_periodo) AS faltou_periodo,
        GREATEST(0, entrada_periodo - necessidade) AS sobra_periodo,
        CASE
            WHEN necessidade <= 0 THEN 'SEM NECESSIDADE'
            WHEN entrada_periodo >= necessidade THEN 'OK'
            WHEN entrada_periodo > 0 THEN 'PARCIAL'
            ELSE 'ZERADO'
        END AS status_reposicao
    FROM analitico_base
)
"""


def light_cte(month_scoped: bool = False) -> str:
    return (MONTHS_SINGLE_CTE if month_scoped else MONTHS_YEAR_CTE) + LIGHT_ANALITICA_REST


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/analysis/monthly")
def monthly_analysis(year: int = Query(default=2026, ge=2020, le=2035)):
    query = """
    SELECT
        mes,
        SUM(necessidade) AS necessidade,
        SUM(entrada_periodo) AS entrada_periodo,
        SUM(entrada_atrasada) AS entrada_atrasada,
        SUM(entrada_total) AS entrada_total,
        SUM(faltou) AS faltou_periodo,
        SUM(GREATEST(0, entrada_periodo - necessidade)) AS sobra_periodo,
        SUM(skus_demanda) AS skus_demanda,
        SUM(skus_ok) AS skus_ok,
        SUM(skus_parcial) AS skus_parcial,
        SUM(skus_zerados) AS skus_zerados,
        ROUND(100.0 * SUM(skus_ok) / NULLIF(SUM(skus_demanda), 0), 1) AS pct_ok
    FROM extrato_reposicao_loja_perm
    WHERE mes LIKE %(year_like)s
    GROUP BY mes
    ORDER BY mes;
    """
    return fetch_all(query, {"year": year, "year_like": f"{year}-%"})


@app.get("/api/analysis/stores")
def store_analysis(
    year: int = Query(default=2026, ge=2020, le=2035),
    month: str | None = Query(default=None, pattern=r"^\d{4}-\d{2}$"),
):
    where = "WHERE e.mes = %(month)s" if month else "WHERE e.mes LIKE %(year_like)s"
    params: dict[str, Any] = {"year": year}
    if month:
        params["month"] = month
    else:
        params["year_like"] = f"{year}-%"

    query = f"""
    SELECT
        mes,
        cd_loja,
        nome_loja,
        necessidade,
        entrada_periodo,
        entrada_atrasada,
        entrada_total,
        faltou AS faltou_periodo,
        skus_demanda,
        skus_ok,
        skus_parcial,
        skus_zerados,
        pct_ok
    FROM extrato_reposicao_loja_perm e
    {where}
    ORDER BY mes, faltou DESC, cd_loja;
    """
    return fetch_all(query, params)


@app.get("/api/analysis/products")
def product_analysis(
    year: int = Query(default=2026, ge=2020, le=2035),
    month: str = Query(default="2026-06", pattern=r"^\d{4}-\d{2}$"),
    limit: int = Query(default=200, ge=1, le=1000),
    status: str | None = Query(default=None),
):
    params: dict[str, Any] = {"year": year, "month": month, "limit": limit}
    status_filter = ""
    if status and status != "TODOS":
        params["status"] = status
        status_filter = "AND status_reposicao = %(status)s"

    query = analysis_cte(month_scoped=True) + f"""
    SELECT
        mes,
        cd_loja,
        nome_loja,
        cd_produto,
        referencia,
        descricao_produto,
        curva_completa,
        vendas_3m,
        media_mensal,
        estoque_minimo,
        saldo_inicial,
        necessidade,
        entrada_periodo,
        entrada_atrasada,
        entrada_total,
        faltou_periodo,
        sobra_periodo,
        status_reposicao,
        status_entrada,
        primeira_entrada,
        ultima_entrada,
        lotes_entrada
    FROM analitico_status
    WHERE mes = %(month)s
      {status_filter}
    ORDER BY faltou_periodo DESC, entrada_atrasada DESC, nome_loja, referencia
    LIMIT %(limit)s;
    """
    return fetch_all(query, params)


@app.get("/api/pending/current")
def current_pending(limit: int = Query(default=500, ge=1, le=2000)):
    query = """
    WITH produtos_permanente AS (
        SELECT DISTINCT pc.cd_produto
        FROM prd_produtoclas pc
        JOIN prd_classificacao c
            ON pc.cd_classificacao = c.cd_classificacao
            AND pc.cd_tipoclas = c.cd_tipoclas
        WHERE pc.cd_tipoclas = 802
          AND c.ds_classificacao IN ('PERMANENTE', 'PERMANENTE COR NOVA')
    ),
    pendentes AS (
        SELECT
            pi.cd_produto,
            f_dic_prd_nivel(pi.cd_produto, 'CD'::bpchar) AS referencia,
            f_dic_prd_nivel(pi.cd_produto, 'DS'::bpchar) AS descricao_produto,
            COALESCE(abc.curva_completa, 'SEM CURVA') AS curva_completa,
            SUM(pi.qt_pendente) AS qt_pendente,
            COUNT(DISTINCT pi.cd_pedido) AS qtd_pedidos
        FROM vr_ped_pedidoi pi
        JOIN produtos_permanente pp
            ON pi.cd_produto = pp.cd_produto
        LEFT JOIN curva_abc abc
            ON abc.referencia = f_dic_prd_nivel(pi.cd_produto, 'CD'::bpchar)
        WHERE pi.cd_empresa = 1
          AND pi.cd_operacao <> 44
          AND pi.tp_situacao <> 6
          AND pi.qt_pendente > 0
        GROUP BY pi.cd_produto, referencia, descricao_produto, curva_completa
    )
    SELECT *
    FROM pendentes
    ORDER BY qt_pendente DESC, referencia
    LIMIT %(limit)s;
    """
    return fetch_all(query, {"limit": limit})


@app.get("/api/summary")
def summary(year: int = Query(default=2026, ge=2020, le=2035)):
    monthly_query = """
    SELECT
        SUM(necessidade) AS necessidade,
        SUM(entrada_periodo) AS entrada_periodo,
        SUM(entrada_atrasada) AS entrada_atrasada,
        SUM(entrada_total) AS entrada_total,
        SUM(faltou) AS faltou_periodo,
        SUM(skus_demanda) AS skus_demanda,
        SUM(skus_ok) AS skus_ok,
        COUNT(DISTINCT mes) AS meses_base,
        MIN(mes) AS primeiro_mes,
        MAX(mes) AS ultimo_mes
    FROM extrato_reposicao_loja_perm
    WHERE mes LIKE %(year_like)s;
    """
    pending_query = """
    SELECT COALESCE(SUM(qt_pendente), 0) AS pedidos_pendentes
    FROM vr_ped_pedidoi
    WHERE cd_empresa = 1
      AND cd_operacao <> 44
      AND tp_situacao <> 6
      AND qt_pendente > 0;
    """
    totals = fetch_all(monthly_query, {"year": year, "year_like": f"{year}-%"})[0]
    pending = fetch_all(pending_query)[0]
    return {**totals, **pending}


CACHE_STATUS: dict[str, Any] = {
    "status": "nunca_atualizado",
    "iniciado_em": None,
    "finalizado_em": None,
    "erro": None,
}


CACHE_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS reposicao_config (
    chave TEXT PRIMARY KEY,
    valor TEXT NOT NULL,
    atualizado_em TIMESTAMP DEFAULT NOW()
);

INSERT INTO reposicao_config (chave, valor)
VALUES
    ('meses_media', '3'),
    ('multiplicador_estoque_minimo', '1.5')
ON CONFLICT (chave) DO NOTHING;

CREATE TABLE IF NOT EXISTS cache_reposicao_resumo (
    id SERIAL PRIMARY KEY,
    mes VARCHAR(7),
    cd_loja BIGINT,
    nome_loja VARCHAR(100),
    qtd_skus INTEGER DEFAULT 0,
    qtd_skus_demanda INTEGER DEFAULT 0,
    estoque_minimo_total NUMERIC DEFAULT 0,
    saldo_inicial_total NUMERIC DEFAULT 0,
    necessidade_total NUMERIC DEFAULT 0,
    entrada_periodo NUMERIC DEFAULT 0,
    entrada_atrasada NUMERIC DEFAULT 0,
    entrada_sem_lote NUMERIC DEFAULT 0,
    entrada_total NUMERIC DEFAULT 0,
    faltou NUMERIC DEFAULT 0,
    taxa_atendimento NUMERIC DEFAULT 100,
    skus_ok INTEGER DEFAULT 0,
    skus_parcial INTEGER DEFAULT 0,
    skus_zerados INTEGER DEFAULT 0,
    skus_sem_necessidade INTEGER DEFAULT 0,
    atualizado_em TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_cache_reposicao_resumo_mes_loja
    ON cache_reposicao_resumo (mes, cd_loja);

CREATE TABLE IF NOT EXISTS cache_skus_mortos (
    cd_produto BIGINT,
    cd_loja BIGINT,
    nome_loja VARCHAR(100),
    referencia VARCHAR(50),
    descricao_produto TEXT,
    curva_original VARCHAR(50),
    ultimo_mes_com_venda VARCHAR(7),
    ultimo_mes_com_estoque VARCHAR(7),
    meses_sem_estoque INTEGER,
    vendas_historico NUMERIC,
    status TEXT,
    atualizado_em TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_cache_skus_mortos_loja_ref
    ON cache_skus_mortos (cd_loja, referencia);

CREATE TABLE IF NOT EXISTS cache_evolucao_mensal (
    mes VARCHAR(7),
    cd_loja BIGINT,
    necessidade NUMERIC DEFAULT 0,
    entrada_total NUMERIC DEFAULT 0,
    faltou NUMERIC DEFAULT 0,
    gap_acumulado NUMERIC DEFAULT 0,
    taxa_atendimento NUMERIC DEFAULT 100,
    atualizado_em TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_cache_evolucao_mensal_mes_loja
    ON cache_evolucao_mensal (mes, cd_loja);

-- Tabelas de acompanhamento de pedidos de reposição
CREATE TABLE IF NOT EXISTS reposicao_pedidos (
    id SERIAL PRIMARY KEY,
    order_id VARCHAR(100) UNIQUE NOT NULL,
    pedido_tipo VARCHAR(20) NOT NULL,
    mes VARCHAR(7) NOT NULL,
    cd_loja BIGINT NOT NULL,
    nome_loja VARCHAR(100),
    total_skus INTEGER DEFAULT 0,
    total_pecas NUMERIC DEFAULT 0,
    total_valor NUMERIC(12,2) DEFAULT 0,
    status VARCHAR(30) DEFAULT 'GERADO',
    totvs_order_number VARCHAR(50),
    totvs_response JSONB,
    criado_em TIMESTAMP DEFAULT NOW(),
    atualizado_em TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_reposicao_pedidos_mes ON reposicao_pedidos (mes);
CREATE INDEX IF NOT EXISTS idx_reposicao_pedidos_loja ON reposicao_pedidos (cd_loja);
CREATE INDEX IF NOT EXISTS idx_reposicao_pedidos_status ON reposicao_pedidos (status);

CREATE TABLE IF NOT EXISTS reposicao_pedido_itens (
    id SERIAL PRIMARY KEY,
    pedido_id INTEGER REFERENCES reposicao_pedidos(id) ON DELETE CASCADE,
    cd_produto BIGINT NOT NULL,
    referencia VARCHAR(50),
    descricao VARCHAR(200),
    cor VARCHAR(50),
    tamanho VARCHAR(20),
    curva_completa VARCHAR(30),
    quantidade NUMERIC NOT NULL,
    preco NUMERIC(12,2),
    status VARCHAR(30) DEFAULT 'GERADO',
    media_mensal NUMERIC,
    estoque_minimo NUMERIC,
    saldo_inicial NUMERIC,
    necessidade NUMERIC,
    entrada_total NUMERIC,
    qtd_ja_programada NUMERIC,
    observacao TEXT,
    atualizado_em TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_reposicao_itens_pedido ON reposicao_pedido_itens (pedido_id);
CREATE INDEX IF NOT EXISTS idx_reposicao_itens_status ON reposicao_pedido_itens (status);
CREATE INDEX IF NOT EXISTS idx_reposicao_itens_produto ON reposicao_pedido_itens (cd_produto);

CREATE TABLE IF NOT EXISTS reposicao_pedido_historico (
    id SERIAL PRIMARY KEY,
    pedido_id INTEGER REFERENCES reposicao_pedidos(id) ON DELETE CASCADE,
    item_id INTEGER REFERENCES reposicao_pedido_itens(id) ON DELETE CASCADE,
    status_anterior VARCHAR(30),
    status_novo VARCHAR(30) NOT NULL,
    usuario VARCHAR(100),
    observacao TEXT,
    criado_em TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_reposicao_historico_pedido ON reposicao_pedido_historico (pedido_id);
CREATE INDEX IF NOT EXISTS idx_reposicao_historico_item ON reposicao_pedido_historico (item_id);
"""


def ensure_cache_schema() -> None:
    execute_transaction(
        [
            ("SELECT pg_advisory_xact_lock(2026081001);", None),
            (CACHE_SCHEMA_SQL, None),
        ]
    )


def refresh_cache(month: str | None = None) -> dict[str, Any]:
    ensure_cache_schema()
    CACHE_STATUS.update(
        {
            "status": "processando",
            "iniciado_em": datetime.now().isoformat(),
            "finalizado_em": None,
            "erro": None,
        }
    )

    params: dict[str, Any] = {}
    month_filter = ""
    delete_filter = ""
    if month:
        params["month"] = month
        month_filter = "WHERE mes = %(month)s"
        delete_filter = "WHERE mes = %(month)s"

    try:
        execute_transaction(
            [
                ("DROP TABLE IF EXISTS cache_reposicao_analitico_classificado;", None),
                (
                    f"""
                    CREATE TABLE cache_reposicao_analitico_classificado AS
                    WITH base_cache AS (
                        SELECT *
                        FROM extrato_reposicao_loja_perm_analitico
                        {month_filter}
                    ),
                    base_skus AS (
                        SELECT DISTINCT cd_loja, cd_produto
                        FROM base_cache
                    ),
                    entradas_historicas AS (
                        SELECT
                            t.cd_empresa AS cd_loja,
                            i.cd_produto,
                            i.dt_transacao::date AS data_entrada,
                            SUM(i.qt_solicitada) AS quantidade_entrada
                        FROM base_skus bs
                        JOIN vr_tra_transacao t
                            ON t.cd_empresa = bs.cd_loja
                        JOIN vr_tra_transitem i
                            ON i.nr_transacao = t.nr_transacao
                           AND i.cd_empresa = t.cd_empresa
                           AND i.cd_produto = bs.cd_produto
                        WHERE t.tp_operacao = 'E'
                          AND t.tp_situacao = 4
                          AND i.dt_transacao::date <= CURRENT_DATE
                        GROUP BY t.cd_empresa, i.cd_produto, i.dt_transacao::date
                    ),
                    ultima_entrada AS (
                        SELECT DISTINCT ON (cd_loja, cd_produto)
                            cd_loja,
                            cd_produto,
                            data_entrada AS data_ultima_entrada_historica,
                            quantidade_entrada AS quantidade_ultima_entrada_historica
                        FROM entradas_historicas
                        ORDER BY cd_loja, cd_produto, data_entrada DESC
                    )
                    SELECT
                        a.*,
                        cls.status_produto,
                        cls.continuidade,
                        cls.linha,
                        cls.familia,
                        COALESCE(p.ds_cor, '') AS cor,
                        COALESCE(p.ds_tamanho, '') AS tamanho,
                        ue.data_ultima_entrada_historica,
                        COALESCE(ue.quantidade_ultima_entrada_historica, 0) AS quantidade_ultima_entrada_historica,
                        NOW() AS cache_atualizado_em
                    FROM base_cache a
                    LEFT JOIN vr_prd_prdgrade p
                        ON p.cd_produto = a.cd_produto
                    LEFT JOIN ultima_entrada ue
                        ON ue.cd_loja = a.cd_loja
                       AND ue.cd_produto = a.cd_produto
                    LEFT JOIN LATERAL (
                        SELECT
                            {product_classification_select("a")}
                    ) cls ON TRUE;
                    """,
                    params,
                ),
                (
                    """
                    CREATE INDEX idx_cache_reposicao_analitico_mes_loja
                        ON cache_reposicao_analitico_classificado (mes, cd_loja);
                    CREATE INDEX idx_cache_reposicao_analitico_produto
                        ON cache_reposicao_analitico_classificado (cd_produto);
                    CREATE INDEX idx_cache_reposicao_analitico_classificacoes
                        ON cache_reposicao_analitico_classificado (
                            status_produto, continuidade, linha, familia, mes
                        );
                    CREATE INDEX idx_cache_reposicao_analitico_ref
                        ON cache_reposicao_analitico_classificado (referencia, cor, tamanho);
                    """,
                    None,
                ),
                (f"DELETE FROM cache_reposicao_resumo {delete_filter};", params),
                (
                    f"""
                    INSERT INTO cache_reposicao_resumo (
                        mes, cd_loja, nome_loja, qtd_skus, qtd_skus_demanda,
                        estoque_minimo_total, saldo_inicial_total,
                        necessidade_total, entrada_periodo, entrada_atrasada,
                        entrada_sem_lote, entrada_total, faltou, taxa_atendimento,
                        skus_ok, skus_parcial, skus_zerados, skus_sem_necessidade, atualizado_em
                    )
                    SELECT
                        mes,
                        cd_loja,
                        MAX(nome_loja) AS nome_loja,
                        COUNT(*) AS qtd_skus,
                        COUNT(*) FILTER (WHERE necessidade > 0) AS qtd_skus_demanda,
                        SUM(estoque_minimo) AS estoque_minimo_total,
                        SUM(saldo_inicial) AS saldo_inicial_total,
                        SUM(necessidade) AS necessidade_total,
                        SUM(entrada_periodo) AS entrada_periodo,
                        SUM(entrada_atrasada) AS entrada_atrasada,
                        SUM(entrada_sem_lote) AS entrada_sem_lote,
                        SUM(entrada_total) AS entrada_total,
                        SUM(faltou) AS faltou,
                        CASE
                            WHEN SUM(necessidade) > 0
                            THEN ROUND(SUM(entrada_total)::numeric / SUM(necessidade)::numeric * 100, 1)
                            ELSE 100
                        END AS taxa_atendimento,
                        COUNT(*) FILTER (WHERE status_reposicao = 'OK') AS skus_ok,
                        COUNT(*) FILTER (WHERE status_reposicao = 'PARCIAL') AS skus_parcial,
                        COUNT(*) FILTER (WHERE status_reposicao IN ('ZERADO', 'SEM ENTRADA')) AS skus_zerados,
                        COUNT(*) FILTER (WHERE status_reposicao = 'SEM NECESSIDADE') AS skus_sem_necessidade,
                        NOW()
                    FROM cache_reposicao_analitico_classificado
                    {month_filter}
                    GROUP BY mes, cd_loja;
                    """,
                    params,
                ),
                (f"DELETE FROM cache_evolucao_mensal {delete_filter};", params),
                (
                    f"""
                    INSERT INTO cache_evolucao_mensal (
                        mes, cd_loja, necessidade, entrada_total, faltou,
                        gap_acumulado, taxa_atendimento, atualizado_em
                    )
                    SELECT
                        mes,
                        cd_loja,
                        necessidade_total,
                        entrada_total,
                        faltou,
                        SUM(faltou) OVER (
                            PARTITION BY cd_loja
                            ORDER BY mes
                            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
                        ) AS gap_acumulado,
                        taxa_atendimento,
                        NOW()
                    FROM cache_reposicao_resumo
                    {month_filter};
                    """,
                    params,
                ),
            ]
        )

        if relation_exists("public.extrato_reposicao_loja_perm_analitico"):
            sku_params = {"month": month} if month else {}
            sku_filter = "WHERE mes = %(month)s" if month else ""
            execute_transaction(
                [
                    ("DELETE FROM cache_skus_mortos;", None),
                    (
                        f"""
                        INSERT INTO cache_skus_mortos (
                            cd_produto, cd_loja, nome_loja, referencia, descricao_produto,
                            curva_original, ultimo_mes_com_venda, ultimo_mes_com_estoque,
                            meses_sem_estoque, vendas_historico, status, atualizado_em
                        )
                        WITH historico AS (
                            SELECT
                                cd_produto,
                                cd_loja,
                                MAX(nome_loja) AS nome_loja,
                                MAX(referencia) AS referencia,
                                MAX(descricao_produto) AS descricao_produto,
                                MAX(curva_completa) AS curva_original,
                                MAX(mes) FILTER (WHERE COALESCE(vendas_3m, 0) > 0) AS ultimo_mes_com_venda,
                                MAX(mes) FILTER (WHERE COALESCE(saldo_inicial, 0) > 0) AS ultimo_mes_com_estoque,
                                SUM(COALESCE(vendas_3m, 0)) AS vendas_historico,
                                MAX(mes) AS ultimo_mes_base
                            FROM extrato_reposicao_loja_perm_analitico
                            {sku_filter}
                            GROUP BY cd_produto, cd_loja
                        )
                        SELECT
                            cd_produto,
                            cd_loja,
                            nome_loja,
                            referencia,
                            descricao_produto,
                            curva_original,
                            ultimo_mes_com_venda,
                            ultimo_mes_com_estoque,
                            GREATEST(
                                0,
                                (
                                    EXTRACT(YEAR FROM AGE(
                                        TO_DATE(ultimo_mes_base || '-01', 'YYYY-MM-DD'),
                                        TO_DATE(ultimo_mes_com_estoque || '-01', 'YYYY-MM-DD')
                                    )) * 12
                                    + EXTRACT(MONTH FROM AGE(
                                        TO_DATE(ultimo_mes_base || '-01', 'YYYY-MM-DD'),
                                        TO_DATE(ultimo_mes_com_estoque || '-01', 'YYYY-MM-DD')
                                    ))
                                )::int
                            ) AS meses_sem_estoque,
                            vendas_historico,
                            CASE
                                WHEN curva_original IN ('CURVA A', 'CURVA AA') THEN 'CRITICO'
                                ELSE 'MORTO'
                            END AS status,
                            NOW()
                        FROM historico
                        WHERE ultimo_mes_com_venda IS NOT NULL
                          AND ultimo_mes_com_estoque IS NOT NULL
                          AND curva_original IN ('CURVA A', 'CURVA AA', 'CURVA B')
                          AND ultimo_mes_com_estoque < ultimo_mes_base;
                        """,
                        sku_params,
                    ),
                ]
            )

        CACHE_STATUS.update(
            {"status": "ok", "finalizado_em": datetime.now().isoformat(), "erro": None}
        )
        meta = fetch_one(
            """
            SELECT
                COUNT(*) AS registros_resumo,
                MIN(mes) AS primeiro_mes,
                MAX(mes) AS ultimo_mes,
                MAX(atualizado_em) AS atualizado_em
            FROM cache_reposicao_resumo;
            """
        )
        return {"status": "ok", **(meta or {})}
    except HTTPException as exc:
        CACHE_STATUS.update(
            {
                "status": "erro",
                "finalizado_em": datetime.now().isoformat(),
                "erro": exc.detail,
            }
        )
        raise


@app.get("/api/config/meses-relevantes")
def get_meses_relevantes():
    ensure_cache_schema()
    rows = fetch_all("SELECT chave, valor, atualizado_em FROM reposicao_config ORDER BY chave;")
    values = {row["chave"]: row["valor"] for row in rows}
    return {
        "meses_media": int(values.get("meses_media", 3)),
        "multiplicador_estoque_minimo": float(values.get("multiplicador_estoque_minimo", 1.5)),
        "multiplicador_curva_aa": float(values.get("multiplicador_curva_aa", 1.5)),
        "multiplicador_curva_a": float(values.get("multiplicador_curva_a", 1.5)),
        "multiplicador_curva_b": float(values.get("multiplicador_curva_b", 1.0)),
        "multiplicador_curva_c": float(values.get("multiplicador_curva_c", 1.0)),
        "modo_meses": values.get("modo_meses", "ultimos_3"),
        "meses_selecionados": [mes for mes in values.get("meses_selecionados", "").split(",") if mes],
        "config": rows,
    }


@app.post("/api/config/meses-relevantes")
def save_meses_relevantes(payload: dict[str, Any] = Body(...)):
    ensure_cache_schema()
    meses_media = int(payload.get("meses_media", 3))
    multiplicador = float(payload.get("multiplicador_estoque_minimo", 1.5))
    multiplicador_curva_aa = float(payload.get("multiplicador_curva_aa", 1.5))
    multiplicador_curva_a = float(payload.get("multiplicador_curva_a", 1.5))
    multiplicador_curva_b = float(payload.get("multiplicador_curva_b", 1.0))
    multiplicador_curva_c = float(payload.get("multiplicador_curva_c", 1.0))
    modo_meses = str(payload.get("modo_meses", "ultimos_3"))
    meses_selecionados_payload = payload.get("meses_selecionados") or []
    meses_selecionados = ",".join(str(mes) for mes in meses_selecionados_payload)
    if meses_media < 1 or meses_media > 12:
        raise HTTPException(status_code=422, detail="meses_media deve ficar entre 1 e 12.")
    multiplicadores = [
        multiplicador,
        multiplicador_curva_aa,
        multiplicador_curva_a,
        multiplicador_curva_b,
        multiplicador_curva_c,
    ]
    if any(value <= 0 for value in multiplicadores):
        raise HTTPException(status_code=422, detail="Multiplicadores devem ser positivos.")
    execute_transaction(
        [
            (
                """
                INSERT INTO reposicao_config (chave, valor, atualizado_em)
                VALUES
                    ('meses_media', %(meses_media)s, NOW()),
                    ('multiplicador_estoque_minimo', %(multiplicador)s, NOW()),
                    ('multiplicador_curva_aa', %(multiplicador_curva_aa)s, NOW()),
                    ('multiplicador_curva_a', %(multiplicador_curva_a)s, NOW()),
                    ('multiplicador_curva_b', %(multiplicador_curva_b)s, NOW()),
                    ('multiplicador_curva_c', %(multiplicador_curva_c)s, NOW()),
                    ('modo_meses', %(modo_meses)s, NOW()),
                    ('meses_selecionados', %(meses_selecionados)s, NOW())
                ON CONFLICT (chave)
                DO UPDATE SET valor = EXCLUDED.valor, atualizado_em = NOW();
                """,
                {
                    "meses_media": str(meses_media),
                    "multiplicador": str(multiplicador),
                    "multiplicador_curva_aa": str(multiplicador_curva_aa),
                    "multiplicador_curva_a": str(multiplicador_curva_a),
                    "multiplicador_curva_b": str(multiplicador_curva_b),
                    "multiplicador_curva_c": str(multiplicador_curva_c),
                    "modo_meses": modo_meses,
                    "meses_selecionados": meses_selecionados,
                },
            )
        ]
    )
    return get_meses_relevantes()


@app.get("/api/config/ultima-atualizacao")
def ultima_atualizacao():
    ensure_cache_schema()
    return fetch_one(
        """
        SELECT
            MAX(atualizado_em) AS atualizado_em,
            COUNT(*) AS registros_resumo,
            MIN(mes) AS primeiro_mes,
            MAX(mes) AS ultimo_mes
        FROM cache_reposicao_resumo;
        """
    )


@app.get("/api/filtros/classificacoes")
def filtros_classificacoes():
    rows = fetch_all(
        """
        SELECT
            pc.cd_tipoclas,
            c.ds_classificacao AS valor,
            COUNT(DISTINCT pc.cd_produto) AS qtd_produtos
        FROM prd_produtoclas pc
        JOIN prd_classificacao c
            ON c.cd_tipoclas = pc.cd_tipoclas
           AND c.cd_classificacao = pc.cd_classificacao
        WHERE pc.cd_tipoclas IN %(tipos)s
        GROUP BY pc.cd_tipoclas, c.ds_classificacao
        ORDER BY pc.cd_tipoclas, c.ds_classificacao;
        """,
        {"tipos": tuple(CLASSIFICATION_TYPES.values())},
    )
    by_code = {
        CLASSIFICATION_TYPES["status_produto"]: "status_produto",
        CLASSIFICATION_TYPES["continuidade"]: "continuidade",
        CLASSIFICATION_TYPES["linha"]: "linha",
        CLASSIFICATION_TYPES["familia"]: "familia",
    }
    result: dict[str, list[dict[str, Any]]] = {
        "status_produto": [],
        "continuidade": [],
        "linha": [],
        "familia": [],
    }
    for row in rows:
        key = by_code.get(row["cd_tipoclas"])
        if key:
            result[key].append({"valor": row["valor"], "qtd_produtos": row["qtd_produtos"]})
    return result


@app.post("/api/cache/atualizar")
def atualizar_cache():
    return refresh_cache()


@app.post("/api/cache/atualizar-mes/{mes}")
def atualizar_cache_mes(mes: str):
    if len(mes) != 7 or mes[4] != "-":
        raise HTTPException(status_code=422, detail="Mes deve estar no formato YYYY-MM.")
    return refresh_cache(month=mes)


@app.get("/api/cache/status")
def cache_status():
    ensure_cache_schema()
    meta = ultima_atualizacao()
    status = CACHE_STATUS["status"]
    if status == "nunca_atualizado" and meta and meta.get("atualizado_em"):
        status = "ok"
    return {**CACHE_STATUS, "status": status, "cache": meta}


@app.get("/api/dashboard/resumo-geral")
def dashboard_resumo_geral(
    year: int = Query(default=2026, ge=2020, le=2035),
    month: str | None = Query(default=None, pattern=r"^\d{4}-\d{2}$"),
    cd_loja: int | None = Query(default=None),
    referencia: str | None = Query(default=None),
    somente_entrada_sem_necessidade: bool | None = Query(default=None),
    status_produto: str | None = Query(default=None),
    continuidade: str | None = Query(default=None),
    linha: str | None = Query(default=None),
    familia: str | None = Query(default=None),
):
    analytic_table = source_analytic_table()
    filter_builder = (
        product_classification_column_filter_sql
        if analytic_table == "cache_reposicao_analitico_classificado"
        else product_classification_filter_sql
    )
    product_filter_sql, filter_params = filter_builder(
        "a", status_produto=status_produto, continuidade=continuidade, linha=linha, familia=familia
    )
    scope_sql, scope_params = scope_filter_sql(
        "a",
        cd_loja=cd_loja,
        referencia=referencia,
        somente_entrada_sem_necessidade=somente_entrada_sem_necessidade,
    )
    table = source_summary_table("\n".join(part for part in [product_filter_sql, scope_sql] if part), analytic_table)
    where = "WHERE mes = %(month)s" if month else "WHERE mes LIKE %(year_like)s"
    params = {"month": month} if month else {"year_like": f"{year}-%"}
    params.update(filter_params)
    params.update(scope_params)
    row = fetch_one(
        f"""
        SELECT
            SUM(necessidade_total) AS necessidade,
            SUM(entrada_periodo) AS entrada_periodo,
            SUM(entrada_atrasada) AS entrada_atrasada,
            SUM(entrada_sem_lote) AS entrada_sem_lote,
            SUM(entrada_total) AS entrada_total,
            SUM(entrada_sem_necessidade) AS entrada_sem_necessidade,
            SUM(faltou) AS faltou,
            SUM(qtd_skus_demanda) AS skus_demanda,
            SUM(skus_atendidos) AS skus_atendidos,
            SUM(skus_faltantes) AS skus_faltantes,
            SUM(skus_entrada_periodo) AS skus_entrada_periodo,
            SUM(skus_entrada_atrasada) AS skus_entrada_atrasada,
            SUM(skus_entrada_sem_lote) AS skus_entrada_sem_lote,
            SUM(skus_entrada_sem_necessidade) AS skus_entrada_sem_necessidade,
            SUM(skus_ok) AS skus_ok,
            SUM(skus_parcial) AS skus_parcial,
            SUM(skus_zerados) AS skus_zerados,
            ROUND(SUM(skus_atendidos)::numeric / NULLIF(SUM(qtd_skus_demanda), 0)::numeric * 100, 1)
                AS taxa_atendimento,
            MIN(mes) AS primeiro_mes,
            MAX(mes) AS ultimo_mes
        FROM {table}
        {where};
        """,
        params,
    ) or {}
    entrada_total = row.get("entrada_total") or 0
    return {
        **row,
        "pct_periodo": round((row.get("entrada_periodo") or 0) / entrada_total * 100, 1) if entrada_total else 0,
        "pct_atrasada": round((row.get("entrada_atrasada") or 0) / entrada_total * 100, 1) if entrada_total else 0,
        "pct_sem_lote": round((row.get("entrada_sem_lote") or 0) / entrada_total * 100, 1) if entrada_total else 0,
    }


@app.get("/api/dashboard/evolucao-mensal")
def dashboard_evolucao_mensal(
    year: int = Query(default=2026, ge=2020, le=2035),
    cd_loja: int | None = Query(default=None),
    referencia: str | None = Query(default=None),
    somente_entrada_sem_necessidade: bool | None = Query(default=None),
    status_produto: str | None = Query(default=None),
    continuidade: str | None = Query(default=None),
    linha: str | None = Query(default=None),
    familia: str | None = Query(default=None),
):
    analytic_table = source_analytic_table()
    filter_builder = (
        product_classification_column_filter_sql
        if analytic_table == "cache_reposicao_analitico_classificado"
        else product_classification_filter_sql
    )
    product_filter_sql, filter_params = filter_builder(
        "a", status_produto=status_produto, continuidade=continuidade, linha=linha, familia=familia
    )
    scope_sql, scope_params = scope_filter_sql(
        "a",
        cd_loja=cd_loja,
        referencia=referencia,
        somente_entrada_sem_necessidade=somente_entrada_sem_necessidade,
    )
    table = source_summary_table("\n".join(part for part in [product_filter_sql, scope_sql] if part), analytic_table)
    params = {"year_like": f"{year}-%", **filter_params, **scope_params}
    return fetch_all(
        f"""
        SELECT
            mes,
            SUM(necessidade_total) AS necessidade,
            SUM(entrada_periodo) AS entrada_periodo,
            SUM(entrada_atrasada) AS entrada_atrasada,
            SUM(entrada_sem_lote) AS entrada_sem_lote,
            SUM(entrada_total) AS entrada_total,
            SUM(faltou) AS faltou,
            SUM(qtd_skus_demanda) AS skus_demanda,
            SUM(skus_atendidos) AS skus_atendidos,
            SUM(skus_faltantes) AS skus_faltantes,
            ROUND(SUM(skus_atendidos)::numeric / NULLIF(SUM(qtd_skus_demanda), 0)::numeric * 100, 1)
                AS taxa_atendimento
        FROM {table}
        WHERE mes LIKE %(year_like)s
        GROUP BY mes
        ORDER BY mes;
        """,
        params,
    )


@app.get("/api/dashboard/lojas-ranking")
def dashboard_lojas_ranking(
    year: int = Query(default=2026, ge=2020, le=2035),
    month: str | None = Query(default=None, pattern=r"^\d{4}-\d{2}$"),
    limit: int = Query(default=30, ge=1, le=200),
    cd_loja: int | None = Query(default=None),
    referencia: str | None = Query(default=None),
    somente_entrada_sem_necessidade: bool | None = Query(default=None),
    status_produto: str | None = Query(default=None),
    continuidade: str | None = Query(default=None),
    linha: str | None = Query(default=None),
    familia: str | None = Query(default=None),
):
    analytic_table = source_analytic_table()
    filter_builder = (
        product_classification_column_filter_sql
        if analytic_table == "cache_reposicao_analitico_classificado"
        else product_classification_filter_sql
    )
    product_filter_sql, filter_params = filter_builder(
        "a", status_produto=status_produto, continuidade=continuidade, linha=linha, familia=familia
    )
    scope_sql, scope_params = scope_filter_sql(
        "a",
        cd_loja=cd_loja,
        referencia=referencia,
        somente_entrada_sem_necessidade=somente_entrada_sem_necessidade,
    )
    table = source_summary_table("\n".join(part for part in [product_filter_sql, scope_sql] if part), analytic_table)
    where = "WHERE mes = %(month)s" if month else "WHERE mes LIKE %(year_like)s"
    params: dict[str, Any] = {"limit": limit}
    params.update({"month": month} if month else {"year_like": f"{year}-%"})
    params.update(filter_params)
    params.update(scope_params)
    return fetch_all(
        f"""
        SELECT
            cd_loja,
            MAX(nome_loja) AS nome_loja,
            SUM(necessidade_total) AS necessidade,
            SUM(entrada_total) AS entrada_total,
            SUM(faltou) AS faltou,
            SUM(qtd_skus_demanda) AS skus_demanda,
            SUM(skus_atendidos) AS skus_atendidos,
            SUM(skus_faltantes) AS skus_faltantes,
            SUM(skus_entrada_periodo) AS skus_entrada_periodo,
            SUM(skus_entrada_atrasada) AS skus_entrada_atrasada,
            SUM(skus_entrada_sem_lote) AS skus_entrada_sem_lote,
            ROUND(SUM(skus_atendidos)::numeric / NULLIF(SUM(qtd_skus_demanda), 0)::numeric * 100, 1)
                AS taxa_atendimento,
            SUM(skus_zerados) AS skus_zerados
        FROM {table}
        {where}
        GROUP BY cd_loja
        ORDER BY taxa_atendimento NULLS FIRST, skus_faltantes DESC, faltou DESC
        LIMIT %(limit)s;
        """,
        params,
    )


@app.get("/api/analise/matriz-reposicao")
def matriz_reposicao(
    year: int = Query(default=2026, ge=2020, le=2035),
    month: str | None = Query(default=None, pattern=r"^\d{4}-\d{2}$"),
    limit: int | None = Query(default=None, ge=1),
    cd_loja: int | None = Query(default=None),
    referencia: str | None = Query(default=None),
    somente_entrada_sem_necessidade: bool | None = Query(default=None),
    status_produto: str | None = Query(default=None),
    continuidade: str | None = Query(default=None),
    linha: str | None = Query(default=None),
    familia: str | None = Query(default=None),
):
    table = source_analytic_table()
    is_cached = table == "cache_reposicao_analitico_classificado"
    filter_builder = product_classification_column_filter_sql if is_cached else product_classification_filter_sql
    product_filter_sql, filter_params = filter_builder(
        "a", status_produto=status_produto, continuidade=continuidade, linha=linha, familia=familia
    )
    classification_fields = (
        """
            MAX(a.status_produto) AS status_produto,
            MAX(a.continuidade) AS continuidade,
            MAX(a.linha) AS linha,
            MAX(a.familia) AS familia,
            COALESCE(a.cor, '') AS cor,
            COALESCE(a.tamanho, '') AS tamanho,
        """
        if is_cached
        else """
            MAX(cls.status_produto) AS status_produto,
            MAX(cls.continuidade) AS continuidade,
            MAX(cls.linha) AS linha,
            MAX(cls.familia) AS familia,
            COALESCE(p.ds_cor, '') AS cor,
            COALESCE(p.ds_tamanho, '') AS tamanho,
        """
    )
    classification_join = (
        ""
        if is_cached
        else f"""
        LEFT JOIN vr_prd_prdgrade p
            ON p.cd_produto = a.cd_produto
        LEFT JOIN LATERAL (
            SELECT
                {product_classification_select("a")}
        ) cls ON TRUE
        """
    )
    classification_group = "a.cor, a.tamanho" if is_cached else "p.ds_cor, p.ds_tamanho"
    classification_order = "a.cor, a.tamanho" if is_cached else "p.ds_cor, p.ds_tamanho"
    where = "WHERE a.mes = %(month)s" if month else "WHERE a.mes LIKE %(year_like)s"
    params: dict[str, Any] = {}
    params.update({"month": month} if month else {"year_like": f"{year}-%"})
    params.update(filter_params)
    scope_sql, scope_params = scope_filter_sql(
        "a",
        cd_loja=cd_loja,
        referencia=referencia,
        somente_entrada_sem_necessidade=somente_entrada_sem_necessidade,
    )
    params.update(scope_params)
    limit_sql = "LIMIT %(limit)s" if limit is not None else ""
    if limit is not None:
        params["limit"] = limit
    return fetch_all(
        f"""
        SELECT
            a.mes,
            a.cd_loja,
            a.nome_loja,
            a.referencia,
            a.descricao_produto,
            a.cd_produto,
            {classification_fields}
            MAX(a.curva_completa) AS curva_completa,
            SUM(a.vendas_3m) AS vendas_3m,
            SUM(a.media_mensal) AS media_mensal,
            SUM(a.estoque_minimo) AS estoque_minimo,
            SUM(a.saldo_inicial) AS saldo_inicial,
            SUM(a.necessidade) AS necessidade,
            SUM(a.entrada_periodo) AS entrada_periodo,
            SUM(a.entrada_atrasada) AS entrada_atrasada,
            SUM(a.entrada_sem_lote) AS entrada_sem_lote,
            SUM(a.entrada_total) AS entrada_total,
            SUM(CASE WHEN a.necessidade <= 0 THEN a.entrada_total ELSE 0 END) AS entrada_sem_necessidade,
            SUM(GREATEST(0, a.necessidade - a.entrada_total)) AS faltou,
            COUNT(*) FILTER (WHERE a.necessidade > 0) AS skus_demanda,
            COUNT(*) FILTER (WHERE a.necessidade > 0 AND a.entrada_total >= a.necessidade) AS skus_atendidos,
            COUNT(*) FILTER (WHERE a.necessidade > 0 AND a.entrada_total < a.necessidade) AS skus_faltantes,
            COUNT(*) FILTER (WHERE a.necessidade <= 0 AND a.entrada_total > 0) AS skus_entrada_sem_necessidade,
            CASE
                WHEN SUM(a.necessidade) <= 0 THEN 'SEM NECESSIDADE'
                WHEN SUM(a.entrada_total) >= SUM(a.necessidade) THEN 'OK'
                WHEN SUM(a.entrada_total) > 0 THEN 'PARCIAL'
                ELSE 'ZERADO'
            END AS status_reposicao
        FROM {table} a
        {classification_join}
        {where}
          {product_filter_sql}
          {scope_sql}
        GROUP BY
            a.mes, a.cd_loja, a.nome_loja, a.referencia, a.descricao_produto,
            a.cd_produto, {classification_group}
        ORDER BY a.nome_loja, a.referencia, {classification_order}, a.cd_produto
        {limit_sql};
        """,
        params,
    )


@app.get("/api/analise/diagnostico-produto")
def diagnostico_produto(
    year: int = Query(default=2026, ge=2020, le=2035),
    mes_inicio: str | None = Query(default=None, pattern=r"^\d{4}-\d{2}$"),
    mes_fim: str | None = Query(default=None, pattern=r"^\d{4}-\d{2}$"),
    cd_loja: int | None = Query(default=None),
    referencia: str | None = Query(default=None),
    cor: str | None = Query(default=None),
    tamanho: str | None = Query(default=None),
    limit: int = Query(default=500, ge=1, le=5000),
):
    table = source_analytic_table()
    is_cached = table == "cache_reposicao_analitico_classificado"
    color_expr = "COALESCE(a.cor, '')" if is_cached else "COALESCE(p.ds_cor, '')"
    size_expr = "COALESCE(a.tamanho, '')" if is_cached else "COALESCE(p.ds_tamanho, '')"
    grade_join = "" if is_cached else "LEFT JOIN vr_prd_prdgrade p ON p.cd_produto = a.cd_produto"

    filters = ["a.mes LIKE %(year_like)s"]
    final_filters: list[str] = []
    params: dict[str, Any] = {"year_like": f"{year}-%", "limit": limit}
    if mes_inicio:
        final_filters.append("mes >= %(mes_inicio)s")
        params["mes_inicio"] = mes_inicio
    if mes_fim:
        final_filters.append("mes <= %(mes_fim)s")
        params["mes_fim"] = mes_fim
    if cd_loja is not None:
        filters.append("a.cd_loja = %(cd_loja)s")
        params["cd_loja"] = cd_loja
    if referencia:
        filters.append("a.referencia ILIKE %(referencia)s")
        params["referencia"] = f"%{referencia.strip()}%"
    if cor:
        filters.append(f"{color_expr} ILIKE %(cor)s")
        params["cor"] = f"%{cor.strip()}%"
    if tamanho:
        filters.append(f"{size_expr} ILIKE %(tamanho)s")
        params["tamanho"] = f"%{tamanho.strip()}%"

    where_sql = " AND ".join(filters)
    final_where_sql = f"WHERE {' AND '.join(final_filters)}" if final_filters else ""
    return fetch_all(
        f"""
        WITH base AS (
            SELECT
                a.mes,
                a.cd_loja,
                a.nome_loja,
                a.referencia,
                a.descricao_produto,
                a.cd_produto,
                {color_expr} AS cor,
                {size_expr} AS tamanho,
                a.curva_completa,
                a.vendas_3m,
                a.media_mensal,
                a.estoque_minimo,
                a.saldo_inicial,
                a.necessidade,
                a.entrada_periodo,
                a.entrada_atrasada,
                a.entrada_sem_lote,
                a.entrada_total,
                CASE WHEN a.necessidade <= 0 THEN a.entrada_total ELSE 0 END AS entrada_sem_necessidade,
                GREATEST(0, a.necessidade - a.entrada_total) AS faltou,
                a.status_reposicao
            FROM {table} a
            {grade_join}
            WHERE {where_sql}
        ),
        historico AS (
            SELECT
                b.*,
                MAX(COALESCE(b.vendas_3m, 0)) OVER (
                    PARTITION BY b.cd_loja, b.cd_produto
                    ORDER BY b.mes
                    ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING
                ) AS maior_venda_3m_anterior,
                MAX(CASE WHEN COALESCE(b.saldo_inicial, 0) > 0 THEN b.mes END) OVER (
                    PARTITION BY b.cd_loja, b.cd_produto
                    ORDER BY b.mes
                    ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING
                ) AS ultimo_mes_com_estoque_anterior,
                MAX(CASE WHEN COALESCE(b.necessidade, 0) > 0 THEN b.mes END) OVER (
                    PARTITION BY b.cd_loja, b.cd_produto
                    ORDER BY b.mes
                    ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING
                ) AS ultimo_mes_com_necessidade_anterior,
                MAX(CASE WHEN COALESCE(b.entrada_total, 0) > 0 THEN b.mes END) OVER (
                    PARTITION BY b.cd_loja, b.cd_produto
                    ORDER BY b.mes
                    ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING
                ) AS ultimo_mes_com_entrada_anterior
            FROM base b
        )
        SELECT
            *,
            CASE
                WHEN necessidade > 0 AND entrada_total >= necessidade THEN 'ATENDIDO'
                WHEN necessidade > 0 AND entrada_total > 0 THEN 'ATENDIDO PARCIAL'
                WHEN necessidade > 0 THEN 'TINHA NECESSIDADE E FALTOU'
                WHEN necessidade <= 0 AND entrada_total > 0 THEN 'ENTROU SEM NECESSIDADE'
                WHEN necessidade <= 0
                     AND COALESCE(saldo_inicial, 0) <= 0
                     AND COALESCE(maior_venda_3m_anterior, 0) > 0
                    THEN 'POSSIVEL DEMANDA PERDIDA'
                WHEN necessidade <= 0 AND COALESCE(saldo_inicial, 0) > 0 THEN 'SEM NECESSIDADE COM ESTOQUE'
                ELSE 'SEM MOVIMENTO'
            END AS diagnostico,
            CASE
                WHEN necessidade > 0 AND entrada_total >= necessidade
                    THEN 'Havia necessidade e a entrada total atendeu o SKU.'
                WHEN necessidade > 0 AND entrada_total > 0
                    THEN 'Havia necessidade, mas a entrada total nao cobriu tudo.'
                WHEN necessidade > 0
                    THEN 'Havia necessidade calculada e nao houve entrada suficiente.'
                WHEN necessidade <= 0 AND entrada_total > 0
                    THEN 'Nao havia necessidade calculada, mas houve entrada.'
                WHEN necessidade <= 0
                     AND COALESCE(saldo_inicial, 0) <= 0
                     AND COALESCE(maior_venda_3m_anterior, 0) > 0
                    THEN 'Sem estoque/necessidade agora, mas havia venda historica anterior; pode ter perdido demanda por ruptura.'
                WHEN necessidade <= 0 AND COALESCE(saldo_inicial, 0) > 0
                    THEN 'Saldo inicial cobria a regra de estoque minimo.'
                ELSE 'Sem venda, estoque, necessidade ou entrada no recorte.'
            END AS leitura
        FROM historico
        {final_where_sql}
        ORDER BY cd_loja, referencia, cor, tamanho, cd_produto, mes
        LIMIT %(limit)s;
        """,
        params,
    )


def processo_reposicao_query(
    table: str,
    is_cached: bool,
    product_filter_sql: str,
    where: str,
    select_sql: str,
    order_limit_sql: str = "",
) -> str:
    classification_fields = (
        """
            MAX(a.status_produto) AS status_produto,
            MAX(a.continuidade) AS continuidade,
            MAX(a.linha) AS linha,
            MAX(a.familia) AS familia,
            COALESCE(a.cor, '') AS cor,
            COALESCE(a.tamanho, '') AS tamanho,
        """
        if is_cached
        else """
            MAX(cls.status_produto) AS status_produto,
            MAX(cls.continuidade) AS continuidade,
            MAX(cls.linha) AS linha,
            MAX(cls.familia) AS familia,
            COALESCE(p.ds_cor, '') AS cor,
            COALESCE(p.ds_tamanho, '') AS tamanho,
        """
    )
    classification_join = (
        ""
        if is_cached
        else f"""
        LEFT JOIN vr_prd_prdgrade p
            ON p.cd_produto = a.cd_produto
        LEFT JOIN LATERAL (
            SELECT
                {product_classification_select("a")}
        ) cls ON TRUE
        """
    )
    enrichment_join = """
        LEFT JOIN public."dPRODUTO" dp
            ON dp.idproduto = a.cd_produto
        LEFT JOIN public."dEMPRESA" de
            ON de.idempresa = a.cd_loja
    """
    classification_group = "a.cor, a.tamanho" if is_cached else "p.ds_cor, p.ds_tamanho"
    return f"""
        WITH pedidos_pendentes AS (
            SELECT
                de.idempresa AS cd_loja,
                i.cd_produto,
                SUM(
                    GREATEST(
                        0,
                        COALESCE(i.qt_solicitada, 0)
                        - COALESCE(i.qt_atendida, 0)
                        - COALESCE(i.qt_cancelada, 0)
                    )
                ) AS qtd_pendente_pedido
            FROM ped_pedidoc c
            JOIN ped_pedidoi i
                ON i.cd_empresa = c.cd_empresa
               AND i.cd_pedido = c.cd_pedido
            JOIN public."dEMPRESA" de
                ON de.cd_pessoa = c.cd_cliente
            WHERE c.cd_empresa = 1
              AND c.dt_pedido >= (%(month)s::text || '-01')::date
              AND c.dt_pedido < ((%(month)s::text || '-01')::date + INTERVAL '1 month')
              AND c.tp_situacao IN (1, 3)
              AND c.cd_operacao IN (30, 598, 310)
            GROUP BY de.idempresa, i.cd_produto
            HAVING SUM(
                GREATEST(
                    0,
                    COALESCE(i.qt_solicitada, 0)
                    - COALESCE(i.qt_atendida, 0)
                    - COALESCE(i.qt_cancelada, 0)
                )
            ) > 0
        ),
        base AS (
            SELECT
                a.mes,
                a.cd_loja,
                a.nome_loja,
                a.referencia,
                a.descricao_produto,
                a.cd_produto,
                {classification_fields}
                MAX(a.curva_completa) AS curva_completa,
                SUM(a.media_mensal) AS media_mensal,
                SUM(a.saldo_inicial) AS saldo_inicial,
                SUM(a.necessidade) AS necessidade,
                SUM(a.entrada_total) AS entrada_total,
                SUM(GREATEST(0, a.necessidade - a.entrada_total)) AS qtd_sugerida_bruta,
                MAX(COALESCE(pp.qtd_pendente_pedido, 0)) AS qtd_pendente_pedido,
                0::numeric AS qtd_transito,
                MAX(COALESCE(pp.qtd_pendente_pedido, 0)) AS qtd_ja_programada,
                GREATEST(
                    0,
                    SUM(GREATEST(0, a.necessidade - a.entrada_total))
                    - MAX(COALESCE(pp.qtd_pendente_pedido, 0))
                ) AS qtd_sugerida,
                MAX(COALESCE(dp.prcpfabrica, 0)) AS original_price,
                MAX(COALESCE(dp.prcpfabrica, 0)) AS price,
                0::numeric AS discount_percentage,
                0::numeric AS discount_value,
                MAX(de.cd_pessoa)::bigint AS customer_code,
                CASE
                    WHEN a.cd_loja IN (2,3,4,5,6,7,8,21,22,19) THEN 598
                    WHEN a.cd_loja IN (10,14,15,20,120) THEN 30
                    WHEN a.cd_loja = 17 THEN 310
                    ELSE NULL
                END AS operation_code,
                1::integer AS payment_condition_code,
                NULL::integer AS shipping_company_code,
                NULL::text AS freight_type,
                CASE
                    WHEN SUM(a.necessidade) <= 0 THEN 'SEM NECESSIDADE'
                    WHEN SUM(a.entrada_total) >= SUM(a.necessidade) THEN 'OK'
                    WHEN SUM(a.entrada_total) > 0 THEN 'PARCIAL'
                    ELSE 'ZERADO'
                END AS status_reposicao
            FROM {table} a
            {classification_join}
            {enrichment_join}
            LEFT JOIN pedidos_pendentes pp
                ON pp.cd_loja = a.cd_loja
               AND pp.cd_produto = a.cd_produto
            {where}
              {product_filter_sql}
            GROUP BY
                a.mes, a.cd_loja, a.nome_loja, a.referencia, a.descricao_produto,
                a.cd_produto, {classification_group}
        ),
        sugestao AS (
            SELECT
                *,
                CASE
                    WHEN status_reposicao = 'ZERADO' OR curva_completa IN ('CURVA A', 'CURVA AA') THEN 'CRITICA'
                    WHEN curva_completa = 'CURVA B' OR qtd_sugerida >= 3 THEN 'ALTA'
                    ELSE 'NORMAL'
                END AS prioridade
            FROM base
            WHERE necessidade > 0
              AND qtd_sugerida > 0
        )
        {select_sql}
        {order_limit_sql}
    """


@app.get("/api/processo-reposicao/resumo")
def processo_reposicao_resumo(
    year: int = Query(default=2026, ge=2020, le=2035),
    month: str | None = Query(default=None, pattern=r"^\d{4}-\d{2}$"),
    status_produto: str | None = Query(default=None),
    continuidade: str | None = Query(default=None),
    linha: str | None = Query(default=None),
    familia: str | None = Query(default=None),
):
    if not month:
        month = date.today().strftime("%Y-%m")
    table = source_analytic_table()
    is_cached = table == "cache_reposicao_analitico_classificado"
    filter_builder = product_classification_column_filter_sql if is_cached else product_classification_filter_sql
    product_filter_sql, filter_params = filter_builder(
        "a", status_produto=status_produto, continuidade=continuidade, linha=linha, familia=familia
    )
    where = "WHERE a.mes = %(month)s"
    params = {"month": month}
    params.update(filter_params)
    query = processo_reposicao_query(
        table,
        is_cached,
        product_filter_sql,
        where,
        """
        SELECT
            COUNT(*) AS skus_sugeridos,
            COUNT(DISTINCT cd_loja) AS lojas,
            SUM(qtd_sugerida) AS pecas_sugeridas,
            SUM(necessidade) AS necessidade,
            SUM(entrada_total) AS entrada_total,
            COUNT(*) FILTER (WHERE prioridade = 'CRITICA') AS criticos,
            COUNT(*) FILTER (WHERE prioridade = 'ALTA') AS altos,
            COUNT(*) FILTER (WHERE prioridade = 'NORMAL') AS normais
        FROM sugestao
        """,
    )
    return fetch_one(query, params) or {
        "skus_sugeridos": 0,
        "lojas": 0,
        "pecas_sugeridas": 0,
        "necessidade": 0,
        "entrada_total": 0,
        "criticos": 0,
        "altos": 0,
        "normais": 0,
    }


@app.get("/api/processo-reposicao/sugestao")
def processo_reposicao_sugestao(
    year: int = Query(default=2026, ge=2020, le=2035),
    month: str | None = Query(default=None, pattern=r"^\d{4}-\d{2}$"),
    limit: int = Query(default=1000, ge=1, le=10000),
    status_produto: str | None = Query(default=None),
    continuidade: str | None = Query(default=None),
    linha: str | None = Query(default=None),
    familia: str | None = Query(default=None),
):
    if not month:
        month = date.today().strftime("%Y-%m")
    table = source_analytic_table()
    is_cached = table == "cache_reposicao_analitico_classificado"
    filter_builder = product_classification_column_filter_sql if is_cached else product_classification_filter_sql
    product_filter_sql, filter_params = filter_builder(
        "a", status_produto=status_produto, continuidade=continuidade, linha=linha, familia=familia
    )
    params: dict[str, Any] = {"limit": limit}
    params.update({"month": month})
    params.update(filter_params)
    query = processo_reposicao_query(
        table,
        is_cached,
        product_filter_sql,
        "WHERE a.mes = %(month)s",
        """
        SELECT
            mes,
            cd_loja,
            nome_loja,
            referencia,
            descricao_produto,
            cd_produto,
            status_produto,
            continuidade,
            linha,
            familia,
            cor,
            tamanho,
            curva_completa,
            media_mensal,
            saldo_inicial,
            necessidade,
            entrada_total,
            qtd_sugerida_bruta,
            qtd_pendente_pedido,
            qtd_transito,
            qtd_ja_programada,
            qtd_sugerida,
            original_price,
            price,
            discount_percentage,
            discount_value,
            customer_code,
            operation_code,
            payment_condition_code,
            shipping_company_code,
            freight_type,
            status_reposicao,
            prioridade
        FROM sugestao
        """,
        """
        ORDER BY
            CASE prioridade WHEN 'CRITICA' THEN 0 WHEN 'ALTA' THEN 1 ELSE 2 END,
            qtd_sugerida DESC,
            nome_loja,
            referencia,
            cor,
            tamanho
        LIMIT %(limit)s;
        """,
    )
    return fetch_all(query, params)


def _is_curva_a_aa(curva: str) -> bool:
    return curva.strip().upper() in ("CURVA A", "CURVA AA")


def _is_curva_b_c(curva: str) -> bool:
    return curva.strip().upper() in ("CURVA B", "CURVA C")


def processo_reposicao_rows_for_order(
    *,
    year: int,
    month: str,
    pedido_tipo: str,
    filtros: dict[str, Any],
) -> list[dict[str, Any]]:
    table = source_analytic_table()
    is_cached = table == "cache_reposicao_analitico_classificado"
    filter_builder = product_classification_column_filter_sql if is_cached else product_classification_filter_sql
    product_filter_sql, filter_params = filter_builder(
        "a",
        status_produto=filtros.get("status_produto"),
        continuidade=filtros.get("continuidade"),
        linha=filtros.get("linha"),
        familia=filtros.get("familia"),
    )
    params: dict[str, Any] = {"month": month, "limit": 10000}
    params.update(filter_params)
    query = processo_reposicao_query(
        table,
        is_cached,
        product_filter_sql,
        "WHERE a.mes = %(month)s",
        """
        SELECT
            mes,
            cd_loja,
            nome_loja,
            referencia,
            descricao_produto,
            cd_produto,
            status_produto,
            continuidade,
            linha,
            familia,
            cor,
            tamanho,
            curva_completa,
            media_mensal,
            saldo_inicial,
            necessidade,
            entrada_total,
            qtd_sugerida_bruta,
            qtd_pendente_pedido,
            qtd_transito,
            qtd_ja_programada,
            qtd_sugerida,
            original_price,
            price,
            discount_percentage,
            discount_value,
            customer_code,
            operation_code,
            payment_condition_code,
            shipping_company_code,
            freight_type,
            status_reposicao,
            prioridade
        FROM sugestao
        """,
        """
        ORDER BY
            CASE prioridade WHEN 'CRITICA' THEN 0 WHEN 'ALTA' THEN 1 ELSE 2 END,
            qtd_sugerida DESC,
            nome_loja,
            referencia,
            cor,
            tamanho
        LIMIT %(limit)s;
        """,
    )
    rows = fetch_all(query, params)
    pedido_tipo_normalizado = pedido_tipo.strip().upper()
    selected: list[dict[str, Any]] = []
    for row in rows:
        curva = str(row.get("curva_completa") or "")
        qtd = float(row.get("qtd_sugerida") or 0)
        if pedido_tipo_normalizado == "CURVA_A_AA" and _is_curva_a_aa(curva):
            row["qtd_pedido"] = qtd
        elif pedido_tipo_normalizado == "CURVA_BC_1" and _is_curva_b_c(curva):
            row["qtd_pedido"] = int((qtd + 1) // 2)
        elif pedido_tipo_normalizado == "CURVA_BC_2" and _is_curva_b_c(curva):
            row["qtd_pedido"] = int(qtd // 2)
        else:
            continue
        if float(row["qtd_pedido"]) > 0:
            selected.append(row)
    return selected


def build_totvs_orders_for_rows(
    *,
    rows: list[dict[str, Any]],
    month: str,
    pedido_tipo: str,
    settings: dict[str, Any],
) -> list[dict[str, Any]]:
    grouped: dict[int, list[dict[str, Any]]] = {}
    for row in rows:
        cd_loja = int(row.get("cd_loja") or 0)
        grouped.setdefault(cd_loja, []).append(row)

    orders: list[dict[str, Any]] = []
    for cd_loja, loja_rows in sorted(grouped.items()):
        nome_loja = str(loja_rows[0].get("nome_loja") or cd_loja)
        order_id = f"{settings['order_id_prefix']}{month}-{pedido_tipo}-{cd_loja}"
        payload = build_order_payload(
            order_id=order_id,
            order_date=datetime.now(),
            rows=loja_rows,
            settings=settings,
        )
        missing_order_config: list[str] = []
        if not payload.get("customerCode") and not payload.get("customerCpfCnpj"):
            missing_order_config.append("customerCode")
        if not payload.get("operationCode"):
            missing_order_config.append("operationCode")
        if not payload.get("items"):
            missing_order_config.append("items")
        orders.append(
            {
                "cd_loja": cd_loja,
                "nome_loja": nome_loja,
                "order_id": order_id,
                "skus": len(loja_rows),
                "pecas": sum(float(row.get("qtd_pedido") or 0) for row in loja_rows),
                "total_amount": payload.get("totalAmountOrder", 0),
                "missing_config": missing_order_config,
                "payload": payload,
            }
        )
    return orders


@app.get("/api/totvs/config-status")
def totvs_config_status():
    settings = totvs_settings()
    missing = missing_totvs_settings(settings)
    return {
        "configured": not missing,
        "missing": missing,
        "order_url_configured": bool(settings.get("order_url")),
        "token_url_configured": bool(settings.get("token_url")),
    }


@app.post("/api/processo-reposicao/pedido-totvs/preview")
def processo_reposicao_pedido_totvs_preview(payload: dict[str, Any] = Body(...)):
    month = str(payload.get("month") or "")
    pedido_tipo = str(payload.get("pedido_tipo") or "")
    if len(month) != 7 or month[4] != "-":
        raise HTTPException(status_code=422, detail="month deve estar no formato YYYY-MM.")
    if pedido_tipo not in ("CURVA_A_AA", "CURVA_BC_1", "CURVA_BC_2"):
        raise HTTPException(status_code=422, detail="pedido_tipo invalido.")

    settings = totvs_settings()
    rows = processo_reposicao_rows_for_order(
        year=int(payload.get("year") or 2026),
        month=month,
        pedido_tipo=pedido_tipo,
        filtros=payload.get("filtros") or {},
    )
    test_item = payload.get("test_item") is True
    if test_item:
        rows = rows[:1]

    pedido_tipo_order_id = pedido_tipo
    if test_item:
        pedido_tipo_order_id = f"{pedido_tipo}-TEST-{datetime.now().strftime('%Y%m%d%H%M%S')}"

    orders = build_totvs_orders_for_rows(rows=rows, month=month, pedido_tipo=pedido_tipo_order_id, settings=settings)
    base_missing = missing_totvs_settings(settings)
    order_missing = sorted({item for order in orders for item in order["missing_config"]})
    return {
        "ready_to_send": not base_missing and not order_missing and bool(rows),
        "missing_config": base_missing + order_missing,
        "pedido_tipo": pedido_tipo,
        "month": month,
        "test_item": test_item,
        "skus": len(rows),
        "pecas": sum(float(row.get("qtd_pedido") or 0) for row in rows),
        "pedidos": len(orders),
        "orders": orders,
        "payload": orders[0]["payload"] if len(orders) == 1 else {"orders": [order["payload"] for order in orders]},
    }


def salvar_pedido_reposicao(
    order: dict[str, Any],
    pedido_tipo: str,
    month: str,
    rows: list[dict[str, Any]],
    status: str = "GERADO",
    totvs_response: dict[str, Any] | None = None,
) -> int:
    """Salva pedido e itens no banco, retorna o ID do pedido."""
    ensure_cache_schema()

    # Extrair número do pedido TOTVS da resposta
    totvs_order_number = None
    if totvs_response:
        totvs_order_number = (
            totvs_response.get("orderNumber")
            or totvs_response.get("orderCode")
            or totvs_response.get("code")
            or totvs_response.get("id")
            or totvs_response.get("nr_pedido")
            or totvs_response.get("numero")
        )
        if totvs_order_number:
            totvs_order_number = str(totvs_order_number)

    # Inserir pedido
    pedido_sql = """
    INSERT INTO reposicao_pedidos (
        order_id, pedido_tipo, mes, cd_loja, nome_loja,
        total_skus, total_pecas, total_valor, status,
        totvs_order_number, totvs_response
    ) VALUES (
        %(order_id)s, %(pedido_tipo)s, %(mes)s, %(cd_loja)s, %(nome_loja)s,
        %(total_skus)s, %(total_pecas)s, %(total_valor)s, %(status)s,
        %(totvs_order_number)s, %(totvs_response)s
    )
    ON CONFLICT (order_id) DO UPDATE SET
        status = EXCLUDED.status,
        totvs_order_number = COALESCE(EXCLUDED.totvs_order_number, reposicao_pedidos.totvs_order_number),
        totvs_response = COALESCE(EXCLUDED.totvs_response, reposicao_pedidos.totvs_response),
        atualizado_em = NOW()
    RETURNING id;
    """
    pedido_params = {
        "order_id": order["order_id"],
        "pedido_tipo": pedido_tipo,
        "mes": month,
        "cd_loja": order["cd_loja"],
        "nome_loja": order["nome_loja"],
        "total_skus": order["skus"],
        "total_pecas": order["pecas"],
        "total_valor": order.get("total_amount", 0),
        "status": status,
        "totvs_order_number": totvs_order_number,
        "totvs_response": json.dumps(totvs_response) if totvs_response else None,
    }

    result = execute_transaction([(pedido_sql, pedido_params)])
    pedido_id = result[0][0]["id"] if result and result[0] else None

    if not pedido_id:
        # Buscar ID existente
        existing = fetch_one(
            "SELECT id FROM reposicao_pedidos WHERE order_id = %(order_id)s",
            {"order_id": order["order_id"]},
        )
        pedido_id = existing["id"] if existing else None

    if pedido_id:
        # Inserir itens (apenas na primeira vez)
        loja_rows = [r for r in rows if int(r.get("cd_loja") or 0) == order["cd_loja"]]
        for row in loja_rows:
            item_sql = """
            INSERT INTO reposicao_pedido_itens (
                pedido_id, cd_produto, referencia, descricao, cor, tamanho,
                curva_completa, quantidade, preco, status,
                media_mensal, estoque_minimo, saldo_inicial, necessidade,
                entrada_total, qtd_ja_programada
            ) VALUES (
                %(pedido_id)s, %(cd_produto)s, %(referencia)s, %(descricao)s,
                %(cor)s, %(tamanho)s, %(curva_completa)s, %(quantidade)s,
                %(preco)s, %(status)s, %(media_mensal)s, %(estoque_minimo)s,
                %(saldo_inicial)s, %(necessidade)s, %(entrada_total)s, %(qtd_ja_programada)s
            )
            ON CONFLICT DO NOTHING;
            """
            item_params = {
                "pedido_id": pedido_id,
                "cd_produto": row.get("cd_produto"),
                "referencia": row.get("referencia"),
                "descricao": row.get("descricao_produto"),
                "cor": row.get("cor"),
                "tamanho": row.get("tamanho"),
                "curva_completa": row.get("curva_completa"),
                "quantidade": row.get("qtd_pedido", 0),
                "preco": row.get("price") or row.get("preco_fabrica") or 0,
                "status": status,
                "media_mensal": row.get("media_mensal"),
                "estoque_minimo": row.get("estoque_minimo"),
                "saldo_inicial": row.get("saldo_inicial"),
                "necessidade": row.get("necessidade"),
                "entrada_total": row.get("entrada_total"),
                "qtd_ja_programada": row.get("qtd_ja_programada"),
            }
            try:
                execute_transaction([(item_sql, item_params)])
            except Exception:
                pass  # Item já existe, ignorar

        # Registrar histórico
        hist_sql = """
        INSERT INTO reposicao_pedido_historico (pedido_id, status_anterior, status_novo, usuario)
        VALUES (%(pedido_id)s, %(status_anterior)s, %(status_novo)s, %(usuario)s);
        """
        hist_params = {
            "pedido_id": pedido_id,
            "status_anterior": None,
            "status_novo": status,
            "usuario": "sistema",
        }
        try:
            execute_transaction([(hist_sql, hist_params)])
        except Exception:
            pass

    return pedido_id


@app.post("/api/processo-reposicao/pedido-totvs/enviar")
def processo_reposicao_pedido_totvs_enviar(payload: dict[str, Any] = Body(...)):
    if payload.get("confirmar") is not True:
        raise HTTPException(status_code=422, detail="Envio exige confirmar=true.")
    preview = processo_reposicao_pedido_totvs_preview(payload)
    if preview["missing_config"]:
        raise HTTPException(status_code=422, detail={"missing_config": preview["missing_config"]})
    if not preview["skus"]:
        raise HTTPException(status_code=422, detail="Pedido sem itens.")
    if not preview.get("orders"):
        raise HTTPException(status_code=422, detail="Nenhum pedido por loja foi gerado.")
    ensure_cache_schema()

    # Buscar rows para salvar memória de cálculo
    month = str(payload.get("month") or "")
    pedido_tipo = str(payload.get("pedido_tipo") or "")
    rows = processo_reposicao_rows_for_order(
        year=int(payload.get("year") or 2026),
        month=month,
        pedido_tipo=pedido_tipo,
        filtros=payload.get("filtros") or {},
    )
    if payload.get("test_item"):
        rows = rows[:1]

    # Filtrar por loja específica se informada
    orders_to_send = preview["orders"]
    cd_loja_filter = payload.get("cd_loja")
    if cd_loja_filter:
        cd_loja_filter = int(cd_loja_filter)
        orders_to_send = [o for o in orders_to_send if int(o["cd_loja"]) == cd_loja_filter]
        if not orders_to_send:
            raise HTTPException(status_code=422, detail=f"Nenhum pedido encontrado para loja {cd_loja_filter}")
        # Filtrar rows também para apenas essa loja
        rows = [r for r in rows if int(r.get("cd_loja", 0)) == cd_loja_filter]

    responses: list[dict[str, Any]] = []
    client = TotvsModaClient(totvs_settings())

    for order in orders_to_send:
        totvs_response = None
        status = "GERADO"
        error_msg = None

        try:
            totvs_response = client.create_order(order["payload"])
            status = "ENVIADO_TOTVS"
        except TotvsModaError as exc:
            status = "ERRO_TOTVS"
            error_msg = str(exc)
            totvs_response = {"error": error_msg}

        # Salvar no banco
        pedido_id = salvar_pedido_reposicao(
            order=order,
            pedido_tipo=pedido_tipo,
            month=month,
            rows=rows,
            status=status,
            totvs_response=totvs_response,
        )

        responses.append({
            "cd_loja": order["cd_loja"],
            "nome_loja": order["nome_loja"],
            "order_id": order["order_id"],
            "pedido_id": pedido_id,
            "sucesso": status == "ENVIADO_TOTVS",
            "status": status,
            "totvs": totvs_response,
            "erro": error_msg,
            "error": error_msg,
        })

    return {"pedido_tipo": preview["pedido_tipo"], "month": preview["month"], "pedidos": responses}


# ============================================================
# Endpoints de Acompanhamento de Reposição
# ============================================================

REPOSICAO_STATUS_LIST = [
    "GERADO", "ENVIADO_TOTVS", "ERRO_TOTVS", "FATURADO",
    "EXPEDIDO", "EM_TRANSITO", "RECEBIDO", "CONFERIDO", "FINALIZADO", "CANCELADO"
]


@app.get("/api/reposicao/dashboard")
def reposicao_dashboard(
    mes: str | None = Query(default=None),
    cd_loja: int | None = Query(default=None),
):
    ensure_cache_schema()
    filters = []
    params: dict[str, Any] = {}
    if mes:
        filters.append("mes = %(mes)s")
        params["mes"] = mes
    if cd_loja:
        filters.append("cd_loja = %(cd_loja)s")
        params["cd_loja"] = cd_loja
    where = f"WHERE {' AND '.join(filters)}" if filters else ""

    # Resumo por status
    status_query = f"""
    SELECT status, COUNT(*) as total, SUM(total_pecas) as pecas
    FROM reposicao_pedidos
    {where}
    GROUP BY status;
    """
    status_rows = fetch_all(status_query, params)
    status_map = {row["status"]: {"total": row["total"], "pecas": row["pecas"]} for row in status_rows}

    # Total geral
    total_query = f"""
    SELECT
        COUNT(*) as total_pedidos,
        COALESCE(SUM(total_skus), 0) as total_skus,
        COALESCE(SUM(total_pecas), 0) as total_pecas,
        COALESCE(SUM(total_valor), 0) as total_valor
    FROM reposicao_pedidos
    {where};
    """
    totals = fetch_one(total_query, params) or {}

    return {
        "total_pedidos": totals.get("total_pedidos", 0),
        "total_skus": totals.get("total_skus", 0),
        "total_pecas": totals.get("total_pecas", 0),
        "total_valor": totals.get("total_valor", 0),
        "por_status": status_map,
        "status_disponiveis": REPOSICAO_STATUS_LIST,
    }


@app.get("/api/reposicao/pedidos")
def listar_reposicao_pedidos(
    mes: str | None = Query(default=None),
    cd_loja: int | None = Query(default=None),
    status: str | None = Query(default=None),
    pedido_tipo: str | None = Query(default=None),
    limit: int = Query(default=500, ge=1, le=5000),
):
    ensure_cache_schema()
    filters = []
    params: dict[str, Any] = {"limit": limit}
    if mes:
        filters.append("mes = %(mes)s")
        params["mes"] = mes
    if cd_loja:
        filters.append("cd_loja = %(cd_loja)s")
        params["cd_loja"] = cd_loja
    if status:
        filters.append("status = %(status)s")
        params["status"] = status
    if pedido_tipo:
        filters.append("pedido_tipo = %(pedido_tipo)s")
        params["pedido_tipo"] = pedido_tipo

    where = f"WHERE {' AND '.join(filters)}" if filters else ""
    query = f"""
    SELECT
        id, order_id, pedido_tipo, mes, cd_loja, nome_loja,
        total_skus, total_pecas, total_valor, status,
        totvs_order_number, criado_em, atualizado_em
    FROM reposicao_pedidos
    {where}
    ORDER BY criado_em DESC
    LIMIT %(limit)s;
    """
    return fetch_all(query, params)


@app.get("/api/reposicao/pedidos/{pedido_id}")
def detalhe_reposicao_pedido(pedido_id: int):
    ensure_cache_schema()
    pedido = fetch_one(
        """
        SELECT
            id, order_id, pedido_tipo, mes, cd_loja, nome_loja,
            total_skus, total_pecas, total_valor, status,
            totvs_order_number, totvs_response, criado_em, atualizado_em
        FROM reposicao_pedidos
        WHERE id = %(pedido_id)s;
        """,
        {"pedido_id": pedido_id},
    )
    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido não encontrado.")

    itens = fetch_all(
        """
        SELECT
            id, cd_produto, referencia, descricao, cor, tamanho,
            curva_completa, quantidade, preco, status, observacao,
            media_mensal, estoque_minimo, saldo_inicial, necessidade,
            entrada_total, qtd_ja_programada, atualizado_em
        FROM reposicao_pedido_itens
        WHERE pedido_id = %(pedido_id)s
        ORDER BY referencia, cor, tamanho;
        """,
        {"pedido_id": pedido_id},
    )

    historico = fetch_all(
        """
        SELECT
            id, item_id, status_anterior, status_novo, usuario, observacao, criado_em
        FROM reposicao_pedido_historico
        WHERE pedido_id = %(pedido_id)s
        ORDER BY criado_em DESC
        LIMIT 100;
        """,
        {"pedido_id": pedido_id},
    )

    return {"pedido": pedido, "itens": itens, "historico": historico}


@app.put("/api/reposicao/pedidos/{pedido_id}/status")
def atualizar_status_pedido(pedido_id: int, payload: dict[str, Any] = Body(...)):
    novo_status = str(payload.get("status") or "").upper()
    if novo_status not in REPOSICAO_STATUS_LIST:
        raise HTTPException(status_code=422, detail=f"Status inválido. Opções: {REPOSICAO_STATUS_LIST}")

    observacao = payload.get("observacao")
    usuario = payload.get("usuario", "manual")

    # Buscar status atual
    pedido = fetch_one(
        "SELECT id, status FROM reposicao_pedidos WHERE id = %(pedido_id)s",
        {"pedido_id": pedido_id},
    )
    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido não encontrado.")

    status_anterior = pedido["status"]

    # Atualizar pedido
    execute_transaction([
        (
            """
            UPDATE reposicao_pedidos
            SET status = %(status)s, atualizado_em = NOW()
            WHERE id = %(pedido_id)s;
            """,
            {"pedido_id": pedido_id, "status": novo_status},
        ),
        (
            """
            INSERT INTO reposicao_pedido_historico (pedido_id, status_anterior, status_novo, usuario, observacao)
            VALUES (%(pedido_id)s, %(status_anterior)s, %(status_novo)s, %(usuario)s, %(observacao)s);
            """,
            {
                "pedido_id": pedido_id,
                "status_anterior": status_anterior,
                "status_novo": novo_status,
                "usuario": usuario,
                "observacao": observacao,
            },
        ),
    ])

    # Opcionalmente atualizar todos os itens também
    if payload.get("atualizar_itens"):
        execute_transaction([
            (
                """
                UPDATE reposicao_pedido_itens
                SET status = %(status)s, atualizado_em = NOW()
                WHERE pedido_id = %(pedido_id)s;
                """,
                {"pedido_id": pedido_id, "status": novo_status},
            ),
        ])

    return {"success": True, "status_anterior": status_anterior, "status_novo": novo_status}


@app.put("/api/reposicao/itens/{item_id}/status")
def atualizar_status_item(item_id: int, payload: dict[str, Any] = Body(...)):
    novo_status = str(payload.get("status") or "").upper()
    if novo_status not in REPOSICAO_STATUS_LIST:
        raise HTTPException(status_code=422, detail=f"Status inválido. Opções: {REPOSICAO_STATUS_LIST}")

    observacao = payload.get("observacao")
    usuario = payload.get("usuario", "manual")

    # Buscar item atual
    item = fetch_one(
        "SELECT id, pedido_id, status FROM reposicao_pedido_itens WHERE id = %(item_id)s",
        {"item_id": item_id},
    )
    if not item:
        raise HTTPException(status_code=404, detail="Item não encontrado.")

    status_anterior = item["status"]
    pedido_id = item["pedido_id"]

    # Atualizar item
    execute_transaction([
        (
            """
            UPDATE reposicao_pedido_itens
            SET status = %(status)s, observacao = %(observacao)s, atualizado_em = NOW()
            WHERE id = %(item_id)s;
            """,
            {"item_id": item_id, "status": novo_status, "observacao": observacao},
        ),
        (
            """
            INSERT INTO reposicao_pedido_historico (pedido_id, item_id, status_anterior, status_novo, usuario, observacao)
            VALUES (%(pedido_id)s, %(item_id)s, %(status_anterior)s, %(status_novo)s, %(usuario)s, %(observacao)s);
            """,
            {
                "pedido_id": pedido_id,
                "item_id": item_id,
                "status_anterior": status_anterior,
                "status_novo": novo_status,
                "usuario": usuario,
                "observacao": observacao,
            },
        ),
    ])

    return {"success": True, "status_anterior": status_anterior, "status_novo": novo_status}


@app.get("/api/analise/skus-sem-reposicao")
def skus_sem_reposicao(
    year: int = Query(default=2026, ge=2020, le=2035),
    cd_loja: int | None = Query(default=None),
    limit: int = Query(default=500, ge=1, le=5000),
    status_produto: str | None = Query(default=None),
    continuidade: str | None = Query(default=None),
    linha: str | None = Query(default=None),
    familia: str | None = Query(default=None),
):
    table = source_analytic_table()
    is_cached = table == "cache_reposicao_analitico_classificado"
    loja_filter = "AND base.cd_loja = %(cd_loja)s" if cd_loja else ""
    params: dict[str, Any] = {"year_like": f"{year}-%", "limit": limit}
    if cd_loja:
        params["cd_loja"] = cd_loja
    filter_builder = product_classification_column_filter_sql if is_cached else product_classification_filter_sql
    product_filter_sql, filter_params = filter_builder(
        "a", status_produto=status_produto, continuidade=continuidade, linha=linha, familia=familia
    )
    base_classification_fields = (
        ""
        if is_cached
        else """
                cls.status_produto,
                cls.continuidade,
                cls.linha,
                cls.familia,
                COALESCE(p.ds_cor, '') AS cor,
                COALESCE(p.ds_tamanho, '') AS tamanho,
        """
    )
    base_classification_join = (
        ""
        if is_cached
        else f"""
            LEFT JOIN vr_prd_prdgrade p
                ON p.cd_produto = a.cd_produto
            LEFT JOIN LATERAL (
                SELECT
                    {product_classification_select("a")}
            ) cls ON TRUE
        """
    )
    params.update(filter_params)

    query = skus_sem_reposicao_query(
        table,
        is_cached,
        product_filter_sql,
        loja_filter,
        """
        SELECT
            empresa,
            referencia,
            status_produto,
            continuidade,
            linha,
            familia,
            cor,
            tamanho,
            sku,
            ultima_venda_antes_ruptura,
            media_venda_antes_ruptura,
            data_ultima_entrada,
            quantidade_ultima_entrada,
            data_inicio_falta,
            necessidade_identificada,
            quantidade_reposta_depois,
            dias_sem_reposicao,
            venda_apos_ruptura,
            status
        FROM final
        """,
        """
        ORDER BY
            CASE WHEN status = 'PERDIDO' THEN 0 ELSE 1 END,
            dias_sem_reposicao DESC,
            necessidade_identificada DESC
        LIMIT %(limit)s;
        """,
    )
    return fetch_all(query, params)

    return fetch_all(
        f"""
        WITH base AS (
            SELECT
                a.*,
                {base_classification_fields}
                TO_DATE(a.mes || '-01', 'YYYY-MM-DD') AS mes_data
            FROM {table} a
            {base_classification_join}
            WHERE a.mes LIKE %(year_like)s
              {product_filter_sql}
        ),
        base_meta AS (
            SELECT MAX(mes) AS mes_atual
            FROM base
        ),
        base_skus AS (
            SELECT DISTINCT cd_loja, cd_produto
            FROM base
        ),
        entradas_historicas AS (
            SELECT
                t.cd_empresa AS cd_loja,
                i.cd_produto,
                i.dt_transacao::date AS data_entrada,
                SUM(i.qt_solicitada) AS quantidade_entrada
            FROM base_skus bs
            JOIN vr_tra_transacao t
                ON t.cd_empresa = bs.cd_loja
            JOIN vr_tra_transitem i
                ON i.nr_transacao = t.nr_transacao
               AND i.cd_empresa = t.cd_empresa
               AND i.cd_produto = bs.cd_produto
            WHERE t.tp_operacao = 'E'
              AND t.tp_situacao = 4
              AND i.dt_transacao::date <= CURRENT_DATE
            GROUP BY t.cd_empresa, i.cd_produto, i.dt_transacao::date
        ),
        ultima_entrada AS (
            SELECT DISTINCT ON (cd_loja, cd_produto)
                cd_loja,
                cd_produto,
                data_entrada AS data_ultima_entrada,
                quantidade_entrada AS quantidade_ultima_entrada
            FROM entradas_historicas
            ORDER BY cd_loja, cd_produto, data_entrada DESC
        ),
        rupturas AS (
            SELECT
                cd_loja,
                cd_produto,
                MIN(mes) AS mes_inicio_falta
            FROM base
            WHERE necessidade > 0
              AND COALESCE(entrada_total, 0) < necessidade
              AND (COALESCE(saldo_inicial, 0) <= 0 OR COALESCE(saldo_inicial, 0) < estoque_minimo)
            GROUP BY cd_loja, cd_produto
            HAVING MIN(mes) < (SELECT mes_atual FROM base_meta)
        ),
        analise AS (
            SELECT
                r.cd_loja,
                b.nome_loja,
                r.cd_produto,
                MAX(b.referencia) AS referencia,
                MAX(b.descricao_produto) AS descricao_produto,
                MAX(b.status_produto) AS status_produto,
                MAX(b.continuidade) AS continuidade,
                MAX(b.linha) AS linha,
                MAX(b.familia) AS familia,
                MAX(b.cor) AS cor,
                MAX(b.tamanho) AS tamanho,
                r.mes_inicio_falta,
                MAX(b.mes) FILTER (
                    WHERE b.mes <= r.mes_inicio_falta AND COALESCE(b.vendas_3m, 0) > 0
                ) AS ultima_venda_antes_ruptura,
                MAX(b.media_mensal) FILTER (WHERE b.mes = r.mes_inicio_falta) AS media_venda_antes_ruptura,
                MAX(b.necessidade) FILTER (WHERE b.mes = r.mes_inicio_falta) AS necessidade_identificada,
                MAX(ue.data_ultima_entrada) AS data_ultima_entrada,
                MAX(ue.quantidade_ultima_entrada) AS quantidade_ultima_entrada,
                SUM(b.entrada_total) FILTER (WHERE b.mes > r.mes_inicio_falta) AS quantidade_reposta_depois,
                SUM(b.vendas_3m) FILTER (WHERE b.mes > r.mes_inicio_falta) AS venda_apos_ruptura,
                MAX(b.media_mensal) FILTER (WHERE b.mes > r.mes_inicio_falta) AS maior_media_apos_ruptura,
                GREATEST(
                    0,
                    COALESCE(
                        CURRENT_DATE - MAX(ue.data_ultima_entrada),
                        CURRENT_DATE - TO_DATE(r.mes_inicio_falta || '-01', 'YYYY-MM-DD')
                    )
                )::integer AS dias_sem_reposicao
            FROM rupturas r
            JOIN base b
                ON b.cd_loja = r.cd_loja
               AND b.cd_produto = r.cd_produto
            LEFT JOIN ultima_entrada ue
                ON ue.cd_loja = r.cd_loja
               AND ue.cd_produto = r.cd_produto
            WHERE 1 = 1
              {loja_filter}
            GROUP BY r.cd_loja, b.nome_loja, r.cd_produto, r.mes_inicio_falta
        )
        SELECT
            nome_loja AS empresa,
            referencia,
            status_produto,
            continuidade,
            linha,
            familia,
            cor,
            tamanho,
            cd_produto AS sku,
            ultima_venda_antes_ruptura,
            COALESCE(media_venda_antes_ruptura, 0) AS media_venda_antes_ruptura,
            data_ultima_entrada,
            COALESCE(quantidade_ultima_entrada, 0) AS quantidade_ultima_entrada,
            mes_inicio_falta AS data_inicio_falta,
            COALESCE(necessidade_identificada, 0) AS necessidade_identificada,
            COALESCE(quantidade_reposta_depois, 0) AS quantidade_reposta_depois,
            dias_sem_reposicao,
            COALESCE(venda_apos_ruptura, 0) AS venda_apos_ruptura,
            CASE
                WHEN COALESCE(quantidade_reposta_depois, 0) >= COALESCE(necessidade_identificada, 0)
                    THEN 'RECUPERANDO'
                WHEN COALESCE(maior_media_apos_ruptura, 0) <= COALESCE(media_venda_antes_ruptura, 0) * 0.5
                    THEN 'PERDIDO'
                ELSE 'EM RISCO'
            END AS status
        FROM analise
        WHERE COALESCE(media_venda_antes_ruptura, 0) > 0
        ORDER BY
            CASE
                WHEN COALESCE(maior_media_apos_ruptura, 0) <= COALESCE(media_venda_antes_ruptura, 0) * 0.5 THEN 0
                ELSE 1
            END,
            dias_sem_reposicao DESC,
            necessidade_identificada DESC
        LIMIT %(limit)s;
        """,
        params,
    )


def skus_sem_reposicao_query(
    table: str,
    is_cached: bool,
    product_filter_sql: str,
    loja_filter: str,
    select_sql: str,
    order_limit_sql: str = "",
) -> str:
    base_classification_fields = (
        ""
        if is_cached
        else """
                cls.status_produto,
                cls.continuidade,
                cls.linha,
                cls.familia,
                COALESCE(p.ds_cor, '') AS cor,
                COALESCE(p.ds_tamanho, '') AS tamanho,
        """
    )
    base_classification_join = (
        ""
        if is_cached
        else f"""
            LEFT JOIN vr_prd_prdgrade p
                ON p.cd_produto = a.cd_produto
            LEFT JOIN LATERAL (
                SELECT
                    {product_classification_select("a")}
            ) cls ON TRUE
        """
    )
    has_historical_entry_cache = is_cached and column_exists(
        "cache_reposicao_analitico_classificado", "data_ultima_entrada_historica"
    )
    ultima_entrada_cte = (
        """
        ultima_entrada AS (
            SELECT DISTINCT ON (cd_loja, cd_produto)
                cd_loja,
                cd_produto,
                data_ultima_entrada_historica AS data_ultima_entrada,
                quantidade_ultima_entrada_historica AS quantidade_ultima_entrada
            FROM base
            WHERE data_ultima_entrada_historica IS NOT NULL
            ORDER BY cd_loja, cd_produto, data_ultima_entrada_historica DESC
        ),
        """
        if has_historical_entry_cache
        else """
        ultima_entrada AS (
            SELECT DISTINCT ON (cd_loja, cd_produto)
                cd_loja,
                cd_produto,
                ultima_entrada AS data_ultima_entrada,
                entrada_total AS quantidade_ultima_entrada
            FROM base
            WHERE ultima_entrada IS NOT NULL
            ORDER BY cd_loja, cd_produto, ultima_entrada DESC, mes DESC
        ),
        """
    )
    return f"""
        WITH base AS (
            SELECT
                a.*,
                {base_classification_fields}
                TO_DATE(a.mes || '-01', 'YYYY-MM-DD') AS mes_data
            FROM {table} a
            {base_classification_join}
            WHERE a.mes LIKE %(year_like)s
              {product_filter_sql}
        ),
        base_meta AS (
            SELECT MAX(mes) AS mes_atual
            FROM base
        ),
        {ultima_entrada_cte}
        rupturas AS (
            SELECT
                cd_loja,
                cd_produto,
                MIN(mes) AS mes_inicio_falta
            FROM base
            WHERE necessidade > 0
              AND COALESCE(entrada_total, 0) < necessidade
              AND (COALESCE(saldo_inicial, 0) <= 0 OR COALESCE(saldo_inicial, 0) < estoque_minimo)
            GROUP BY cd_loja, cd_produto
            HAVING MIN(mes) < (SELECT mes_atual FROM base_meta)
        ),
        analise AS (
            SELECT
                r.cd_loja,
                b.nome_loja,
                r.cd_produto,
                MAX(b.referencia) AS referencia,
                MAX(b.descricao_produto) AS descricao_produto,
                MAX(b.status_produto) AS status_produto,
                MAX(b.continuidade) AS continuidade,
                MAX(b.linha) AS linha,
                MAX(b.familia) AS familia,
                MAX(b.cor) AS cor,
                MAX(b.tamanho) AS tamanho,
                r.mes_inicio_falta,
                MAX(b.mes) FILTER (
                    WHERE b.mes <= r.mes_inicio_falta AND COALESCE(b.vendas_3m, 0) > 0
                ) AS ultima_venda_antes_ruptura,
                MAX(b.media_mensal) FILTER (WHERE b.mes = r.mes_inicio_falta) AS media_venda_antes_ruptura,
                MAX(b.necessidade) FILTER (WHERE b.mes = r.mes_inicio_falta) AS necessidade_identificada,
                MAX(ue.data_ultima_entrada) AS data_ultima_entrada,
                MAX(ue.quantidade_ultima_entrada) AS quantidade_ultima_entrada,
                SUM(b.entrada_total) FILTER (WHERE b.mes > r.mes_inicio_falta) AS quantidade_reposta_depois,
                SUM(b.vendas_3m) FILTER (WHERE b.mes > r.mes_inicio_falta) AS venda_apos_ruptura,
                MAX(b.media_mensal) FILTER (WHERE b.mes > r.mes_inicio_falta) AS maior_media_apos_ruptura,
                GREATEST(
                    0,
                    COALESCE(
                        CURRENT_DATE - MAX(ue.data_ultima_entrada),
                        CURRENT_DATE - TO_DATE(r.mes_inicio_falta || '-01', 'YYYY-MM-DD')
                    )
                )::integer AS dias_sem_reposicao
            FROM rupturas r
            JOIN base b
                ON b.cd_loja = r.cd_loja
               AND b.cd_produto = r.cd_produto
            LEFT JOIN ultima_entrada ue
                ON ue.cd_loja = r.cd_loja
               AND ue.cd_produto = r.cd_produto
            WHERE 1 = 1
              {loja_filter}
            GROUP BY r.cd_loja, b.nome_loja, r.cd_produto, r.mes_inicio_falta
        ),
        final AS (
            SELECT
                nome_loja AS empresa,
                referencia,
                status_produto,
                continuidade,
                linha,
                familia,
                cor,
                tamanho,
                cd_produto AS sku,
                ultima_venda_antes_ruptura,
                COALESCE(media_venda_antes_ruptura, 0) AS media_venda_antes_ruptura,
                data_ultima_entrada,
                COALESCE(quantidade_ultima_entrada, 0) AS quantidade_ultima_entrada,
                mes_inicio_falta AS data_inicio_falta,
                COALESCE(necessidade_identificada, 0) AS necessidade_identificada,
                COALESCE(quantidade_reposta_depois, 0) AS quantidade_reposta_depois,
                dias_sem_reposicao,
                COALESCE(venda_apos_ruptura, 0) AS venda_apos_ruptura,
                CASE
                    WHEN COALESCE(quantidade_reposta_depois, 0) >= COALESCE(necessidade_identificada, 0)
                        THEN 'RECUPERANDO'
                    WHEN COALESCE(maior_media_apos_ruptura, 0) <= COALESCE(media_venda_antes_ruptura, 0) * 0.5
                        THEN 'PERDIDO'
                    ELSE 'EM RISCO'
                END AS status,
                maior_media_apos_ruptura
            FROM analise
            WHERE COALESCE(media_venda_antes_ruptura, 0) > 0
        )
        {select_sql}
        {order_limit_sql}
    """


@app.get("/api/analise/skus-sem-reposicao/resumo")
def skus_sem_reposicao_resumo(
    year: int = Query(default=2026, ge=2020, le=2035),
    cd_loja: int | None = Query(default=None),
    status_produto: str | None = Query(default=None),
    continuidade: str | None = Query(default=None),
    linha: str | None = Query(default=None),
    familia: str | None = Query(default=None),
):
    table = source_analytic_table()
    is_cached = table == "cache_reposicao_analitico_classificado"
    loja_filter = "AND base.cd_loja = %(cd_loja)s" if cd_loja else ""
    params: dict[str, Any] = {"year_like": f"{year}-%"}
    if cd_loja:
        params["cd_loja"] = cd_loja
    filter_builder = product_classification_column_filter_sql if is_cached else product_classification_filter_sql
    product_filter_sql, filter_params = filter_builder(
        "a", status_produto=status_produto, continuidade=continuidade, linha=linha, familia=familia
    )
    params.update(filter_params)
    query = skus_sem_reposicao_query(
        table,
        is_cached,
        product_filter_sql,
        loja_filter,
        """
        SELECT
            COUNT(*) AS total,
            COUNT(*) FILTER (WHERE status = 'PERDIDO') AS perdidos,
            COUNT(*) FILTER (WHERE status = 'EM RISCO') AS risco,
            COUNT(*) FILTER (WHERE status = 'RECUPERANDO') AS recuperando,
            COUNT(DISTINCT empresa) AS empresas,
            MAX(data_ultima_entrada) AS data_ultima_entrada,
            MIN(data_inicio_falta) AS data_inicio_falta,
            SUM(necessidade_identificada) AS necessidade_identificada,
            SUM(quantidade_reposta_depois) AS quantidade_reposta_depois,
            MAX(dias_sem_reposicao) AS dias_sem_reposicao,
            SUM(venda_apos_ruptura) AS venda_apos_ruptura
        FROM final
        """,
    )
    return fetch_one(query, params) or {
        "total": 0,
        "perdidos": 0,
        "risco": 0,
        "recuperando": 0,
        "empresas": 0,
        "data_ultima_entrada": None,
        "data_inicio_falta": None,
        "necessidade_identificada": 0,
        "quantidade_reposta_depois": 0,
        "dias_sem_reposicao": 0,
        "venda_apos_ruptura": 0,
    }


@app.get("/api/dashboard/alertas")
def dashboard_alertas(month: str | None = Query(default=None, pattern=r"^\d{4}-\d{2}$")):
    table = source_summary_table()
    month_row = fetch_one(f"SELECT COALESCE(%(month)s, MAX(mes)) AS mes FROM {table};", {"month": month})
    target_month = month_row["mes"] if month_row else month
    lojas = fetch_all(
        f"""
        SELECT cd_loja, nome_loja, necessidade_total, entrada_total, taxa_atendimento, faltou
        FROM {table}
        WHERE mes = %(month)s
          AND necessidade_total > 0
          AND taxa_atendimento < 50
        ORDER BY taxa_atendimento, faltou DESC
        LIMIT 20;
        """,
        {"month": target_month},
    )
    alertas = [
        {
            "tipo": "LOJA_CRITICA",
            "severidade": "alto",
            "mensagem": f"{row['nome_loja']} com {row['taxa_atendimento']}% de atendimento",
            "dados": row,
            "criado_em": datetime.now().isoformat(),
        }
        for row in lojas
    ]

    if relation_exists("public.cache_skus_mortos"):
        refs = fetch_all(
            """
            SELECT referencia, COUNT(DISTINCT cd_loja) AS lojas_afetadas, MAX(curva_original) AS curva
            FROM cache_skus_mortos
            GROUP BY referencia
            HAVING COUNT(DISTINCT cd_loja) >= 3
            ORDER BY lojas_afetadas DESC, referencia
            LIMIT 20;
            """
        )
        alertas.extend(
            {
                "tipo": "REFERENCIA_MORRENDO",
                "severidade": "critico" if row["curva"] in ("CURVA A", "CURVA AA") else "alto",
                "mensagem": f"Referencia {row['referencia']} zerou em {row['lojas_afetadas']} lojas",
                "dados": row,
                "criado_em": datetime.now().isoformat(),
            }
            for row in refs
        )
    return alertas


@app.get("/api/analise/por-mes/{mes}")
def analise_por_mes(mes: str):
    table = source_summary_table()
    return fetch_all(
        f"""
        SELECT *
        FROM {table}
        WHERE mes = %(mes)s
        ORDER BY faltou DESC, taxa_atendimento NULLS FIRST, nome_loja;
        """,
        {"mes": mes},
    )


@app.get("/api/analise/por-loja/{cd_loja}")
def analise_por_loja(cd_loja: int, year: int = Query(default=2026, ge=2020, le=2035)):
    table = source_summary_table()
    return fetch_all(
        f"""
        SELECT *
        FROM {table}
        WHERE cd_loja = %(cd_loja)s
          AND mes LIKE %(year_like)s
        ORDER BY mes;
        """,
        {"cd_loja": cd_loja, "year_like": f"{year}-%"},
    )


@app.get("/api/analise/entradas/{mes}")
def analise_entradas(mes: str):
    table = source_summary_table()
    return fetch_all(
        f"""
        SELECT
            cd_loja,
            nome_loja,
            entrada_periodo,
            entrada_atrasada,
            entrada_sem_lote,
            entrada_total
        FROM {table}
        WHERE mes = %(mes)s
        ORDER BY entrada_sem_lote DESC, entrada_atrasada DESC, nome_loja;
        """,
        {"mes": mes},
    )


@app.get("/api/analise/necessidade-zerada")
def analise_necessidade_zerada(limit: int = Query(default=200, ge=1, le=1000)):
    if relation_exists("public.cache_skus_mortos"):
        return fetch_all(
            """
            SELECT *
            FROM cache_skus_mortos
            ORDER BY meses_sem_estoque DESC, vendas_historico DESC
            LIMIT %(limit)s;
            """,
            {"limit": limit},
        )
    return []


@app.get("/api/micro/sku/{cd_produto}")
def micro_sku(cd_produto: int):
    table = source_analytic_table()
    return fetch_all(
        f"""
        SELECT *
        FROM {table}
        WHERE cd_produto = %(cd_produto)s
        ORDER BY mes, nome_loja;
        """,
        {"cd_produto": cd_produto},
    )


@app.get("/api/micro/loja/{cd_loja}/criticos")
def micro_loja_criticos(
    cd_loja: int,
    month: str | None = Query(default=None, pattern=r"^\d{4}-\d{2}$"),
    limit: int = Query(default=200, ge=1, le=1000),
):
    table = source_analytic_table()
    month_row = fetch_one(f"SELECT COALESCE(%(month)s, MAX(mes)) AS mes FROM {table};", {"month": month})
    target_month = month_row["mes"] if month_row else month
    return fetch_all(
        f"""
        SELECT *
        FROM {table}
        WHERE cd_loja = %(cd_loja)s
          AND mes = %(month)s
          AND curva_completa IN ('CURVA A', 'CURVA AA', 'CURVA B')
          AND status_reposicao IN ('ZERADO', 'PARCIAL')
        ORDER BY curva_completa, faltou DESC, referencia
        LIMIT %(limit)s;
        """,
        {"cd_loja": cd_loja, "month": target_month, "limit": limit},
    )


@app.get("/api/micro/referencias-morrendo")
def micro_referencias_morrendo(limit: int = Query(default=100, ge=1, le=1000)):
    if relation_exists("public.cache_skus_mortos"):
        return fetch_all(
            """
            SELECT
                referencia,
                MAX(descricao_produto) AS descricao_produto,
                MAX(curva_original) AS curva_original,
                COUNT(DISTINCT cd_loja) AS lojas_afetadas,
                MAX(meses_sem_estoque) AS maior_tempo_sem_estoque,
                SUM(vendas_historico) AS vendas_historico
            FROM cache_skus_mortos
            GROUP BY referencia
            ORDER BY lojas_afetadas DESC, maior_tempo_sem_estoque DESC, vendas_historico DESC
            LIMIT %(limit)s;
            """,
            {"limit": limit},
        )
    return []


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
