"""
Analise de Reposicao por Loja - Curva ABC
Verifica se cada loja esta recebendo as reposicoes corretas:
- Curva A/AA: 1 reposicao por mes (LOTE 2)
- Curva B/C: 2 ressuprimentos por mes
"""

import os
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
from dotenv import load_dotenv
import psycopg2
import pandas as pd

load_dotenv()

def get_connection():
    """Cria conexao com o banco PostgreSQL"""
    return psycopg2.connect(
        host=os.getenv('DB_HOST'),
        port=os.getenv('DB_PORT'),
        dbname=os.getenv('DB_NAME'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD')
    )

def get_meses_fechados():
    """Retorna os ultimos 3 meses fechados"""
    hoje = date.today()
    inicio_mes_atual = hoje.replace(day=1)

    mes1 = inicio_mes_atual - relativedelta(months=1)
    mes2 = inicio_mes_atual - relativedelta(months=2)
    mes3 = inicio_mes_atual - relativedelta(months=3)

    return {
        'inicio': mes3,
        'fim': inicio_mes_atual,
        'meses': [mes3, mes2, mes1]
    }

def analisar_reposicoes_lojas(mes_analise='2026-06'):
    """
    Analisa reposicoes por loja em um mes especifico
    """

    # Extrair ano e mes
    ano, mes = mes_analise.split('-')
    inicio_mes = f"{ano}-{mes}-01"

    # Calcular fim do mes
    dt_inicio = datetime.strptime(inicio_mes, '%Y-%m-%d')
    if int(mes) == 12:
        fim_mes = f"{int(ano)+1}-01-01"
    else:
        fim_mes = f"{ano}-{int(mes)+1:02d}-01"

    query = """
    -- =====================================================
    -- CTE 1: Entradas nas lojas no mes
    -- =====================================================
    WITH entradas_mes AS (
        SELECT
            t.cd_empresa AS cd_loja,
            i.cd_produto,
            i.dt_transacao,
            i.qt_solicitada AS qt_entrada,
            t.nr_transacao,
            DATE_PART('day', i.dt_transacao) AS dia_entrada
        FROM vr_tra_transacao t
        JOIN vr_tra_transitem i
            ON t.nr_transacao = i.nr_transacao
            AND t.cd_empresa = i.cd_empresa
        WHERE t.cd_empresa > 1
            AND t.tp_operacao = 'E'
            AND t.tp_modalidade::text = '2'
            AND t.tp_situacao = 4
            AND i.dt_transacao >= %(inicio_mes)s::date
            AND i.dt_transacao < %(fim_mes)s::date
    ),

    -- =====================================================
    -- CTE 2: Agregar entradas por loja/produto com referencia
    -- =====================================================
    entradas_agregadas AS (
        SELECT
            e.cd_loja,
            e.cd_produto,
            f_dic_prd_nivel(e.cd_produto, 'CD'::bpchar) AS referencia,
            COUNT(DISTINCT e.nr_transacao) AS qtd_entradas,
            SUM(e.qt_entrada) AS total_recebido,
            MIN(e.dt_transacao) AS primeira_entrada,
            MAX(e.dt_transacao) AS ultima_entrada,
            -- Verifica se teve entrada na 1a quinzena (dias 1-15)
            COUNT(DISTINCT e.nr_transacao) FILTER (WHERE e.dia_entrada <= 15) AS entradas_quinzena1,
            -- Verifica se teve entrada na 2a quinzena (dias 16-31)
            COUNT(DISTINCT e.nr_transacao) FILTER (WHERE e.dia_entrada > 15) AS entradas_quinzena2
        FROM entradas_mes e
        GROUP BY e.cd_loja, e.cd_produto
    ),

    -- =====================================================
    -- CTE 3: Adicionar curva ABC
    -- =====================================================
    entradas_com_curva AS (
        SELECT
            ea.*,
            COALESCE(abc.curva_completa, 'SEM CURVA') AS curva_completa
        FROM entradas_agregadas ea
        LEFT JOIN curva_abc abc ON abc.referencia = ea.referencia
    ),

    -- =====================================================
    -- CTE 4: Vendas 3 meses fechados por loja/referencia
    -- =====================================================
    vendas_3m AS (
        SELECT
            t.cd_empresa AS cd_loja,
            f_dic_prd_nivel(i.cd_produto, 'CD'::bpchar) AS referencia,
            SUM(i.qt_solicitada * (
                CASE WHEN t.tp_modalidade::text = '3' THEN -1 ELSE 1 END
            )::double precision) AS vendas_3m,
            ROUND(
                SUM(i.qt_solicitada * (
                    CASE WHEN t.tp_modalidade::text = '3' THEN -1 ELSE 1 END
                )::double precision) / 3.0,
                2
            ) AS media_mensal
        FROM vr_tra_transacao t
        JOIN vr_tra_transitem i
            ON t.nr_transacao = i.nr_transacao
            AND t.cd_empresa = i.cd_empresa
        WHERE t.cd_empresa > 1
            AND t.cd_operacao NOT IN (140, 76, 25, 26, 27, 273, 44, 240, 241, 242, 243, 244, 245, 239, 238, 237, 236)
            AND i.dt_transacao >= %(inicio_mes)s::date - INTERVAL '3 months'
            AND i.dt_transacao < %(inicio_mes)s::date
            AND i.cd_compvend <> 1
            AND t.tp_situacao <> 6
            AND t.tp_modalidade::text IN ('3', '4')
        GROUP BY t.cd_empresa, f_dic_prd_nivel(i.cd_produto, 'CD'::bpchar)
    )

    -- =====================================================
    -- SELECT FINAL: Analise consolidada
    -- =====================================================
    SELECT
        ec.cd_loja,
        emp.ds_empresa AS nome_loja,
        ec.referencia,
        ec.curva_completa,
        ec.qtd_entradas,
        ec.total_recebido,
        ec.primeira_entrada,
        ec.ultima_entrada,
        ec.entradas_quinzena1,
        ec.entradas_quinzena2,
        -- Esperado por curva
        CASE
            WHEN ec.curva_completa IN ('CURVA A', 'CURVA AA') THEN 1
            ELSE 2
        END AS entradas_esperadas,
        -- Status da entrada
        CASE
            WHEN ec.curva_completa IN ('CURVA A', 'CURVA AA') AND ec.qtd_entradas >= 1 THEN 'OK'
            WHEN ec.curva_completa NOT IN ('CURVA A', 'CURVA AA') AND ec.qtd_entradas >= 2 THEN 'OK'
            ELSE 'FALTANDO'
        END AS status_entrada,
        -- Vendas e estoque minimo
        COALESCE(v.vendas_3m, 0) AS vendas_3m,
        COALESCE(v.media_mensal, 0) AS media_mensal,
        ROUND(COALESCE(v.media_mensal, 0) * 1.5, 0) AS estoque_minimo
    FROM entradas_com_curva ec
    JOIN vr_ger_empresa emp ON ec.cd_loja = emp.cd_empresa
    LEFT JOIN vendas_3m v ON ec.cd_loja = v.cd_loja AND ec.referencia = v.referencia
    ORDER BY ec.cd_loja, ec.curva_completa, ec.referencia;
    """

    conn = get_connection()
    df = pd.read_sql(query, conn, params={
        'inicio_mes': inicio_mes,
        'fim_mes': fim_mes
    })
    conn.close()

    return df

def gerar_relatorio(df, mes_analise):
    """Gera relatorio de analise"""

    print("=" * 100)
    print(f"ANALISE DE REPOSICOES POR LOJA - {mes_analise}")
    print("=" * 100)

    # Resumo geral
    print(f"\n[RESUMO GERAL]")
    print(f"   Total de registros: {len(df)}")
    print(f"   Lojas analisadas: {df['cd_loja'].nunique()}")
    print(f"   Referencias unicas: {df['referencia'].nunique()}")

    # Resumo por curva
    print(f"\n[RESUMO POR CURVA]")
    curvas = df.groupby('curva_completa').agg({
        'referencia': 'nunique',
        'qtd_entradas': 'sum',
        'total_recebido': 'sum'
    }).rename(columns={
        'referencia': 'refs_unicas',
        'qtd_entradas': 'total_entradas',
        'total_recebido': 'qtd_total'
    })
    print(curvas.to_string())

    # Status das entradas
    print(f"\n[STATUS DAS ENTRADAS]")
    status = df.groupby(['curva_completa', 'status_entrada']).size().unstack(fill_value=0)
    print(status.to_string())

    # Lojas com problemas (FALTANDO)
    faltando = df[df['status_entrada'] == 'FALTANDO']
    if len(faltando) > 0:
        print(f"\n[!] ITENS COM ENTRADA FALTANDO: {len(faltando)}")
        print("-" * 100)

        # Agrupar por loja
        for loja in faltando['cd_loja'].unique()[:5]:  # Limitar a 5 lojas
            loja_items = faltando[faltando['cd_loja'] == loja]
            nome = loja_items['nome_loja'].iloc[0]

            print(f"\n   Loja {loja}: {nome[:50]}")
            print(f"   Itens faltando: {len(loja_items)}")

            # Mostrar alguns itens
            for _, item in loja_items.head(5).iterrows():
                print(f"      - Ref: {item['referencia']} | Curva: {item['curva_completa']} | Entradas: {item['qtd_entradas']}/{item['entradas_esperadas']}")

    return df

def exportar_csv(df, mes_analise):
    """Exporta resultados para CSV"""

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    arquivo = f'reposicao_lojas_{mes_analise}_{timestamp}.csv'

    df.to_csv(arquivo, index=False, encoding='utf-8-sig')
    print(f"\n[EXPORTADO] {arquivo}")

    return arquivo

def main():
    """Funcao principal"""

    # Mes de analise (pode ser parametrizado)
    mes_analise = '2026-06'

    print("Conectando ao banco de dados...")
    print(f"Analisando mes: {mes_analise}")

    try:
        df = analisar_reposicoes_lojas(mes_analise)

        if len(df) == 0:
            print("[!] Nenhum registro encontrado para o periodo!")
        else:
            gerar_relatorio(df, mes_analise)
            exportar_csv(df, mes_analise)

    except Exception as e:
        print(f"[ERRO] {e}")
        raise

if __name__ == "__main__":
    main()
