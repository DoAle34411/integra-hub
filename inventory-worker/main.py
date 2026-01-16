import os
import json
import asyncio
import pika
import time
import random
from tortoise import Tortoise, run_async
from models import Order

# Configuración
RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@rabbitmq:5672/")
DB_URL = os.getenv("DATABASE_URL")
QUEUE_NAME = "orders_queue"
DLQ_NAME = "orders_dlq"
DLX_NAME = "dlx_exchange"

async def init_db():
    await Tortoise.init(db_url=DB_URL, modules={"models": ["models"]})
    await Tortoise.generate_schemas()

async def process_order(ch, method, properties, body):
    """
    Lógica de negocio: Validar inventario y pago.
    """
    data = json.loads(body)
    order_uuid = data.get("order_uuid")
    print(f" [->] Recibido pedido: {order_uuid}")

    # 1. Patrón IDEMPOTENCIA: Verificar si ya fue procesado
    # Buscamos en DB si este pedido ya no está en PENDING
    order = await Order.get_or_none(order_uuid=order_uuid)
    
    if not order:
        print(f" [!] Pedido {order_uuid} no encontrado en DB. Ignorando.")
        ch.basic_ack(delivery_tag=method.delivery_tag)
        return

    if order.status != "PENDING":
        print(f" [i] Pedido {order_uuid} ya procesado (Estado: {order.status}). Saltando (Idempotencia).")
        ch.basic_ack(delivery_tag=method.delivery_tag)
        return

    try:
        # --- SIMULACIÓN DE PROCESO DE NEGOCIO ---
        print(" [..] Validando stock y procesando pago...")
        time.sleep(2) # Simular latencia
        
        # --- SIMULACIÓN DE FALLO CONTROLADO (Para la defensa) ---
        # Si el cliente se llama "ERROR", forzamos un fallo para probar la DLQ
        if "ERROR" in data.get("customer_name", "").upper():
            raise Exception("Fallo simulado de conexión con Pasarela de Pagos")

        # 2. Actualizar estado en DB
        order.status = "CONFIRMED"
        await order.save()
        
        print(f" [OK] Pedido {order_uuid} confirmado exitosamente.")
        
        # Aquí podrías publicar el evento "OrderConfirmed" (Pub/Sub) para notificaciones
        
        # Confirmar a RabbitMQ que todo salió bien
        ch.basic_ack(delivery_tag=method.delivery_tag)

    except Exception as e:
        print(f" [X] Error procesando pedido: {str(e)}")
        # NACK negativo: Le decimos a RabbitMQ que NO procesamos el mensaje.
        # requeue=False es CLAVE aquí: al decir False, RabbitMQ lo manda al DLQ 
        # (porque configuraremos la cola con Dead Letter Exchange abajo).
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

def start_consumer():
    params = pika.URLParameters(RABBITMQ_URL)
    connection = pika.BlockingConnection(params)
    channel = connection.channel()

    # 1. Declarar el Exchange de Muertos (DLX)
    channel.exchange_declare(exchange=DLX_NAME, exchange_type='direct', durable=True)

    # 2. Declarar la Cola de Muertos (DLQ) y atarla al DLX
    channel.queue_declare(queue=DLQ_NAME, durable=True)
    channel.queue_bind(exchange=DLX_NAME, queue=DLQ_NAME, routing_key="dead_message")

    # 3. Declarar la Cola Principal con configuración de DLQ
    # Si un mensaje es rechazado (nack) o expira, se va al DLX con la routing key "dead_message"
    args = {
        'x-dead-letter-exchange': DLX_NAME,
        'x-dead-letter-routing-key': 'dead_message'
    }
    channel.queue_declare(queue=QUEUE_NAME, durable=True, arguments=args)

    # Le decimos a RabbitMQ que solo nos mande 1 mensaje a la vez (Fair dispatch)
    channel.basic_qos(prefetch_count=1)

    print(" [*] Worker de Inventario esperando pedidos...")
    
    # Adaptador para correr función async dentro del callback síncrono de Pika
    def on_message(ch, method, properties, body):
        asyncio.run(process_order(ch, method, properties, body))

    channel.basic_consume(queue=QUEUE_NAME, on_message_callback=on_message)
    channel.start_consuming()

if __name__ == "__main__":
    # Inicializar DB antes de consumir
    run_async(init_db())
    # Arrancar consumidor (loop infinito)
    # Pequeño sleep para esperar a que RabbitMQ levante en el primer arranque
    time.sleep(10) 
    start_consumer()