"""
Serviço de atualização da View Materializada mv_geo3
Roda em background e atualiza periodicamente
"""

import os
import time
import logging
from datetime import datetime
from dotenv import load_dotenv
import psycopg2

# Configuração
INTERVALO_HORAS = 2  # Atualizar a cada 2 horas
LOG_FILE = os.path.join(os.path.dirname(__file__), 'refresh_service.log')

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Carregar variáveis de ambiente
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

def refresh_materialized_view():
    """Executa o REFRESH da view materializada"""
    logger.info("Iniciando REFRESH da mv_geo3...")
    start = time.time()

    try:
        conn = get_connection()
        conn.autocommit = True

        with conn.cursor() as cur:
            cur.execute("REFRESH MATERIALIZED VIEW mv_geo3;")

        elapsed = time.time() - start
        logger.info(f"REFRESH concluído com sucesso em {elapsed:.1f} segundos")

        # Verificar quantidade de registros
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM mv_geo3;")
            count = cur.fetchone()[0]
            logger.info(f"Total de registros na mv_geo3: {count}")

        conn.close()
        return True

    except Exception as e:
        logger.error(f"Erro no REFRESH: {e}")
        return False

def run_service():
    """Loop principal do serviço"""
    logger.info("=" * 60)
    logger.info("SERVIÇO DE REFRESH INICIADO")
    logger.info(f"Intervalo de atualização: {INTERVALO_HORAS} hora(s)")
    logger.info("=" * 60)

    while True:
        try:
            # Executar refresh
            refresh_materialized_view()

            # Calcular próxima execução
            proxima = datetime.now().replace(
                hour=(datetime.now().hour + INTERVALO_HORAS) % 24,
                minute=0, second=0
            )
            logger.info(f"Próxima atualização: {proxima.strftime('%H:%M')}")

            # Aguardar intervalo
            time.sleep(INTERVALO_HORAS * 3600)

        except KeyboardInterrupt:
            logger.info("Serviço interrompido pelo usuário")
            break
        except Exception as e:
            logger.error(f"Erro no serviço: {e}")
            logger.info("Tentando novamente em 5 minutos...")
            time.sleep(300)

if __name__ == "__main__":
    run_service()
