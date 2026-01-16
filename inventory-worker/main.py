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

# Configuración de Resiliencia
MAX_RETRIES = 3

async def init_db():
    await Tortoise.init(db_url=DB_URL, modules={"models": ["models"]})
    await Tortoise.generate_schemas()

async def process_order(ch, method, properties, body):
    data = json.loads(body)
    order_uuid = data.get("order_uuid")
    
    # Leer contador de reintentos de los headers (si no existe, es 0)
    headers = properties.headers or {}
    retry_count = headers.get("x-retry-count", 0)

    print(f" [->] Recibido pedido: {order_uuid} | Intento: {retry_count + 1}/{MAX_RETRIES + 1}")

    # --- PATRÓN IDEMPOTENCIA ---
    order = await Order.get_or_none(order_uuid=order_uuid)
    if not order:
        print(f" [!] Pedido no encontrado en DB. Ignorando.")
        ch.basic_ack(delivery_tag=method.delivery_tag)
        return

    if order.status != "PENDING":
        print(f" [i] Pedido ya procesado (Estado: {order.status}). Idempotencia activada.")
        ch.basic_ack(delivery_tag=method.delivery_tag)
        return

    try:
        # --- SIMULACIÓN DE PROCESO ---
        time.sleep(1)
        
        if "ERROR" in data.get("customer_name", "").upper():
            raise Exception("Fallo simulado de conexión con Pasarela de Pagos")

        # --- ÉXITO ---
        order.status = "CONFIRMED"
        await order.save()
        print(f" [OK] Pedido {order_uuid} confirmado.")
        
        # --- NUEVO: PUBLICAR EVENTO FANOUT (PUB/SUB) ---
        # Declaramos el exchange por si acaso no existe
        ch.exchange_declare(exchange='notifications_exchange', exchange_type='fanout')
        
        message = json.dumps({
            "order_uuid": order_uuid,
            "customer_name": data.get("customer_name"),
            "status": "CONFIRMED"
        })
        
        ch.basic_publish(
            exchange='notifications_exchange', # ¡A todos los que escuchen!
            routing_key='', 
            body=message
        )
        print(f" [📢] Evento publicado a notifications_exchange")
        # -----------------------------------------------
        
        ch.basic_ack(delivery_tag=method.delivery_tag)

    except Exception as e:
        print(f" [X] Error: {str(e)}")
        
        # --- ESTRATEGIA DE RETRIES (Backoff manual) ---
        if retry_count < MAX_RETRIES:
            print(f" [..] Reintentando en 2 segundos... (Intento {retry_count + 1})")
            time.sleep(2) # Backoff simple
            
            # Republicamos el mensaje a la misma cola, pero aumentamos el contador
            headers['x-retry-count'] = retry_count + 1
            
            ch.basic_publish(
                exchange='',
                routing_key=QUEUE_NAME,
                body=body,
                properties=pika.BasicProperties(
                    delivery_mode=2,
                    headers=headers # Pasamos el contador actualizado
                )
            )
            # Confirmamos el mensaje viejo (porque ya publicamos el nuevo)
            ch.basic_ack(delivery_tag=method.delivery_tag)
        else:
            print(f" [!!!] Max reintentos alcanzados. Enviando a DLQ.")
            # Nack con requeue=False envía al DLQ configurado
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

def start_consumer():
    params = pika.URLParameters(RABBITMQ_URL)
    connection = pika.BlockingConnection(params)
    channel = connection.channel()

    # Configuración de DLQ (Dead Letter Queue)
    channel.exchange_declare(exchange=DLX_NAME, exchange_type='direct', durable=True)
    channel.queue_declare(queue=DLQ_NAME, durable=True)
    channel.queue_bind(exchange=DLX_NAME, queue=DLQ_NAME, routing_key="dead_message")

    # Cola Principal con DLQ
    args = {
        'x-dead-letter-exchange': DLX_NAME,
        'x-dead-letter-routing-key': 'dead_message'
    }
    channel.queue_declare(queue=QUEUE_NAME, durable=True, arguments=args)
    channel.basic_qos(prefetch_count=1)

    print(" [*] Worker con Retries iniciado. Esperando pedidos...")
    
    def on_message(ch, method, properties, body):
        asyncio.run(process_order(ch, method, properties, body))

    channel.basic_consume(queue=QUEUE_NAME, on_message_callback=on_message)
    channel.start_consuming()

if __name__ == "__main__":
    run_async(init_db())
    time.sleep(10) 
    start_consumer()