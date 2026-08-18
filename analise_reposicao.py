"""
Análise de Reposições - Curva A/AA
Identifica pedidos de Curva A e AA incluídos entre 01-15 do mês
que não estão no LOTE 2 (padrão esperado para curva A)
"""

import os
from datetime import datetime
from dotenv import load_dotenv
import psycopg2
import pandas as pd

load_dotenv()

def get_connection():
    """Cria conexão com o banco PostgreSQL"""
    return psycopg2.connect(
        host=os.getenv('DB_HOST'),
        port=os.getenv('DB_PORT'),
        dbname=os.getenv('DB_NAME'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD')
    )

def analisar_reposicoes_curva_a():
    """
    Busca pedidos Curva A/AA incluídos entre 01-15 junho
    e verifica se estão ou não no LOTE 2
    """

    query = """
    WITH pedidos_base AS (
        SELECT
            ped.cd_emppedido,
            ped.cd_representant,
            ped.cd_pedido,
            ped.nr_transacao,
            ped.dt_inclusao,
            ped.dt_transacao,
            lote.cd_lote,
            item.cd_produto,
            f_dic_prd_nivel(item.cd_produto, 'CD'::bpchar) AS referencia
        FROM vr_ped_pedidotra AS ped
        LEFT JOIN vr_ped_pedidoc2 AS lote
            ON ped.cd_emppedido = lote.cd_empresa
            AND ped.cd_pedido = lote.cd_pedido
            AND ped.cd_representant = lote.cd_representant
        LEFT JOIN vr_ped_pedidoi AS item
            ON ped.cd_emppedido = item.cd_empresa
            AND ped.cd_pedido = item.cd_pedido
            AND ped.cd_representant = item.cd_representant
        WHERE ped.dt_inclusao >= '2026-06-01'
            AND ped.dt_inclusao <= '2026-06-15'
            AND ped.cd_emppedido = 1
    )
    SELECT
        pb.cd_emppedido,
        pb.cd_representant,
        pb.cd_pedido,
        pb.nr_transacao,
        pb.dt_inclusao,
        pb.dt_transacao,
        pb.cd_lote,
        pb.cd_produto,
        pb.referencia,
        abc.curva_completa,
        CASE
            WHEN abc.curva_completa IN ('CURVA A', 'CURVA AA') AND pb.cd_lote NOT LIKE '%%.2' THEN 'FORA DO PADRAO'
            WHEN abc.curva_completa IN ('CURVA A', 'CURVA AA') AND pb.cd_lote LIKE '%%.2' THEN 'OK - LOTE 2'
            WHEN abc.curva_completa IN ('CURVA A', 'CURVA AA') AND pb.cd_lote IS NULL THEN 'SEM LOTE'
            ELSE 'CURVA B/C'
        END AS status_lote
    FROM pedidos_base AS pb
    LEFT JOIN curva_abc AS abc
        ON abc.referencia = pb.referencia
    WHERE abc.curva_completa IN ('CURVA A', 'CURVA AA')
    ORDER BY pb.dt_inclusao, pb.cd_pedido;
    """

    conn = get_connection()
    df = pd.read_sql(query, conn)
    conn.close()

    return df

def gerar_relatorio(df):
    """Gera relatório de análise"""

    print("=" * 80)
    print("ANÁLISE DE REPOSIÇÕES - CURVA A/AA")
    print(f"Período: 01/06/2026 a 15/06/2026")
    print("=" * 80)

    # Resumo geral
    print(f"\n[RESUMO GERAL]")
    print(f"   Total de itens Curva A/AA: {len(df)}")
    print(f"   Pedidos unicos: {df['cd_pedido'].nunique()}")
    print(f"   Representantes: {df['cd_representant'].nunique()}")

    # Análise por status do lote
    print(f"\n[STATUS DOS LOTES]")
    status_count = df['status_lote'].value_counts()
    for status, count in status_count.items():
        pct = (count / len(df)) * 100
        marca = "[OK]" if "OK" in status else "[!]" if "FORA" in status else "[?]"
        print(f"   {marca} {status}: {count} ({pct:.1f}%)")

    # Detalhes dos que estão fora do padrão
    fora_padrao = df[df['status_lote'] == 'FORA DO PADRAO']

    if len(fora_padrao) > 0:
        print(f"\n[!] ITENS FORA DO PADRAO (Curva A/AA nao esta no LOTE 2):")
        print("-" * 80)

        # Agrupar por pedido
        for pedido in fora_padrao['cd_pedido'].unique():
            pedido_items = fora_padrao[fora_padrao['cd_pedido'] == pedido]
            primeiro = pedido_items.iloc[0]

            print(f"\n   Pedido: {pedido}")
            print(f"   Representante: {primeiro['cd_representant']}")
            print(f"   Data Inclusao: {primeiro['dt_inclusao']}")
            print(f"   Data Transacao: {primeiro['dt_transacao']}")
            print(f"   Lote Atual: {primeiro['cd_lote']}")
            print(f"   Itens:")

            for _, item in pedido_items.iterrows():
                print(f"      - {item['cd_produto']} | Ref: {item['referencia']} | Curva: {item['curva_completa']}")

    # Itens sem lote
    sem_lote = df[df['status_lote'] == 'SEM LOTE']

    if len(sem_lote) > 0:
        print(f"\n[?] ITENS SEM LOTE DEFINIDO:")
        print("-" * 80)

        for _, item in sem_lote.head(20).iterrows():
            print(f"   Pedido {item['cd_pedido']} | Produto: {item['cd_produto']} | Curva: {item['curva_completa']}")

        if len(sem_lote) > 20:
            print(f"   ... e mais {len(sem_lote) - 20} itens")

    # Análise por data de inclusão
    print(f"\n[DISTRIBUICAO POR DATA DE INCLUSAO]")
    print("-" * 80)

    df['dia_inclusao'] = pd.to_datetime(df['dt_inclusao']).dt.day
    por_dia = df.groupby('dia_inclusao').agg({
        'cd_produto': 'count',
        'cd_pedido': 'nunique'
    }).rename(columns={'cd_produto': 'itens', 'cd_pedido': 'pedidos'})

    for dia, row in por_dia.iterrows():
        print(f"   Dia {dia:02d}: {row['itens']} itens em {row['pedidos']} pedidos")

    # Análise de lotes encontrados
    print(f"\n[LOTES ENCONTRADOS]")
    print("-" * 80)

    lotes = df.groupby('cd_lote').size().sort_values(ascending=False)
    for lote, count in lotes.items():
        lote_str = lote if lote else "(SEM LOTE)"
        print(f"   {lote_str}: {count} itens")

    return fora_padrao, sem_lote

def exportar_csv(df, fora_padrao):
    """Exporta resultados para CSV"""

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    # Exportar todos
    arquivo_todos = f'reposicao_curva_a_completo_{timestamp}.csv'
    df.to_csv(arquivo_todos, index=False, encoding='utf-8-sig')
    print(f"\n[EXPORTADO] {arquivo_todos}")

    # Exportar apenas fora do padrão
    if len(fora_padrao) > 0:
        arquivo_fora = f'reposicao_fora_padrao_{timestamp}.csv'
        fora_padrao.to_csv(arquivo_fora, index=False, encoding='utf-8-sig')
        print(f"[EXPORTADO] {arquivo_fora}")

if __name__ == "__main__":
    print("Conectando ao banco de dados...")

    try:
        df = analisar_reposicoes_curva_a()

        if len(df) == 0:
            print("[!] Nenhum registro encontrado para o periodo!")
        else:
            fora_padrao, sem_lote = gerar_relatorio(df)
            exportar_csv(df, fora_padrao)

    except Exception as e:
        print(f"[ERRO] {e}")
        raise
