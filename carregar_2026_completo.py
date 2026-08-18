"""
Carrega extrato de reposicao para todos os meses de 2026
Executa mes a mes para evitar timeout
"""

import os
from dotenv import load_dotenv
import psycopg2
from datetime import datetime

load_dotenv()

def get_connection():
    return psycopg2.connect(
        host=os.getenv('DB_HOST'),
        port=os.getenv('DB_PORT'),
        dbname=os.getenv('DB_NAME'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD')
    )

def criar_tabela(conn):
    """Cria a tabela vazia"""
    cur = conn.cursor()
    cur.execute("""
        DROP TABLE IF EXISTS extrato_reposicao_loja_perm_analitico;

        CREATE TABLE extrato_reposicao_loja_perm_analitico (
            mes VARCHAR(7),
            cd_loja INTEGER,
            nome_loja VARCHAR(100),
            cd_produto BIGINT,
            referencia VARCHAR(50),
            descricao_produto VARCHAR(200),
            curva_completa VARCHAR(50),
            vendas_3m NUMERIC,
            media_mensal NUMERIC,
            estoque_minimo NUMERIC,
            saldo_inicial NUMERIC,
            necessidade NUMERIC,
            entrada_periodo NUMERIC,
            entrada_atrasada NUMERIC,
            entrada_sem_lote NUMERIC,
            entrada_total NUMERIC,
            faltou NUMERIC,
            sobra_periodo NUMERIC,
            qtd_transacoes_periodo INTEGER,
            qtd_transacoes_atrasadas INTEGER,
            primeira_entrada DATE,
            ultima_entrada DATE,
            lotes_entrada TEXT,
            status_reposicao VARCHAR(20),
            status_entrada VARCHAR(30)
        );
    """)
    conn.commit()
    print("Tabela criada!")

def carregar_mes(conn, mes):
    """Carrega dados de um mes especifico"""

    ano, mes_num = mes.split('-')
    inicio_mes = f"{mes}-01"

    # Calcular fim do mes
    if int(mes_num) == 12:
        fim_mes = f"{int(ano)+1}-01-01"
    else:
        fim_mes = f"{ano}-{int(mes_num)+1:02d}-01"

    # Pattern do lote (ex: '26.06%' para junho/2026)
    lote_periodo = f"{ano[2:]}.{mes_num}%"

    print(f"\n{'='*60}")
    print(f"Carregando {mes} (lote: {lote_periodo})")
    print(f"Periodo: {inicio_mes} a {fim_mes}")
    print(f"{'='*60}")

    query = """
    INSERT INTO extrato_reposicao_loja_perm_analitico
    WITH produtos_permanente AS (
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
            %(mes)s AS mes,
            t.cd_empresa AS cd_loja,
            i.cd_produto,
            i.qt_solicitada AS qt_entrada,
            t.nr_transacao,
            i.dt_transacao,
            lote.cd_lote,
            CASE
                WHEN lote.cd_lote LIKE %(lote_periodo)s THEN 'PERIODO'
                WHEN lote.cd_lote IS NULL THEN 'SEM_LOTE'
                ELSE 'ATRASADA'
            END AS tipo_entrada
        FROM vr_tra_transacao t
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
          AND t.cd_empresaori = 1
          AND i.dt_transacao >= %(inicio_mes)s::date
          AND i.dt_transacao < %(fim_mes)s::date
    ),

    entradas_agregadas AS (
        SELECT
            mes,
            cd_loja,
            cd_produto,
            COALESCE(SUM(qt_entrada) FILTER (WHERE tipo_entrada = 'PERIODO'), 0) AS entrada_periodo,
            COALESCE(SUM(qt_entrada) FILTER (WHERE tipo_entrada = 'ATRASADA'), 0) AS entrada_atrasada,
            COALESCE(SUM(qt_entrada) FILTER (WHERE tipo_entrada = 'SEM_LOTE'), 0) AS entrada_sem_lote,
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
            %(mes)s AS mes,
            %(inicio_mes)s::date AS inicio_mes,
            t.cd_empresa AS cd_loja,
            i.cd_produto,
            SUM(
                i.qt_solicitada *
                CASE WHEN t.tp_modalidade::text = '3' THEN -1 ELSE 1 END
            ) AS vendas_3m
        FROM vr_tra_transacao t
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
          AND i.dt_transacao >= %(inicio_mes)s::date - INTERVAL '3 months'
          AND i.dt_transacao < %(inicio_mes)s::date
          AND i.cd_compvend <> 1
          AND t.tp_situacao <> 6
          AND t.tp_modalidade::text IN ('3', '4')
        GROUP BY t.cd_empresa, i.cd_produto
        HAVING SUM(
            i.qt_solicitada *
            CASE WHEN t.tp_modalidade::text = '3' THEN -1 ELSE 1 END
        ) > 0
    ),

    base_sem_curva AS (
        SELECT
            v.mes,
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

    analise AS (
        SELECT
            b.*,
            GREATEST(0, b.estoque_minimo - b.saldo_inicial) AS necessidade,
            COALESCE(e.entrada_periodo, 0) AS entrada_periodo,
            COALESCE(e.entrada_atrasada, 0) AS entrada_atrasada,
            COALESCE(e.entrada_sem_lote, 0) AS entrada_sem_lote,
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
    )

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
        entrada_sem_lote,
        entrada_total,
        GREATEST(0, necessidade - entrada_total) AS faltou,
        GREATEST(0, entrada_periodo - necessidade) AS sobra_periodo,
        qtd_transacoes_periodo,
        qtd_transacoes_atrasadas,
        primeira_entrada,
        ultima_entrada,
        lotes_entrada,
        CASE
            WHEN necessidade <= 0 THEN 'SEM NECESSIDADE'
            WHEN entrada_total >= necessidade THEN 'OK'
            WHEN entrada_total > 0 THEN 'PARCIAL'
            ELSE 'ZERADO'
        END AS status_reposicao,
        CASE
            WHEN entrada_atrasada > 0 AND entrada_periodo > 0 THEN 'PERIODO + ATRASADA'
            WHEN entrada_atrasada > 0 THEN 'SOMENTE ATRASADA'
            WHEN entrada_sem_lote > 0 THEN 'FABRICA SEM LOTE'
            WHEN entrada_periodo > 0 THEN 'SOMENTE PERIODO'
            ELSE 'SEM ENTRADA'
        END AS status_entrada
    FROM analise;
    """

    cur = conn.cursor()
    inicio = datetime.now()

    cur.execute(query, {
        'mes': mes,
        'inicio_mes': inicio_mes,
        'fim_mes': fim_mes,
        'lote_periodo': lote_periodo
    })

    conn.commit()

    # Contar registros inseridos
    cur.execute("SELECT COUNT(*) FROM extrato_reposicao_loja_perm_analitico WHERE mes = %s", (mes,))
    count = cur.fetchone()[0]

    duracao = (datetime.now() - inicio).total_seconds()
    print(f"Inseridos {count:,} registros em {duracao:.1f}s")

    return count

def criar_indices(conn):
    """Cria indices apos carregar todos os dados"""
    print("\nCriando indices...")
    cur = conn.cursor()
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_extrato_reposicao_perm_analitico_mes_loja
            ON extrato_reposicao_loja_perm_analitico (mes, cd_loja);

        CREATE INDEX IF NOT EXISTS idx_extrato_reposicao_perm_analitico_produto
            ON extrato_reposicao_loja_perm_analitico (cd_produto);

        CREATE INDEX IF NOT EXISTS idx_extrato_reposicao_perm_analitico_status
            ON extrato_reposicao_loja_perm_analitico (status_reposicao, status_entrada);
    """)
    conn.commit()
    print("Indices criados!")

def main():
    # Meses a carregar (julho a janeiro, de tras para frente)
    meses = [
        '2026-07',
        '2026-06',
        '2026-05',
        '2026-04',
        '2026-03',
        '2026-02',
        '2026-01'
    ]

    print("="*60)
    print("CARREGANDO EXTRATO DE REPOSICAO 2026")
    print(f"Meses: {meses[0]} a {meses[-1]}")
    print("="*60)

    conn = get_connection()

    # Criar tabela
    criar_tabela(conn)

    # Carregar cada mes
    total = 0
    inicio_total = datetime.now()

    for mes in meses:
        try:
            count = carregar_mes(conn, mes)
            total += count
        except Exception as e:
            print(f"ERRO no mes {mes}: {e}")
            raise

    # Criar indices
    criar_indices(conn)

    duracao_total = (datetime.now() - inicio_total).total_seconds()

    print("\n" + "="*60)
    print("RESUMO FINAL")
    print("="*60)
    print(f"Total de registros: {total:,}")
    print(f"Tempo total: {duracao_total/60:.1f} minutos")

    # Mostrar resumo por mes
    cur = conn.cursor()
    cur.execute("""
        SELECT
            mes,
            COUNT(DISTINCT cd_loja) AS lojas,
            COUNT(*) AS registros,
            SUM(necessidade) AS necessidade,
            SUM(entrada_total) AS entrada_total,
            SUM(faltou) AS faltou
        FROM extrato_reposicao_loja_perm_analitico
        GROUP BY mes
        ORDER BY mes
    """)

    print("\nRESUMO POR MES:")
    print("-"*80)
    print(f"{'MES':<10} {'LOJAS':>6} {'REGISTROS':>12} {'NECESSIDADE':>14} {'ENTRADA':>14} {'FALTOU':>12}")
    print("-"*80)

    for row in cur.fetchall():
        print(f"{row[0]:<10} {row[1]:>6} {row[2]:>12,} {row[3]:>14,.0f} {row[4]:>14,.0f} {row[5]:>12,.0f}")

    conn.close()
    print("\nConcluido!")

if __name__ == "__main__":
    main()
