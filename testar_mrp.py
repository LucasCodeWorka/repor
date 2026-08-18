"""
Testa a query MRP otimizada
"""
import os
import time
from datetime import datetime
from dotenv import load_dotenv
import psycopg2

load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

def get_connection():
    return psycopg2.connect(
        host=os.getenv('DB_HOST'),
        port=os.getenv('DB_PORT'),
        dbname=os.getenv('DB_NAME'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD')
    )

def testar_mrp():
    print("=" * 70)
    print("TESTE MRP - Análise de MP para produtos 60/90 dias")
    print("=" * 70)
    print()

    conn = get_connection()

    # Query otimizada
    query = """
    WITH
    produtos_30_dias AS (
        SELECT DISTINCT codigoproduto
        FROM mv_geo3
        WHERE dataproduto >= CURRENT_DATE
          AND dataproduto <= CURRENT_DATE + INTERVAL '30 days'
    ),
    produtos_apenas_60_90 AS (
        SELECT
            m.codigoproduto,
            MAX(m.quantidade) AS quantidade_necessaria
        FROM mv_geo3 m
        WHERE m.dataproduto > CURRENT_DATE + INTERVAL '30 days'
          AND m.dataproduto <= CURRENT_DATE + INTERVAL '90 days'
          AND NOT EXISTS (
              SELECT 1 FROM produtos_30_dias p30
              WHERE p30.codigoproduto = m.codigoproduto
          )
        GROUP BY m.codigoproduto
    ),
    necessidade_mp AS (
        SELECT
            c.cd_produtomp,
            SUM(c.qt_consumo * p.quantidade_necessaria) AS qt_necessidade
        FROM produtos_apenas_60_90 p
        JOIN vr_pcp_fcconsumo c ON c.cd_produtopa = p.codigoproduto
        GROUP BY c.cd_produtomp
    ),
    estoque_mp AS (
        SELECT
            s.cd_produto,
            SUM(s.qt_saldo) AS qt_estoque
        FROM prd_prdsaldo s
        WHERE s.cd_empresa = 1
          AND s.cd_saldo IN (1, 2, 15)
        GROUP BY s.cd_produto
    ),
    classificacao_mp AS (
        SELECT
            pc.cd_produto,
            cl.ds_classificacao AS artigo
        FROM prd_produtoclas pc
        JOIN prd_classificacao cl ON cl.cd_tipoclas = pc.cd_tipoclas
                                  AND cl.cd_classificacao = pc.cd_classificacao
        WHERE pc.cd_tipoclas = 111
    )
    SELECT
        n.cd_produtomp AS codigo_mp,
        p.ds_produto AS descricao_mp,
        COALESCE(c.artigo, '-') AS artigo,
        ROUND(n.qt_necessidade, 2) AS necessidade,
        COALESCE(ROUND(e.qt_estoque, 2), 0) AS estoque,
        ROUND(n.qt_necessidade - COALESCE(e.qt_estoque, 0), 2) AS falta
    FROM necessidade_mp n
    JOIN prd_produto p ON p.cd_produto = n.cd_produtomp
    LEFT JOIN estoque_mp e ON e.cd_produto = n.cd_produtomp
    LEFT JOIN classificacao_mp c ON c.cd_produto = n.cd_produtomp
    WHERE n.qt_necessidade > COALESCE(e.qt_estoque, 0)
    ORDER BY falta DESC
    """

    # Primeiro, verificar quantos produtos estão apenas em 60/90
    with conn.cursor() as cur:
        cur.execute("""
            WITH
            produtos_30_dias AS (
                SELECT DISTINCT codigoproduto
                FROM mv_geo3
                WHERE dataproduto >= CURRENT_DATE
                  AND dataproduto <= CURRENT_DATE + INTERVAL '30 days'
            ),
            produtos_apenas_60_90 AS (
                SELECT DISTINCT codigoproduto
                FROM mv_geo3 m
                WHERE m.dataproduto > CURRENT_DATE + INTERVAL '30 days'
                  AND m.dataproduto <= CURRENT_DATE + INTERVAL '90 days'
                  AND NOT EXISTS (
                      SELECT 1 FROM produtos_30_dias p30
                      WHERE p30.codigoproduto = m.codigoproduto
                  )
            )
            SELECT COUNT(*) FROM produtos_apenas_60_90
        """)
        qtd_produtos = cur.fetchone()[0]
        print(f"Produtos APENAS em 60/90 dias (sem estoque 30d): {qtd_produtos}")

    # Executar query MRP
    print()
    print("Executando análise MRP...")
    start = time.time()

    with conn.cursor() as cur:
        cur.execute(query)
        rows = cur.fetchall()

    elapsed = time.time() - start
    print(f"Tempo de execução: {elapsed:.2f}s")
    print()

    if rows:
        print(f"{'CÓDIGO':<10} {'DESCRIÇÃO':<35} {'ARTIGO':<15} {'NECESS.':>12} {'ESTOQUE':>12} {'FALTA':>12}")
        print("-" * 100)

        for row in rows[:30]:  # Top 30
            codigo, descricao, artigo, necessidade, estoque, falta = row
            descricao = (descricao[:32] + '...') if descricao and len(descricao) > 35 else (descricao or '-')
            artigo = artigo[:13] if artigo else '-'
            print(f"{codigo:<10} {descricao:<35} {artigo:<15} {necessidade:>12,.0f} {estoque:>12,.0f} {falta:>12,.0f}")

        if len(rows) > 30:
            print(f"... e mais {len(rows) - 30} itens")

        print()
        print(f"Total de MPs com falta: {len(rows)}")
        print(f"Soma total da falta: {sum(r[5] for r in rows):,.2f}")
    else:
        print("Nenhuma MP com falta identificada!")

    conn.close()

if __name__ == "__main__":
    testar_mrp()
