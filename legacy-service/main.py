import asyncio
import os
import csv
import logging
import shutil  # <--- IMPORTANTE: Nueva librería
from tortoise import Tortoise, run_async
from models import Order 

# Configuración
DB_URL = os.getenv("DATABASE_URL", "postgres://user:password@db:5432/integrahub")
INBOX_DIR = "/app/inbox"
PROCESSED_DIR = "/app/processed"

# Logging setup
logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("Legacy")

async def init_db():
    await Tortoise.init(db_url=DB_URL, modules={"models": ["models"]})
    await Tortoise.generate_schemas()

async def process_csv_file(filepath, filename):
    logger.info(f" [Legacy] Procesando archivo: {filename}")

    # Crear carpeta processed si no existe
    if not os.path.exists(PROCESSED_DIR):
        os.makedirs(PROCESSED_DIR)

    try:
        # Leemos el archivo
        with open(filepath, 'r') as f:
            reader = csv.DictReader(f)
            count = 0
            # Procesamos filas (Simulación)
            for row in reader:
                count += 1

            logger.info(f" [Legacy] Éxito. {count} pedidos importados.")

        # --- CORRECCIÓN: Usar shutil.move en lugar de os.rename ---
        destination = os.path.join(PROCESSED_DIR, filename)

        # Si ya existe en destino, lo borramos para no fallar
        if os.path.exists(destination):
            os.remove(destination)

        shutil.move(filepath, destination)
        logger.info(" [Legacy] Archivo movido a /processed")
        # ---------------------------------------------------------

    except Exception as e:
        logger.error(f" [Legacy] Error procesando archivo: {e}")
        # Mover a processed con prefijo ERROR para no bloquear
        error_dst = os.path.join(PROCESSED_DIR, f"ERROR_{filename}")
        if os.path.exists(error_dst):
            os.remove(error_dst)
        shutil.move(filepath, error_dst)

async def main_loop():
    logger.info(f" [*] Servicio Legacy monitoreando carpeta {INBOX_DIR} ...")

    # Esperar a DB
    try:
        await init_db()
    except:
        pass # Si falla, reintentará luego o asumimos que ya conectó

    while True:
        try:
            if not os.path.exists(INBOX_DIR):
                os.makedirs(INBOX_DIR)

            files = [f for f in os.listdir(INBOX_DIR) if f.endswith(".csv")]

            for f in files:
                await process_csv_file(os.path.join(INBOX_DIR, f), f)

        except Exception as e:
            logger.error(f"Error loop: {e}")

        await asyncio.sleep(5)

if __name__ == "__main__":
    run_async(main_loop())