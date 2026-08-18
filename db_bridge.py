import os
import psycopg2
from psycopg2 import sql
from dotenv import load_dotenv
from tabulate import tabulate

# Carrega variáveis do .env
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

def execute_query(query, params=None, limit=50):
    """Executa uma query e retorna os resultados formatados"""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(query, params)

            # Se for SELECT, retorna resultados
            if cur.description:
                columns = [desc[0] for desc in cur.description]
                rows = cur.fetchmany(limit)
                return columns, rows
            else:
                conn.commit()
                return None, f"Query executada. Rows affected: {cur.rowcount}"
    finally:
        conn.close()

def show_query(query, params=None, limit=50):
    """Executa e exibe a query formatada"""
    columns, rows = execute_query(query, params, limit)
    if columns:
        print(tabulate(rows, headers=columns, tablefmt='psql'))
        print(f"\n({len(rows)} rows)")
    else:
        print(rows)

def describe_table(table_name):
    """Mostra a estrutura de uma tabela"""
    query = """
        SELECT column_name, data_type, is_nullable, column_default
        FROM information_schema.columns
        WHERE table_name = %s
        ORDER BY ordinal_position
    """
    show_query(query, (table_name,), limit=100)

def sample_data(table_name, limit=10):
    """Mostra amostra de dados de uma tabela"""
    query = sql.SQL("SELECT * FROM {} LIMIT {}").format(
        sql.Identifier(table_name),
        sql.Literal(limit)
    )
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(query)
            columns = [desc[0] for desc in cur.description]
            rows = cur.fetchall()
            print(tabulate(rows, headers=columns, tablefmt='psql'))
    finally:
        conn.close()


if __name__ == "__main__":
    print("=== Conectando ao banco ===")
    print(f"Host: {os.getenv('DB_HOST')}")
    print(f"Database: {os.getenv('DB_NAME')}")

    # Teste de conexão
    try:
        conn = get_connection()
        conn.close()
        print("Conexão OK!\n")
    except Exception as e:
        print(f"Erro na conexão: {e}")
        exit(1)

    # Mostra estrutura das tabelas de classificação
    print("=" * 60)
    print("ESTRUTURA: prd_classificacao")
    print("=" * 60)
    describe_table('prd_classificacao')

    print("\n" + "=" * 60)
    print("ESTRUTURA: prd_produtoclas")
    print("=" * 60)
    describe_table('prd_produtoclas')

    print("\n" + "=" * 60)
    print("AMOSTRA: prd_classificacao (10 rows)")
    print("=" * 60)
    sample_data('prd_classificacao', 10)

    print("\n" + "=" * 60)
    print("AMOSTRA: prd_produtoclas (10 rows)")
    print("=" * 60)
    sample_data('prd_produtoclas', 10)
