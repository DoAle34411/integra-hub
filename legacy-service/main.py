import os
import time
import pandas as pd
import asyncio
from tortoise import Tortoise, run_async
from models import Order # Reutilizamos el modelo
import uuid

# Configuración
DB_URL = os.getenv("DATABASE_URL")
INBOX_DIR = "./inbox"
PROCESSED_DIR = "./processed"

async def init_db():
    await Tortoise.init(db_url=DB_URL, modules={"models": ["models"]})
    await Tortoise.generate_schemas()

async def process_csv_file(filepath, filename):
    print(f" [Legacy] Procesando archivo: {filename}")
    try:
        # 1. Leer CSV con Pandas
        df = pd.read_csv(filepath)
        
        # 2. Validar formato básico (Requisito 3.3.2)
        required_columns = ['customer', 'product', 'qty', 'price']
        if not all(col in df.columns for col in required_columns):
            raise ValueError(f"Formato inválido. Se requieren columnas: {required_columns}")

        # 3. Transformar y Cargar (ETL)
        orders_created = 0
        for _, row in df.iterrows():
            # Crear un pedido "CONFIRMED" directamente (asumiendo que viene de un sistema confiable)
            total = row['qty'] * row['price']
            await Order.create(
                order_uuid=uuid.uuid4(),
                customer_name=f"{row['customer']} (Legacy)",
                total_amount=total,
                status="CONFIRMED",
                items=[{
                    "product_id": row['product'],
                    "quantity": row['qty'],
                    "price": row['price']
                }]
            )
            orders_created += 1

        print(f" [Legacy] Éxito. {orders_created} pedidos importados.")
        
        # 4. Mover a 'processed' para no procesarlo de nuevo
        os.rename(filepath, os.path.join(PROCESSED_DIR, filename))

    except Exception as e:
        print(f" [Legacy] Error procesando archivo: {e}")
        # En un caso real, moveríamos a una carpeta 'error'
        # Aquí renombramos con prefijo ERROR
        error_path = os.path.join(PROCESSED_DIR, f"ERROR_{filename}")
        if os.path.exists(filepath):
            os.rename(filepath, error_path)

async def main_loop():
    await init_db()
    print(" [*] Servicio Legacy monitoreando carpeta /inbox ...")
    
    while True:
        # Listar archivos .csv en inbox
        files = [f for f in os.listdir(INBOX_DIR) if f.endswith('.csv')]
        
        for f in files:
            filepath = os.path.join(INBOX_DIR, f)
            await process_csv_file(filepath, f)
        
        time.sleep(5) # Polling cada 5 segundos

if __name__ == "__main__":
    run_async(main_loop())